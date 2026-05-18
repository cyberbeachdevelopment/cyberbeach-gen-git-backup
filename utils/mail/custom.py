# cyberbeach.cc & discord.gg/cyberbeach

# this is used with our custom SMTP/IMAP mail nodes, to purchase please visit cyberbeach.cc OR discord.gg/cyberbeach

import time, imaplib, email, re, random

from utils.core import setup_logger, STATS, Beach
from colorama import Style
log = setup_logger(__name__)


# dynamic mail
class CustomMailApi:

    def __init__(self, logger=None, smtp_config: dict = None, forced_domain: str = None):
        self.logger = logger
        self.config = smtp_config or {}
        self.forced_domain = forced_domain

        self.username = self.config.get("username") or self.config.get("email")
        self.password = self.config.get("password")
        self.imap_host = self.config.get("imap_host") or self.config.get("host")
        self.imap_port = int(self.config.get("imap_port", 993))
        self.use_ssl = bool(self.config.get("use_ssl", True))
        self.mailbox = self.config.get("mailbox", "INBOX")


    def create_account(self, email: str = None, password: str = None, proxy: str = None):

        if email and "@" in email:
            return email

        if self.username and "@" in self.username:
            return self.username

        domain = None
        if self.imap_host and "." in self.imap_host:
            domain = self.config.get("domain") or self.imap_host.split(":")[0]

        if self.username and domain and "@" not in self.username:
            return f"{self.username}@{domain}"

        if self.forced_domain:
            local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
            return f"{local}@{self.forced_domain}"

        log.warning(
            f"{Beach.WARNING}no smtp/imap config available{Style.RESET_ALL}"
        )
        return None


    def get_verify_url(
        self,
        email_address: str,
        poll_interval: int = 3,
        timeout: int = 120,
        proxy: str = None
    ):
        start = time.time()
        seen = set()

        log.info(
            f"{Beach.INFO}starting email polling for {Beach.PALM}{email_address}{Style.RESET_ALL}"
        )

        while time.time() - start < timeout:
            try:
                conn = (
                    imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                    if self.use_ssl else
                    imaplib.IMAP4(self.imap_host, self.imap_port)
                )

                conn.login(self.username, self.password)
                conn.select(self.mailbox)

                status, data = conn.search(None, '(UNSEEN)')

                if status == 'OK' and data and data[0]:
                    uids = data[0].split()

                    for uid in uids:
                        if uid in seen:
                            continue

                        typ, msgdata = conn.fetch(uid, '(RFC822)')
                        if typ != 'OK' or not msgdata:
                            continue

                        raw = msgdata[0][1]
                        msg = email.message_from_bytes(raw)

                        payload = ""

                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()

                                if ctype == 'text/html':
                                    try:
                                        payload = part.get_payload(decode=True).decode(errors='ignore')
                                    except Exception:
                                        payload = ""
                                    break

                                elif ctype == 'text/plain' and not payload:
                                    try:
                                        payload = part.get_payload(decode=True).decode(errors='ignore')
                                    except Exception:
                                        payload = ""
                        else:
                            try:
                                payload = msg.get_payload(decode=True).decode(errors='ignore')
                            except Exception:
                                payload = ""

                        subject = msg.get("Subject", "") or ""
                        combined = (payload or "") + subject

                        links = re.findall(r'https?://[^\s"\'<>]+', combined)
                        candidates = [l for l in links if ("discord.com" in l or "click.discord.com" in l)]

                        if candidates:
                            url = max(candidates, key=len)

                            log.debug(
                                f"verification link found for email={email_address}"
                            )

                            conn.logout()
                            return url

                        seen.add(uid)

                conn.logout()

            except Exception as e:
                STATS["error"] += 1

                log.error(
                    f"{Beach.CORAL}email polling error for email={email_address}{Style.RESET_ALL}"
                )

            time.sleep(poll_interval)

        log.warning(
            f"{Beach.WARNING}timeout waiting for email={email_address}{Style.RESET_ALL}"
        )
        return None