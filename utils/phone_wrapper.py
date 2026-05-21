# cyberbeach.cc & discord.gg/cyberbeach

from utils.core import *

from utils.phone.vaksms import VakSmsClient
from utils.phone.herosms import HeroSmsClient


log = setup_logger(__name__)


DEFAULT_SERVICE = "ds" # discord
DEFAULT_COUNTRY = "ru" # default country
DEFAULT_SMS_TIMEOUT = 180
DEFAULT_POLL_INTERVAL = 3



class PhoneWrapper:

    PROVIDERS = {
        "vaksms":  VakSmsClient,
        "herosms": HeroSmsClient,
    }

    def __init__(
        self,
        provider: str,
        api_key: str,
        *,
        service: str = DEFAULT_SERVICE,
        country: str | int = DEFAULT_COUNTRY,
        operator: str | None = None,
        sms_timeout: float = DEFAULT_SMS_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        **kwargs,
    ):
        provider = provider.lower()

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"unsupported provider '{provider}' "
                f"(available: {list(self.PROVIDERS.keys())})"
            )

        self.provider = provider
        self.sms_timeout = float(sms_timeout)
        self.poll_interval = float(poll_interval)

        self.client = self.PROVIDERS[provider](
            api_key=api_key,
            service=service,
            country=country,
            operator=operator,
            **kwargs,
        )

        log.debug(
            f"Phone wrapper initialized {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{provider}{Style.RESET_ALL} "
            f"service={Beach.OCEAN}{service}{Style.RESET_ALL} "
            f"country={Beach.OCEAN}{country}{Style.RESET_ALL} "
            f"operator={Beach.OCEAN}{operator}{Style.RESET_ALL} "
            f"sms_timeout={Beach.OCEAN}{self.sms_timeout}{Style.RESET_ALL} "
            f"poll_interval={Beach.OCEAN}{self.poll_interval}{Style.RESET_ALL}"
        )

    def balance(self) -> float:
        bal = float(self.client.balance())
        log.debug(
            f"Balance check {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{self.provider}{Style.RESET_ALL} "
            f"balance={Beach.OCEAN}{bal}{Style.RESET_ALL}"
        )
        return bal

    def buy_number(
        self,
        *,
        service: str | None = None,
        country: str | int | None = None,
        operator: str | None = None,
    ) -> dict:

        order = self.client.buy_number(
            service=service,
            country=country,
            operator=operator,
        )
        order = self._normalize_order(order)

        log.debug(
            f"Bought number {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{self.provider}{Style.RESET_ALL} "
            f"id={Beach.OCEAN}{order['id']}{Style.RESET_ALL} "
            f"phone={Beach.OCEAN}{order['phone']}{Style.RESET_ALL}"
        )

        return order

    def wait_for_code(
        self,
        order_id: int | str,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> str:
        timeout = float(timeout if timeout is not None else self.sms_timeout)
        poll_interval = float(poll_interval if poll_interval is not None else self.poll_interval)

        code = self.client.wait_for_code(
            order_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )

        log.debug(
            f"SMS code received {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{self.provider}{Style.RESET_ALL} "
            f"id={Beach.OCEAN}{order_id}{Style.RESET_ALL}"
        )

        return code

    def buy_and_wait(
        self,
        *,
        service: str | None = None,
        country: str | int | None = None,
        operator: str | None = None,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> tuple[dict, str]:

        order = self.buy_number(service=service, country=country, operator=operator)
        code = self.wait_for_code(
            order["id"],
            timeout=timeout,
            poll_interval=poll_interval,
        )
        return order, code

    def finish_order(self, order_id: int | str):
        log.debug(
            f"Finish order {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{self.provider}{Style.RESET_ALL} "
            f"id={Beach.OCEAN}{order_id}{Style.RESET_ALL}"
        )
        return self.client.finish_order(order_id)

    def cancel_order(self, order_id: int | str):
        log.debug(
            f"Cancel order {Beach.FOAM}→{Style.RESET_ALL} "
            f"provider={Beach.OCEAN}{self.provider}{Style.RESET_ALL} "
            f"id={Beach.OCEAN}{order_id}{Style.RESET_ALL}"
        )
        return self.client.cancel_order(order_id)

    def _normalize_order(self, order: dict) -> dict:
        if not isinstance(order, dict):
            raise ValueError(f"unexpected buy_number response: {order!r}")

        order_id = (
            order.get("id")
            or order.get("idNum")
            or order.get("activation_id")
        )
        phone = (
            order.get("phone")
            or order.get("tel")
            or order.get("number")
        )

        if not order_id or not phone:
            raise ValueError(
                f"could not normalize order from provider={self.provider}: {order}"
            )

        normalized = dict(order)
        normalized["id"] = str(order_id)
        normalized["phone"] = str(phone)
        return normalized


def build_phone_wrapper_from_config(config: dict) -> PhoneWrapper | None:
    phone_cfg = config.get("phone", {}) if isinstance(config, dict) else {}

    if not phone_cfg.get("enabled", False):
        return None

    provider = (phone_cfg.get("provider") or "vaksms").lower()
    if provider not in PhoneWrapper.PROVIDERS:
        log.debug(
            f"Unknown phone provider {Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.CORAL}{provider}{Style.RESET_ALL}"
        )
        return None

    sub_cfg = phone_cfg.get(provider, {}) if isinstance(phone_cfg, dict) else {}
    api_key = sub_cfg.get("api_key") or sub_cfg.get("token")
    if not api_key:
        log.debug(
            f"Phone provider {Beach.OCEAN}{provider}{Style.RESET_ALL} selected "
            f"{Beach.FOAM}→{Style.RESET_ALL} "
            f"{Beach.SAND}no api_key/token provided{Style.RESET_ALL}"
        )
        return None

    default_country = 0 if provider == "herosms" else DEFAULT_COUNTRY

    return PhoneWrapper(
        provider=provider,
        api_key=api_key,
        service=sub_cfg.get("service", DEFAULT_SERVICE),
        country=sub_cfg.get("country", default_country),
        operator=sub_cfg.get("operator"),
        sms_timeout=float(sub_cfg.get("sms_timeout", DEFAULT_SMS_TIMEOUT)),
        poll_interval=float(sub_cfg.get("poll_interval", DEFAULT_POLL_INTERVAL)),
    )