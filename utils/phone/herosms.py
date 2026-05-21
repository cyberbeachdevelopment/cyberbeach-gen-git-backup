# credits to someone on github lol

# herosms.py
# Docs: https://hero-sms.com/api

from __future__ import annotations

import time
from typing import Optional

import requests


class HeroSmsError(Exception):
    """Base error for hero-sms wrapper."""


class HeroSmsAuthError(HeroSmsError):
    """Bad or missing api key (BAD_KEY / 401)."""


class HeroSmsNoNumbersError(HeroSmsError):
    """'NO_NUMBERS' — no free numbers/emails for the chosen service."""


class HeroSmsNoBalanceError(HeroSmsError):
    """'NO_BALANCE' — not enough money on the account."""


class HeroSmsBadServiceError(HeroSmsError):
    """'BAD_SERVICE' / 'BAD_COUNTRY' / 'BAD_ACTION' — bad input parameters."""


class HeroSmsTimeoutError(HeroSmsError):
    """SMS/email code did not arrive within wait_for_code() deadline."""


class HeroSmsClient:

    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

    # ---- sms / activation statuses ----
    STATUS_WAIT_CODE   = "STATUS_WAIT_CODE"     # waiting for sms
    STATUS_WAIT_RETRY  = "STATUS_WAIT_RETRY"    # waiting for next sms
    STATUS_WAIT_RESEND = "STATUS_WAIT_RESEND"   # waiting for resend
    STATUS_CANCEL      = "STATUS_CANCEL"        # cancelled
    STATUS_OK          = "STATUS_OK"            # code arrived (followed by :code)

    # ---- setStatus action codes ----
    SET_READY        = 1   # ready to receive sms
    SET_GOT_CODE     = 3   # request another sms
    SET_FINISH       = 6   # finish successfully
    SET_CANCEL       = 8   # cancel activation

    # ---- known string error tokens from hero-sms ----
    _ERR_NO_NUMBERS   = "NO_NUMBERS"
    _ERR_NO_BALANCE   = "NO_BALANCE"
    _ERR_BAD_KEY      = "BAD_KEY"
    _ERR_ERROR_SQL    = "ERROR_SQL"
    _ERR_BAD_ACTION   = "BAD_ACTION"
    _ERR_BAD_SERVICE  = "BAD_SERVICE"
    _ERR_BAD_COUNTRY  = "WRONG_COUNTRY"
    _ERR_NO_ACTIVATION = "NO_ACTIVATION"
    _ERR_BAD_STATUS   = "BAD_STATUS"
    _ERR_WRONG_ACT_ID = "WRONG_ACTIVATION_ID"

    def __init__(
        self,
        api_key: str,
        *,
        service: str = "ds",        # ds = discord
        country: str | int = 0,     # 0 = russia in sms-activate-style APIs
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
        self._session.headers.update({"Accept": "application/json, text/plain, */*"})

    # ------------------------------------------------------------------
    # low-level
    # ------------------------------------------------------------------
    def _request(self, action: str, *, params: Optional[dict] = None) -> requests.Response:
        full_params = {"api_key": self.api_key, "action": action}
        if params:
            full_params.update({k: v for k, v in params.items() if v is not None})

        try:
            res = self._session.get(self.BASE_URL, params=full_params, timeout=self.timeout)
        except requests.RequestException as e:
            raise HeroSmsError(f"network error: {e}") from e

        body = res.text.strip()

        # detect error tokens first (works for both plain-text and JSON shapes)
        err = self._extract_error_token(body)
        if err:
            self._raise_for_error_token(err, body)

        if res.status_code in (401, 403):
            raise HeroSmsAuthError(f"unauthorized ({res.status_code}): {body[:200]}")

        if res.status_code >= 400:
            raise HeroSmsError(f"http {res.status_code}: {body[:300]}")

        return res

    @staticmethod
    def _extract_error_token(body: str) -> Optional[str]:
        if not body:
            return None

        # JSON shape
        try:
            data = requests.utils.json.loads(body)
            if isinstance(data, dict):
                status = data.get("status")
                if status in ("error", "fail"):
                    err = data.get("error") or data.get("message")
                    if isinstance(err, str):
                        return err
            # JSON that parses but isn't an error envelope -> not an error
            return None
        except Exception:
            pass

        # plain-text shape: short ALL_CAPS_SNAKE token, possibly followed by ":payload"
        head = body.split(":", 1)[0]
        if (
            head
            and head.isascii()
            and head.replace("_", "").isalnum()
            and head == head.upper()
            and not head.startswith("ACCESS_")
            and not head.startswith("STATUS_OK")
            and len(head) <= 40
        ):
            return head

        return None

    @classmethod
    def _raise_for_error_token(cls, err: str, body: str) -> None:
        if err == cls._ERR_NO_NUMBERS:
            raise HeroSmsNoNumbersError(body)
        if err == cls._ERR_NO_BALANCE:
            raise HeroSmsNoBalanceError(body)
        if err == cls._ERR_BAD_KEY:
            raise HeroSmsAuthError(body)
        if err in (
            cls._ERR_BAD_ACTION,
            cls._ERR_BAD_SERVICE,
            cls._ERR_BAD_COUNTRY,
            cls._ERR_BAD_STATUS,
            cls._ERR_WRONG_ACT_ID,
        ):
            raise HeroSmsBadServiceError(body)
        raise HeroSmsError(body)

    @staticmethod
    def _json(res: requests.Response) -> dict:
        try:
            return res.json()
        except ValueError as e:
            raise HeroSmsError(f"non-json response: {res.text[:200]}") from e

    @staticmethod
    def _parse_text(res: requests.Response) -> tuple[str, list[str]]:
        body = res.text.strip()
        parts = body.split(":")
        return parts[0], parts[1:]

    def balance(self) -> float:
        res = self._request("getBalance")
        token, parts = self._parse_text(res)
        if token != "ACCESS_BALANCE" or not parts:
            raise HeroSmsError(f"unexpected getBalance response: {res.text[:200]}")
        try:
            return float(parts[0])
        except ValueError as e:
            raise HeroSmsError(f"balance parse error: {res.text[:200]}") from e

    def profile(self) -> dict:
        return {"balance": self.balance()}

    def count_numbers(
        self,
        *,
        country: Optional[str | int] = None,
        operator: Optional[str] = None,
    ) -> dict:
        res = self._request(
            "getNumbersStatus",
            params={
                "country": country if country is not None else self.country,
                "operator": operator if operator is not None else self.operator,
            },
        )
        return self._json(res)

    def get_prices(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str | int] = None,
    ) -> dict:
        return self._json(self._request(
            "getPrices",
            params={
                "service": service or self.service,
                "country": country if country is not None else self.country,
            },
        ))

    # ------------------------------------------------------------------
    # buying numbers (SMS activations)
    # ------------------------------------------------------------------
    def buy_number(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str | int] = None,
        operator: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> dict:
        params = {
            "service": service or self.service,
            "country": country if country is not None else self.country,
            "operator": operator if operator is not None else self.operator,
        }
        if max_price is not None:
            params["maxPrice"] = max_price

        res = self._request("getNumber", params=params)
        token, parts = self._parse_text(res)
        if token != "ACCESS_NUMBER" or len(parts) < 2:
            raise HeroSmsError(f"unexpected getNumber response: {res.text[:200]}")

        activation_id, phone = parts[0], parts[1]
        return {
            "id": activation_id,
            "phone": phone,
            "service": params["service"],
            "country": params["country"],
            "raw": res.text.strip(),
        }

    # ------------------------------------------------------------------
    # order lifecycle (SMS)
    # ------------------------------------------------------------------
    def check_order(self, activation_id: int | str) -> dict:
        res = self._request("getStatus", params={"id": activation_id})
        token, parts = self._parse_text(res)

        if token == "STATUS_OK":
            code = parts[0] if parts else None
            return {"status": self.STATUS_OK, "code": code, "raw": res.text.strip()}

        if token in (
            self.STATUS_WAIT_CODE,
            self.STATUS_WAIT_RETRY,
            self.STATUS_WAIT_RESEND,
            self.STATUS_CANCEL,
        ):
            return {"status": token, "code": None, "raw": res.text.strip()}

        raise HeroSmsError(f"unexpected getStatus response: {res.text[:200]}")

    def set_status(self, activation_id: int | str, status_code: int) -> str:
        res = self._request(
            "setStatus",
            params={"id": activation_id, "status": status_code},
        )
        token, _ = self._parse_text(res)
        return token

    def finish_order(self, activation_id: int | str) -> str:
        return self.set_status(activation_id, self.SET_FINISH)

    def cancel_order(self, activation_id: int | str) -> str:
        return self.set_status(activation_id, self.SET_CANCEL)

    def request_new_sms(self, activation_id: int | str) -> str:
        return self.set_status(activation_id, self.SET_GOT_CODE)

    # ------------------------------------------------------------------
    # emails
    # ------------------------------------------------------------------
    def buy_email(
        self,
        *,
        service: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> dict:
        data = self._json(self._request(
            "getEmail",
            params={
                "service": service or self.service,
                "mail": domain,    # docs call this `mail` (the domain) on email endpoints
            },
        ))

        # hero-sms returns {"id": ..., "email": ...} on success
        email_id = data.get("id") or data.get("emailId")
        email_addr = data.get("email") or data.get("mail")
        if not email_id or not email_addr:
            raise HeroSmsError(f"unexpected getEmail response: {data}")

        return {
            "id": str(email_id),
            "email": email_addr,
            "service": service or self.service,
            "raw": data,
        }

    def check_email(self, email_id: int | str) -> dict:
        data = self._json(self._request("getEmailCode", params={"id": email_id}))

        # hero-sms typically returns:
        #   {"status": "wait"}                                    -> still waiting
        #   {"status": "ok", "code": "...", "letter": "..."}      -> arrived
        #   {"status": "cancel"}                                  -> dead
        status = (data.get("status") or "").lower()
        code = data.get("code") or data.get("smsCode")
        letter = data.get("letter") or data.get("text") or data.get("message")

        return {
            "status": status or "unknown",
            "code": str(code) if code else None,
            "letter": letter,
            "raw": data,
        }

    def set_email_status(self, email_id: int | str, status_code: int) -> dict:
        return self._json(self._request(
            "setEmailStatus",
            params={"id": email_id, "status": status_code},
        ))

    def finish_email(self, email_id: int | str) -> dict:
        return self.set_email_status(email_id, self.SET_FINISH)

    def cancel_email(self, email_id: int | str) -> dict:
        return self.set_email_status(email_id, self.SET_CANCEL)

    # ------------------------------------------------------------------
    # high-level helpers — SMS
    # ------------------------------------------------------------------
    def get_code(self, activation_id: int | str) -> Optional[str]:
        data = self.check_order(activation_id)
        return data.get("code")

    def wait_for_code(
        self,
        activation_id: int | str,
        *,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> str:
        deadline = time.time() + timeout

        while time.time() < deadline:
            data = self.check_order(activation_id)
            status = data.get("status")
            code = data.get("code")

            if status == self.STATUS_OK and code:
                return code

            if status == self.STATUS_CANCEL:
                raise HeroSmsError(f"activation {activation_id} ended with status={status}")

            time.sleep(poll_interval)

        try:
            self.cancel_order(activation_id)
        except HeroSmsError:
            pass

        raise HeroSmsTimeoutError(
            f"no sms for activation {activation_id} within {timeout:.0f}s"
        )

    def buy_and_wait(
        self,
        *,
        service: Optional[str] = None,
        country: Optional[str | int] = None,
        operator: Optional[str] = None,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> tuple[dict, str]:
        order = self.buy_number(service=service, country=country, operator=operator)
        code = self.wait_for_code(
            order["id"], timeout=timeout, poll_interval=poll_interval
        )
        return order, code

    # ------------------------------------------------------------------
    # high-level helpers — Email
    # ------------------------------------------------------------------
    def get_email_code(self, email_id: int | str) -> Optional[str]:
        return self.check_email(email_id).get("code")

    def wait_for_email_code(
        self,
        email_id: int | str,
        *,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> str:
        deadline = time.time() + timeout

        while time.time() < deadline:
            data = self.check_email(email_id)
            status = data.get("status")
            code = data.get("code")

            if status == "ok" and code:
                return code

            if status in ("cancel", "error"):
                raise HeroSmsError(f"email {email_id} ended with status={status}")

            time.sleep(poll_interval)

        try:
            self.cancel_email(email_id)
        except HeroSmsError:
            pass

        raise HeroSmsTimeoutError(
            f"no email code for {email_id} within {timeout:.0f}s"
        )

    def buy_email_and_wait(
        self,
        *,
        service: Optional[str] = None,
        domain: Optional[str] = None,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> tuple[dict, str]:
        order = self.buy_email(service=service, domain=domain)
        code = self.wait_for_email_code(
            order["id"], timeout=timeout, poll_interval=poll_interval
        )
        return order, code