# cybertemp.xyz mail service — https://cybertemp.xyz/api  (pip install cybertemp)

import time
import random
import string
import re
import json

from utils.core import setup_logger, STATS, Beach, Style

log = setup_logger(__name__)

try:
    from cybertemp import CyberTemp
except ImportError:
    CyberTemp = None


class CyberTempMailApi:

    def __init__(self, logger=None, api_key: str = None):
        self.created_emails = {}
        self.logger = logger
        self.api_key = (api_key or "").strip()

        if CyberTemp is None:
            log.warning(
                f"cybertemp package missing {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.SAND}pip install cybertemp{Style.RESET_ALL}"
            )
            self.client = None
        elif not self.api_key:
            log.warning(
                f"API key missing {Beach.FOAM}→{Style.RESET_ALL} "
                f"provider={Beach.OCEAN}cybertemp{Style.RESET_ALL}"
            )
            self.client = None
        else:
            try:
                self.client = CyberTemp(api_key=self.api_key, debug=False)
            except Exception as e:
                STATS["error"] += 1
                log.error(f"{Beach.ERROR}error={type(e).__name__}: {e}{Style.RESET_ALL}")
                self.client = None

        self._domain_cache = None

    def _pick_domain(self) -> str:
        if self._domain_cache:
            return random.choice(self._domain_cache)

        if self.client is None:
            return None

        try:
            domains = self.client.get_domains(type="discord")
        except Exception as e:
            log.error(
                f"Domain fetch failed {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.ERROR}{type(e).__name__}: {e}{Style.RESET_ALL}"
            )
            return None

        cleaned = []
        if isinstance(domains, list):
            for d in domains:
                if isinstance(d, str):
                    cleaned.append(d.lstrip("@"))
                elif isinstance(d, dict):
                    v = d.get("domain") or d.get("name") or d.get("address")
                    if v:
                        cleaned.append(str(v).lstrip("@"))

        if not cleaned:
            log.warning(
                f"No discord domains returned {Beach.FOAM}→{Style.RESET_ALL} "
                f"provider={Beach.OCEAN}cybertemp{Style.RESET_ALL}"
            )
            return None

        self._domain_cache = cleaned
        return random.choice(cleaned)

    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if email and "@" in email:
            created_email = email
        else:
            domain = self._pick_domain()
            if not domain:
                log.warning(
                    f"Email creation failed {Beach.FOAM}→{Style.RESET_ALL} "
                    f"provider={Beach.OCEAN}cybertemp{Style.RESET_ALL} "
                    f"{Beach.SAND}no domains available{Style.RESET_ALL}"
                )
                return None
            local = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{local}@{domain}"

        self.created_emails[created_email] = password or ""

        log.debug(
            f"Email registered {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}cybertemp{Style.RESET_ALL} "
            f"email={Beach.OCEAN}{created_email}{Style.RESET_ALL}"
        )
        return created_email

    def get_verify_url(self, email: str, poll_interval: int = 3, timeout: int = 120, proxy: str = None):
        if self.client is None:
            return None

        start_time = time.time()
        used_message_ids = set()

        while time.time() - start_time < timeout:
            try:
                messages = self.client.get_mailbox(email, max_retries=1, delay_between_retries=1.0)
                if messages:
                    for msg in messages:
                        msg_id = msg.get("id")
                        if msg_id in used_message_ids:
                            continue

                        subject = msg.get("subject", "") or ""
                        if not ("discord" in subject.lower() or "verif" in subject.lower()):
                            used_message_ids.add(msg_id)
                            continue

                        html_body = msg.get("html", "") or ""
                        text_body = msg.get("text", "") or msg.get("body", "") or ""
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

    def _resolve_url(self, url: str, proxy: str = None) -> str:
        import requests
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
        if self.client is None or not email:
            return True
        try:
            self.client.delete_user_inbox(email)
        except Exception as e:
            log.debug(
                f"Inbox delete skipped {Beach.FOAM}→{Style.RESET_ALL} "
                f"{Beach.SAND}{type(e).__name__}: {e}{Style.RESET_ALL}"
            )
        return True