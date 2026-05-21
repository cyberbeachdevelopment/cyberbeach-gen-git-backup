# credits to someone on github lol, not made by cyberbeach

# vaksms.py
# Docs: https://vak-sms.com/documentation/v0

from __future__ import annotations

import time
from typing import Optional

import requests


class VakSmsError(Exception):
    """Base error for vak-sms wrapper."""


class VakSmsAuthError(VakSmsError):
    """Bad or missing api key (apiKeyNotFound / 401)."""


class VakSmsNoNumbersError(VakSmsError):
    """'noNumber' — no free numbers for the chosen service/country."""


class VakSmsNoBalanceError(VakSmsError):
    """'noBalance' — not enough money on the account."""


class VakSmsBadServiceError(VakSmsError):
    """'badService' / 'badCountry' / 'badOperator' — bad input parameters."""


class VakSmsTimeoutError(VakSmsError):
    """SMS code did not arrive within wait_for_code() deadline."""


class VakSmsClient:

    BASE_URL = "https://vak-sms.com/api"

    # ---- order / sms statuses from docs ----
    STATUS_WAIT     = "wait"      # waiting for SMS
    STATUS_SEND     = "send"      # SMS received
    STATUS_END      = "end"       # order closed / finished
    STATUS_CANCEL   = "cancel"    # cancelled / refunded
    STATUS_READY    = "ready"     # number ready, awaiting sms (some endpoints)

    # known error strings returned by vak-sms as plain text or JSON {"error": "..."}
    _ERR_NO_NUMBER       = "noNumber"
    _ERR_NO_BALANCE      = "noBalance"
    _ERR_API_KEY         = "apiKeyNotFound"
    _ERR_BAD_SERVICE     = "badService"
    _ERR_BAD_COUNTRY     = "badCountry"
    _ERR_BAD_OPERATOR    = "badOperator"
    _ERR_BAD_ID          = "badIdNum"
    _ERR_BAD_STATUS      = "badStatus"

    def __init__(
        self,
        api_key: str,
        *,
        service: str = "ds",          # ds = discord, tg = telegram, etc.
        country: str = "ru",
        operator: Optional[str] = None,
        timeout: float = 30.0,
    ):
        if not api_key:
            raise ValueError("api_key is required")

        self.api_key = api_key
        self.service = service
        self.country = country
        self.operator = operator
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # low-level
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, *, params: Optional[dict] = None) -> requests.Response:
        url = f"{self.BASE_URL}{path}"
        # vak-sms wants the api key as a query param on every call
        full_params = {"apiKey": self.api_key}
        if params:
            full_params.update({k: v for k, v in params.items() if v is not None})

        try:
            res = self._session.request(method, url, params=full_params, timeout=self.timeout)
        except requests.RequestException as e:
            raise VakSmsError(f"network error: {e}") from e

        body = res.text.strip()

        err = self._extract_error_token(body)
        if err:
            self._raise_for_error_token(err, body)

        if res.status_code in (401, 403):
            raise VakSmsAuthError(f"unauthorized ({res.status_code}): {body[:200]}")

        if res.status_code >= 400:
            raise VakSmsError(f"http {res.status_code}: {body[:300]}")

        return res

    @staticmethod
    def _extract_error_token(body: str) -> Optional[str]:
        if not body:
            return None

        # try JSON first
        try:
            data = requests.utils.json.loads(body)
            if isinstance(data, dict) and "error" in data and isinstance(data["error"], str):
                return data["error"]
        except Exception:
            pass

        # otherwise treat short single-word bodies as possible error tokens
        if " " not in body and "{" not in body and len(body) <= 64:
            # heuristic: lowercase camelCase tokens like "noNumber", "noBalance"
            if body[:1].islower() and body.isascii():
                return body

        return None

    @classmethod
    def _raise_for_error_token(cls, err: str, body: str) -> None:
        if err == cls._ERR_NO_NUMBER:
            raise VakSmsNoNumbersError(body)
        if err == cls._ERR_NO_BALANCE:
            raise VakSmsNoBalanceError(body)
        if err == cls._ERR_API_KEY:
            raise VakSmsAuthError(body)
        if err in (cls._ERR_BAD_SERVICE, cls._ERR_BAD_COUNTRY, cls._ERR_BAD_OPERATOR):
            raise VakSmsBadServiceError(body)
        raise VakSmsError(body)

    @staticmethod
    def _json(res: requests.Response) -> dict:
        try:
            return res.json()
        except ValueError as e:
            raise VakSmsError(f"non-json response: {res.text[:200]}") from e

    # ------------------------------------------------------------------
    # account
    # ------------------------------------------------------------------
    def profile(self) -> dict:
        data = self._json(self._request("GET", "/getBalance/"))
        return data

    def balance(self) -> float:
        data = self.profile()
        # docs return: {"balance": 123.45}
        return float(data.get("balance", 0))

    # ------------------------------------------------------------------
    # service / country listings
    # ------------------------------------------------------------------
    def count_numbers(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> dict:
        return self._json(self._request(
            "GET",
            "/getCountNumber/",
            params={
                "service": service or self.service,
                "country": country or self.country,
                "operator": operator if operator is not None else self.operator,
            },
        ))

    def list_country_operators(self) -> dict:
        return self._json(self._request("GET", "/getCountryOperatorList/"))

    # ------------------------------------------------------------------
    # buying numbers
    # ------------------------------------------------------------------
    def buy_number(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> dict:
        return self._json(self._request(
            "GET",
            "/getNumber/",
            params={
                "service": service or self.service,
                "country": country or self.country,
                "operator": operator if operator is not None else self.operator,
            },
        ))

    # ------------------------------------------------------------------
    # order lifecycle
    # ------------------------------------------------------------------
    def check_order(self, id_num: int | str) -> dict:
        return self._json(self._request(
            "GET",
            "/getSmsCode/",
            params={"idNum": id_num},
        ))

    def set_status(self, id_num: int | str, status: str) -> dict:
        return self._json(self._request(
            "GET",
            "/setStatus/",
            params={"idNum": id_num, "status": status},
        ))

    def finish_order(self, id_num: int | str) -> dict:
        return self.set_status(id_num, self.STATUS_END)

    def cancel_order(self, id_num: int | str) -> dict:
        return self.set_status(id_num, self.STATUS_CANCEL)

    def request_new_sms(self, id_num: int | str) -> dict:
        return self.set_status(id_num, self.STATUS_SEND)

    # ------------------------------------------------------------------
    # high-level helpers
    # ------------------------------------------------------------------
    def get_code(self, id_num: int | str) -> Optional[str]:
        data = self.check_order(id_num)
        code = data.get("smsCode")
        if code:
            return str(code)
        return None

    def wait_for_code(
        self,
        id_num: int | str,
        *,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> str:
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                data = self.check_order(id_num)
            except VakSmsError:
                # surface auth
                raise

            code = data.get("smsCode")
            if code:
                return str(code)

            status = data.get("status")
            if status in (self.STATUS_CANCEL, self.STATUS_END):
                raise VakSmsError(f"order {id_num} ended with status={status}")

            time.sleep(poll_interval)

        # timed out
        try:
            self.cancel_order(id_num)
        except VakSmsError:
            pass

        raise VakSmsTimeoutError(
            f"no sms for order {id_num} within {timeout:.0f}s"
        )

    def buy_and_wait(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str] = None,
        operator: Optional[str] = None,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> tuple[dict, str]:
        order = self.buy_number(service=service, country=country, operator=operator)
        id_num = order.get("idNum") or order.get("id")
        if not id_num:
            raise VakSmsError(f"buy_number returned no idNum: {order}")

        code = self.wait_for_code(
            id_num, timeout=timeout, poll_interval=poll_interval
        )
        return order, code