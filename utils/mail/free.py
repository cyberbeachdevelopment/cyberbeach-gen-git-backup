# freecustom.email mail service — https://www.freecustom.email/api/docs/quickstart
import time
import threading
import requests
import re
import random
import string
import json
from urllib.parse import quote

from utils.core import setup_logger, STATS, Beach, Style
log = setup_logger(__name__)


class TempTfMailApi:
    BASE_URL = "https://api2.freecustom.email/v1"
    INBOXES_ENDPOINT = f"{BASE_URL}/inboxes"
    DEFAULT_DOMAIN = "ditplay.info"

    # shared across all instances
    _cleanup_lock = threading.Lock()
    _last_cleanup_ts = 0.0
    _CLEANUP_COOLDOWN = 8.0

    def __init__(self, logger=None, forced_domain: str = None, api_key: str = None):
        self.created_emails = {}
        self.logger = logger
        self.forced_domain = forced_domain
        self.api_key = api_key
        if not self.api_key:
            self.api_key = self._read_api_key_from_config()

    def _build_proxies(self, proxy: str = None):
        if proxy and "://" not in proxy:
            proxy = f"http://{proxy}"
        return {"http": proxy, "https": proxy} if proxy else None

    def _headers(self):
        if not self.api_key:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _read_api_key_from_config(self):
        try:
            with open("input/config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            mail_cfg = cfg.get("mail", {}) if isinstance(cfg, dict) else {}
            key = mail_cfg.get("freecustomemail_api_key")
            return (key or "").strip()
        except Exception:
            return ""

    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if email and '@' in email:
            created_email = email
        elif self.forced_domain:
            local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{local}@{self.forced_domain}"
        else:
            created_email = self._create_temp_account(proxy=proxy)

        if not created_email:
            log.warning(
                f"Email creation failed {Beach.FOAM}→{Style.RESET_ALL} "
                f"provider={Beach.OCEAN}freecustom.email{Style.RESET_ALL}"
            )
            return None

        if not self._register_inbox(created_email, proxy=proxy):
            log.warning(
                f"No inbox found {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.OCEAN}{created_email}{Style.RESET_ALL}"
            )
            return None

        self.created_emails[created_email] = password or ""

        return created_email

    def _create_temp_account(self, proxy: str = None):
        local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"{local}@{self.DEFAULT_DOMAIN}"


    def _delete_all_inboxes(self, proxy: str = None):
        if not self.api_key:
            return False

        acquired = TempTfMailApi._cleanup_lock.acquire(blocking=True, timeout=60)
        if not acquired:
            log.warning(
                f"Cleanup skipped {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.SAND}lock busy{Style.RESET_ALL}"
            )
            return False

        try:

            if (time.time() - TempTfMailApi._last_cleanup_ts) < TempTfMailApi._CLEANUP_COOLDOWN:
                log.debug(
                    f"Cleanup skipped {Beach.FOAM}→{Style.RESET_ALL} "
                    f"{Beach.OCEAN}recent run detected{Style.RESET_ALL}"
                )
                return True

            proxies = self._build_proxies(proxy)
            time.sleep(1.5)  # throttle before listing

            resp = requests.get(
                self.INBOXES_ENDPOINT,
                headers=self._headers(),
                timeout=20,
                proxies=proxies,
            )

            if not resp.ok:
                log.warning(
                    f"{Beach.WARNING}failed to fetch inboxes "
                    f"status={resp.status_code}{Style.RESET_ALL}"
                )
                return False

            data = resp.json()
            inboxes = data.get("data", [])
            if isinstance(inboxes, dict):
                inboxes = inboxes.get("inboxes", [])

            deleted = 0
            already_gone = 0

            for inbox in inboxes:
                email = (
                    inbox.get("inbox")
                    or inbox.get("email")
                    or inbox.get("address")
                )
                if not email:
                    continue

                encoded_email = quote(email, safe="")
                delete_url = f"{self.INBOXES_ENDPOINT}/{encoded_email}"

                # hard throttle EVERY request
                time.sleep(1.2)

                del_resp = requests.delete(
                    delete_url,
                    headers=self._headers(),
                    timeout=20,
                    proxies=proxies,
                )

                if del_resp.ok:
                    deleted += 1
                    log.debug(
                        f"Inbox deleted {Beach.FOAM}→{Style.RESET_ALL} "
                        f"{Beach.OCEAN}{email}{Style.RESET_ALL}"
                    )
                    continue

                # 404 =
                if del_resp.status_code == 404:
                    already_gone += 1
                    continue

                # rate limit
                if del_resp.status_code == 429:
                    log.warning(
                        f"Rate limited {Beach.FOAM}→{Style.RESET_ALL} "
                        f"{Beach.OCEAN}{email}{Style.RESET_ALL} "
                        f"{Beach.SAND}sleeping 5s{Style.RESET_ALL}"
                    )
                    time.sleep(5)

                    retry_resp = requests.delete(
                        delete_url,
                        headers=self._headers(),
                        timeout=20,
                        proxies=proxies,
                    )
                    if retry_resp.ok or retry_resp.status_code == 404:
                        deleted += 1
                        log.debug(
                            f"Inbox deleted after retry {Beach.FOAM}→{Style.RESET_ALL} "
                            f"{Beach.OCEAN}{email}{Style.RESET_ALL}"
                        )
                    continue

                log.warning(
                    f"Failed deleting inbox {Beach.FOAM}→{Style.RESET_ALL} "
                    f"{Beach.OCEAN}{email}{Style.RESET_ALL} "
                    f"status={Beach.CORAL}{del_resp.status_code}{Style.RESET_ALL}"
                )

            log.info(
                f"Cleanup done {Beach.FOAM}→{Style.RESET_ALL} "
                f"deleted={Beach.OCEAN}{deleted}{Style.RESET_ALL} "
                f"already_gone={Beach.OCEAN}{already_gone}{Style.RESET_ALL}"
            )

            TempTfMailApi._last_cleanup_ts = time.time()
            return True

        except Exception as e:
            STATS["error"] += 1
            log.error(
                f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
            )
            return False
        finally:
            TempTfMailApi._cleanup_lock.release()

    def _register_inbox(self, email: str, proxy: str = None) -> bool:
        if not self.api_key:
            log.warning(
                f"API key missing {Beach.FOAM}→{Style.RESET_ALL} "
                f"provider={Beach.OCEAN}freecustomemail{Style.RESET_ALL}"
            )
            return False

        proxies = self._build_proxies(proxy)
        payload = {"inbox": email}

        try:
            resp = requests.post(
                self.INBOXES_ENDPOINT,
                json=payload,
                headers=self._headers(),
                timeout=20,
                proxies=proxies,
            )

            if resp.status_code in (200, 201):
                log.debug(
                    f"Email registered {Beach.FOAM}→{Style.RESET_ALL} "
                    f"provider={Beach.OCEAN}freecustom.email{Style.RESET_ALL} "
                    f"email={Beach.OCEAN}{email}{Style.RESET_ALL}"
                )
                return True

            error_text = ""
            try:
                error_text = resp.text.lower()
            except Exception:
                pass

            full_errors = ["full", "limit", "quota", "too many inboxes", "maximum inboxes"]

            if any(x in error_text for x in full_errors):

                # and the cooldown check skips redundant cleanups
                with TempTfMailApi._cleanup_lock:
                    needs_cleanup = (time.time() - TempTfMailApi._last_cleanup_ts) >= TempTfMailApi._CLEANUP_COOLDOWN

                if needs_cleanup:
                    log.warning(
                        f"Inbox limit reached {Beach.FOAM}→{Style.RESET_ALL} "
                        f"{Beach.SAND}deleting all inboxes{Style.RESET_ALL}"
                    )
                    self._delete_all_inboxes(proxy=proxy)
                else:
                    log.debug(
                        f"Inbox limit hit {Beach.FOAM}→{Style.RESET_ALL} "
                        f"{Beach.SAND}cleanup just ran, waiting briefly{Style.RESET_ALL}"
                    )
                    time.sleep(2.0)

                # retry once after cleanup
                retry_resp = requests.post(
                    self.INBOXES_ENDPOINT,
                    json=payload,
                    headers=self._headers(),
                    timeout=20,
                    proxies=proxies,
                )
                if retry_resp.status_code in (200, 201):
                    log.debug(
                        f"Email registered after cleanup {Beach.FOAM}→{Style.RESET_ALL} "
                        f"email={Beach.OCEAN}{email}{Style.RESET_ALL}"
                    )
                    return True

            log.warning(
                f"Email registration failed {Beach.FOAM}→{Style.RESET_ALL} "
                f"provider={Beach.OCEAN}freecustom.email{Style.RESET_ALL} "
                f"email={Beach.CORAL}{email}{Style.RESET_ALL}"
            )
            return False

        except Exception as e:
            STATS["error"] += 1
            log.error(f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}")
            return False

    def get_verify_url(self, email: str, poll_interval: int = 3, timeout: int = 120, proxy: str = None):
        start_time = time.time()
        used_message_ids = set()

        while time.time() - start_time < timeout:
            try:
                messages = self._read_inbox(email, proxy=proxy)
                if messages:
                    for msg in messages:
                        msg_id = msg.get("id")
                        if msg_id in used_message_ids:
                            continue

                        subject = msg.get("subject", "")
                        direct_link = msg.get("verification_link") or msg.get("verificationLink")
                        if direct_link and ("discord.com" in direct_link or "click.discord.com" in direct_link):
                            return direct_link

                        if "discord" in subject.lower() or "verify" in subject.lower() or "verif" in subject.lower():
                            detail = self._read_message_detail(email, msg_id, proxy=proxy) if msg_id else None
                            html_body = (detail.get("html", "") if detail else "") or msg.get("html", "")
                            text_body = (detail.get("body", "") if detail else "") or msg.get("body", "")
                            detail_link = (detail.get("verification_link") if detail else "") or ""
                            if detail_link and ("discord.com" in detail_link or "click.discord.com" in detail_link):
                                return detail_link
                            combined = html_body + text_body

                            all_links = re.findall(r'https?://[^\s"\'<>]+', combined)
                            target_links = [
                                l for l in all_links
                                if ("discord.com" in l or "click.discord.com" in l)
                                and "support." not in l and "blog." not in l
                            ]

                            if target_links:
                                url = None
                                if len(target_links) >= 2:
                                    second_url = target_links[1]
                                    if (
                                        "verify" in second_url.lower()
                                        or "token=" in second_url.lower()
                                        or "click.discord.com" in second_url
                                    ):
                                        url = second_url
                                        log.debug(
                                            f"Discord endpoint {Beach.FOAM}→{Style.RESET_ALL} "
                                            f"{Beach.OCEAN}using secondary URL{Style.RESET_ALL}"
                                        )

                                if not url:
                                    url = max(target_links, key=len)
                                    log.debug(
                                        f"Discord endpoint {Beach.FOAM}→{Style.RESET_ALL} "
                                        f"{Beach.OCEAN}using primary URL{Style.RESET_ALL}"
                                    )

                                if "click.discord.com" in url:
                                    log.debug(
                                        f"Request URL {Beach.FOAM}→{Style.RESET_ALL} "
                                        f"{Beach.OCEAN}{url[:30]}...{Style.RESET_ALL}"
                                    )
                                    resolved = self._resolve_url(url, proxy=proxy)
                                    if resolved:
                                        return resolved
                                return url
                            used_message_ids.add(msg_id)
            except Exception as e:
                STATS["error"] += 1
                log.error(f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}")
            time.sleep(poll_interval)

        log.warning(
            f"Request timeout {Beach.FOAM}→{Style.RESET_ALL} "
            f"email={Beach.CORAL}{email}{Style.RESET_ALL}"
        )
        return None

    def _read_message_detail(self, email: str, message_id: str, proxy: str = None):
        if not self.api_key or not email or not message_id:
            return None
        proxies = self._build_proxies(proxy)
        encoded_email = quote(email, safe="")
        encoded_id = quote(str(message_id), safe="")
        url = f"{self.INBOXES_ENDPOINT}/{encoded_email}/messages/{encoded_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=15, proxies=proxies)
            if not resp.ok:
                return None
            data = resp.json()
            msg = data.get("data", {}) if isinstance(data, dict) else {}
            if not isinstance(msg, dict):
                return None
            return {
                "id": msg.get("id") or msg.get("message_id") or msg.get("_id"),
                "subject": msg.get("subject", ""),
                "body": msg.get("text", "") or msg.get("body", "") or msg.get("plain", ""),
                "html": msg.get("html", "") or msg.get("html_body", "") or msg.get("bodyHtml", ""),
                "verification_link": msg.get("verification_link") or msg.get("verificationLink") or "",
            }
        except Exception:
            return None

    def _resolve_url(self, url: str, proxy: str = None) -> str:
        if proxy and "://" not in proxy:
            proxy = f"http://{proxy}"
        proxies = {"http": proxy, "https": proxy} if proxy else None
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, proxies=proxies)
            final_url = resp.url
            if "discord.com/verify" in final_url:
                log.debug(
                    f"Request URL {Beach.FOAM}→{Style.RESET_ALL} "
                    f"{Beach.OCEAN}{final_url[:40]}...{Style.RESET_ALL}"
                )
                return final_url
        except Exception:
            pass
        return None

    def delete_inbox(self, email: str):

        return True

    def _read_inbox(self, email: str, proxy: str = None):
        if not self.api_key:
            return None
        proxies = self._build_proxies(proxy)
        encoded_email = quote(email, safe="")
        url = f"{self.INBOXES_ENDPOINT}/{encoded_email}/messages"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=15, proxies=proxies)
            if not resp.ok:
                return None

            data = resp.json()
            messages = data.get("data", []) if isinstance(data, dict) else []
            if isinstance(messages, dict):
                messages = messages.get("messages", []) or messages.get("items", [])
            if not isinstance(messages, list):
                messages = []

            normalized = []
            for msg in messages:
                html = msg.get("html", "") or msg.get("html_body", "") or msg.get("bodyHtml", "")
                text = msg.get("text", "") or msg.get("body", "") or msg.get("plain", "")
                normalized.append({
                    "id": msg.get("id") or msg.get("message_id") or msg.get("_id"),
                    "from": msg.get("from"),
                    "to": msg.get("to"),
                    "subject": msg.get("subject", ""),
                    "body": text,
                    "html": html,
                    "verification_link": msg.get("verification_link") or msg.get("verificationLink") or "",
                })
            return normalized
        except Exception:
            return None