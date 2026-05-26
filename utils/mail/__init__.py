# cyberbeach.cc & discord.gg/cyberbeach

from .cybertemp import CyberTempMailApi


def get_mail_api(config: dict, logger=None):
    mail_cfg = config.get("mail", {}) if isinstance(config, dict) else {}

    provider = (mail_cfg.get("provider") or "cybertemp").lower()

    if provider == "cybertemp":
        ct_cfg = mail_cfg.get("cybertemp", {}) if isinstance(mail_cfg, dict) else {}
        return CyberTempMailApi(
            logger=logger,
            api_key=ct_cfg.get("api_key"),
        ), "cybertemp"

    # fallback
    cybertemp_cfg = mail_cfg.get("cybertemp", {}) if isinstance(mail_cfg, dict) else {}
    return CyberTempMailApi(logger=logger, api_key=cybertemp_cfg.get("api_key")), "cybertemp"


__all__ = ["CyberTempMailApi", "get_mail_api"]
