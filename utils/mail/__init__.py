# cyberbeach.cc & discord.gg/cyberbeach

from .free import TempTfMailApi
from .custom import ImapMailApi
from .cybertemp import CyberTempMailApi


def get_mail_api(config: dict, logger=None):
    mail_cfg = config.get("mail", {}) if isinstance(config, dict) else {}

    provider = (mail_cfg.get("provider") or "freecustomemail").lower()

    if provider == "imap":
        imap_cfg = mail_cfg.get("imap", {}) if isinstance(mail_cfg, dict) else {}
        return ImapMailApi(logger=logger, imap_config=imap_cfg), "imap"

    if provider == "cybertemp":
        ct_cfg = mail_cfg.get("cybertemp", {}) if isinstance(mail_cfg, dict) else {}
        return CyberTempMailApi(
            logger=logger,
            api_key=ct_cfg.get("api_key"),
        ), "cybertemp"

    if provider == "freecustomemail":
        free_cfg = mail_cfg.get("freecustomemail", {}) if isinstance(mail_cfg, dict) else {}
        return TempTfMailApi(
            logger=logger,
            api_key=free_cfg.get("api_key"),
        ), "freecustomemail"

    # fallback
    free_cfg = mail_cfg.get("freecustomemail", {}) if isinstance(mail_cfg, dict) else {}
    return TempTfMailApi(logger=logger, api_key=free_cfg.get("api_key")), "freecustomemail"


__all__ = ["TempTfMailApi", "ImapMailApi", "CyberTempMailApi", "get_mail_api"]
