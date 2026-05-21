# cyberbeach.cc & discord.gg/cyberbeach

from .vaksms import VakSmsClient
from .herosms import HeroSmsClient


def get_phone_api(config: dict, logger=None):
    phone_cfg = config.get("phone", {}) if isinstance(config, dict) else {}

    if not phone_cfg.get("enabled", False):
        return None, None

    provider = (phone_cfg.get("provider") or "fivesim").lower()

    if provider == "vaksms":
        vs_cfg = phone_cfg.get("vaksms", {}) if isinstance(phone_cfg, dict) else {}
        api_key = vs_cfg.get("api_key") or vs_cfg.get("token")
        if not api_key:
            if logger:
                logger.debug("vaksms selected but no api_key provided")
            return None, None

        client = VakSmsClient(
            api_key=api_key,
            service=vs_cfg.get("service", "ds"),
            country=vs_cfg.get("country", "ru"),
            operator=vs_cfg.get("operator"),
        )
        client.sms_timeout = float(vs_cfg.get("sms_timeout", 180))
        client.poll_interval = float(vs_cfg.get("poll_interval", 3))
        return client, "vaksms"

    if provider == "herosms":
        hs_cfg = phone_cfg.get("herosms", {}) if isinstance(phone_cfg, dict) else {}
        api_key = hs_cfg.get("api_key") or hs_cfg.get("token")
        if not api_key:
            if logger:
                logger.debug("herosms selected but no api_key provided")
            return None, None

        client = HeroSmsClient(
            api_key=api_key,
            service=hs_cfg.get("service", "ds"),
            country=hs_cfg.get("country", 0),
            operator=hs_cfg.get("operator"),
        )
        client.sms_timeout = float(hs_cfg.get("sms_timeout", 180))
        client.poll_interval = float(hs_cfg.get("poll_interval", 3))
        return client, "herosms"

    if logger:
        logger.debug(f"unknown phone provider='{provider}'")
    return None, None


__all__ = [
    "VakSmsClient",
    "HeroSmsClient",
    "get_phone_api",
]