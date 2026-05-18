# cyberbeach.cc & discord.gg/cyberbeach

from .free import TempTfMailApi
from .custom import CustomMailApi


def get_mail_api(config: dict, logger=None):
    mail_cfg = config.get("mail", {}) if isinstance(config, dict) else {}
    smtp_cfg = mail_cfg.get("smtp", {}) if isinstance(mail_cfg, dict) else {}
    if smtp_cfg.get("enabled"):
        return CustomMailApi(logger=logger, smtp_config=smtp_cfg), "custom"
    return TempTfMailApi(logger=logger, api_key=mail_cfg.get("api_key")), "free"

__all__ = ["TempTfMailApi", "CustomMailApi", "get_mail_api"]
