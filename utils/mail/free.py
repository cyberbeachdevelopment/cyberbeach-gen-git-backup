# freecustom.email mail service — https://www.freecustom.email/api/docs/quickstart
import time
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
    DEFAULT_DOMAIN = "junkstopper.info"

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
            log.warning(f"{Beach.WARNING}freecustom.email could not create an email{Style.RESET_ALL}")
            return None

        if not self._register_inbox(created_email, proxy=proxy):
            log.warning(f"{Beach.WARNING}no inbox: email={created_email}{Style.RESET_ALL}")
            return None

        self.created_emails[created_email] = password or ""
        log.debug(f"email={created_email}")
        return created_email

    def _create_temp_account(self, proxy: str = None):
        local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"{local}@{self.DEFAULT_DOMAIN}"

    # temp
    def _delete_all_inboxes(self, proxy: str = None):
        if not self.api_key:
            return False

        proxies = self._build_proxies(proxy)

        try:
            # get all inboxes
            resp = requests.get(
                self.INBOXES_ENDPOINT,
                headers=self._headers(),
                timeout=20,
                proxies=proxies,
            )

            if not resp.ok:
                log.warning(f"{Beach.WARNING}failed to fetch inbox list{Style.RESET_ALL}")
                return False

            data = resp.json()
            inboxes = data.get("data", [])

            if isinstance(inboxes, dict):
                inboxes = inboxes.get("inboxes", [])

            deleted = 0

            for inbox in inboxes:
                email = (
                    inbox.get("inbox")
                    or inbox.get("email")
                    or inbox.get("address")
                )

                if not email:
                    continue

                encoded_email = quote(email, safe="")

                del_resp = requests.delete(
                    f"{self.INBOXES_ENDPOINT}/{encoded_email}",
                    headers=self._headers(),
                    timeout=20,
                    proxies=proxies,
                )

                if del_resp.ok:
                    deleted += 1
                    log.debug(f"deleted inbox={email}")

            log.warning(f"{Beach.WARNING}deleted {deleted} inboxes because storage was full{Style.RESET_ALL}")
            return True

        except Exception as e:
            STATS["error"] += 1
            log.error(f"{Beach.ERROR}delete inboxes error={e}{Style.RESET_ALL}")
            return False

    def _register_inbox(self, email: str, proxy: str = None) -> bool:
        if not self.api_key:
            log.warning(f"{Beach.WARNING}api key missing: provider=freecustomemail{Style.RESET_ALL}")
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

            # success
            if resp.status_code in (200, 201):
                log.debug(f"freecustom.email registered: email={email}")
                return True

            # read response text safely
            error_text = ""
            try:
                error_text = resp.text.lower()
            except Exception:
                pass

            # detect inbox full / limit reached
            full_errors = [
                "full",
                "limit",
                "quota",
                "too many inboxes",
                "maximum inboxes",
            ]

            if any(x in error_text for x in full_errors):
                log.warning(f"{Beach.WARNING}inbox limit reached -> deleting all inboxes{Style.RESET_ALL}")

                if self._delete_all_inboxes(proxy=proxy):

                    # retry once after cleanup
                    retry_resp = requests.post(
                        self.INBOXES_ENDPOINT,
                        json=payload,
                        headers=self._headers(),
                        timeout=20,
                        proxies=proxies,
                    )

                    if retry_resp.status_code in (200, 201):
                        log.debug(f"registered after cleanup: email={email}")
                        return True

            log.warning(f"{Beach.WARNING}freecustom.email failed: email={email}{Style.RESET_ALL}")
            return False

        except Exception as e:
            STATS["error"] += 1
            log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
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
                            target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l and "blog." not in l]
                            
                            if target_links:
                                url = None
                                if len(target_links) >= 2:
                                    second_url = target_links[1]
                                    if "verify" in second_url.lower() or "token=" in second_url.lower() or "click.discord.com" in second_url:
                                        url = second_url
                                        log.debug(f"using discord secondary URL")
                                
                                if not url:
                                    url = max(target_links, key=len)
                                    log.debug(f"using discord URL")
                                
                                if "click.discord.com" in url:
                                    log.debug(f"url={url[:30]}...")
                                    resolved = self._resolve_url(url, proxy=proxy)
                                    if resolved:
                                        return resolved
                                return url
                            used_message_ids.add(msg_id)
            except Exception as e:
                STATS["error"] += 1
                log.error(
            f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}"
        )
            time.sleep(poll_interval)
            
        log.warning(f"{Beach.WARNING}timeout: email={email}{Style.RESET_ALL}")
        return None

    def _read_message_detail(self, email: str, message_id: str, proxy: str = None):
        if not self.api_key or not email or not message_id:
            return None
        proxies = self._build_proxies(proxy)
        encoded_email = quote(email, safe="")
        encoded_id = quote(str(message_id), safe="")
        url = f"{self.INBOXES_ENDPOINT}/{encoded_email}/messages/{encoded_id}"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                timeout=15,
                proxies=proxies,
            )
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
                log.debug(f"url={final_url[:40]}...")
                return final_url
        except Exception:
            pass
        return None

    def delete_inbox(self, email: str):
        # Not required for flow; we only skip old message ids while polling.
        return True

    def _read_inbox(self, email: str, proxy: str = None):
        if not self.api_key:
            return None
        proxies = self._build_proxies(proxy)
        encoded_email = quote(email, safe="")
        url = f"{self.INBOXES_ENDPOINT}/{encoded_email}/messages"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                timeout=15,
                proxies=proxies,
            )

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