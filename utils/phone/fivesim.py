# credits to someone on github lol

# fivesim.py
# Docs: https://5sim.net/docs

from __future__ import annotations

import time
from typing import Optional

import requests


class FiveSimError(Exception):
    """Base error for 5sim wrapper."""


class FiveSimAuthError(FiveSimError):
    """401/403 — bad or missing token."""


class FiveSimNoNumbersError(FiveSimError):
    """'no free phones' / out-of-stock for the chosen country+operator."""


class FiveSimTimeoutError(FiveSimError):
    """SMS code did not arrive within wait_for_code() deadline."""


class FiveSimClient:
    """
    Thin wrapper around the 5sim REST API.

    Auth: pass your API token (from https://5sim.net -> Profile -> API).
    All money values returned by 5sim are in your account currency (RUB by default).
    """

    BASE_URL = "https://5sim.net/v1"

    # ---- order statuses from docs ----
    STATUS_PENDING  = "PENDING"   # waiting for SMS
    STATUS_RECEIVED = "RECEIVED"  # SMS received
    STATUS_CANCELED = "CANCELED"
    STATUS_TIMEOUT  = "TIMEOUT"
    STATUS_FINISHED = "FINISHED"
    STATUS_BANNED   = "BANNED"

    def __init__(
        self,
        api_token: str,
        *,
        product: str = "discord",
        country: str = "england",
        operator: str = "any",
        timeout: float = 30.0,
    ):
        if not api_token:
            raise ValueError("api_token is required")

        self.api_token = api_token
        self.product = product
        self.country = country
        self.operator = operator
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # low-level
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.BASE_URL}{path}"
        try:
            res = self._session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise FiveSimError(f"network error: {e}") from e

        if res.status_code in (401, 403):
            raise FiveSimAuthError(f"unauthorized ({res.status_code}): {res.text[:200]}")

        # 5sim returns plain-text errors like "no free phones", "order not found", etc.
        body = res.text.strip()
        lowered = body.lower()
        if "no free phones" in lowered:
            raise FiveSimNoNumbersError(body)

        if res.status_code >= 400:
            raise FiveSimError(f"http {res.status_code}: {body[:300]}")

        return res

    @staticmethod
    def _json(res: requests.Response) -> dict:
        try:
            return res.json()
        except ValueError as e:
            raise FiveSimError(f"non-json response: {res.text[:200]}") from e

    # ------------------------------------------------------------------
    # account
    # ------------------------------------------------------------------
    def profile(self) -> dict:
        """GET /user/profile — returns id, email, balance, rating, defaults."""
        return self._json(self._request("GET", "/user/profile"))

    def balance(self) -> float:
        """Convenience: just the balance number."""
        return float(self.profile().get("balance", 0))

    # ------------------------------------------------------------------
    # buying numbers
    # ------------------------------------------------------------------
    def buy_number(
        self,
        *,
        product: Optional[str] = None,
        country: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> dict:
        """
        GET /user/buy/activation/{country}/{operator}/{product}

        Returns the order dict:
            {
              "id": int,
              "phone": "+44...",
              "operator": "...",
              "product": "discord",
              "price": float,
              "status": "PENDING",
              "expires": "2024-...",
              "sms": null,
              "created_at": "..."
            }
        """
        product  = product  or self.product
        country  = country  or self.country
        operator = operator or self.operator

        path = f"/user/buy/activation/{country}/{operator}/{product}"
        return self._json(self._request("GET", path))

    # ------------------------------------------------------------------
    # order lifecycle
    # ------------------------------------------------------------------
    def check_order(self, order_id: int | str) -> dict:
        """GET /user/check/{id} — returns current order state including any sms list."""
        return self._json(self._request("GET", f"/user/check/{order_id}"))

    def finish_order(self, order_id: int | str) -> dict:
        """GET /user/finish/{id} — mark order as successfully used."""
        return self._json(self._request("GET", f"/user/finish/{order_id}"))

    def cancel_order(self, order_id: int | str) -> dict:
        """GET /user/cancel/{id} — cancel before SMS arrives (refund)."""
        return self._json(self._request("GET", f"/user/cancel/{order_id}"))

    def ban_order(self, order_id: int | str) -> dict:
        """GET /user/ban/{id} — flag number as banned by the target service."""
        return self._json(self._request("GET", f"/user/ban/{order_id}"))

    # ------------------------------------------------------------------
    # high-level helpers
    # ------------------------------------------------------------------
    def get_code(self, order_id: int | str) -> Optional[str]:
        """
        Single-shot check. Returns the SMS code string if one has arrived, else None.
        Does NOT poll — use wait_for_code() for that.
        """
        order = self.check_order(order_id)
        sms_list = order.get("sms") or []
        if not sms_list:
            return None
        # latest first
        latest = sms_list[-1]
        return latest.get("code") or latest.get("text")

    def wait_for_code(
        self,
        order_id: int | str,
        *,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> str:
        """
        Poll check_order() until an SMS code arrives or timeout expires.

        Raises:
            FiveSimTimeoutError on timeout (and cancels the order to refund).
            FiveSimError if the order enters a terminal non-success state.
        """
        deadline = time.time() + timeout

        while time.time() < deadline:
            order = self.check_order(order_id)
            status = order.get("status")
            sms_list = order.get("sms") or []

            if sms_list:
                latest = sms_list[-1]
                code = latest.get("code") or latest.get("text")
                if code:
                    return code

            if status in (self.STATUS_CANCELED, self.STATUS_TIMEOUT, self.STATUS_BANNED):
                raise FiveSimError(f"order {order_id} ended with status={status}")

            time.sleep(poll_interval)

        # timed out → cancel to get refunded, then raise
        try:
            self.cancel_order(order_id)
        except FiveSimError:
            pass

        raise FiveSimTimeoutError(
            f"no sms for order {order_id} within {timeout:.0f}s"
        )

    def buy_and_wait(
        self,
        *,
        product: Optional[str] = None,
        country: Optional[str] = None,
        operator: Optional[str] = None,
        timeout: float = 180.0,
        poll_interval: float = 3.0,
    ) -> tuple[dict, str]:
        """
        Convenience: buy a number, wait for the SMS code, return (order, code).

        Caller is responsible for calling finish_order(order['id']) afterwards
        if the verification succeeded, or ban_order(...) if it failed.
        """
        order = self.buy_number(product=product, country=country, operator=operator)
        code = self.wait_for_code(
            order["id"], timeout=timeout, poll_interval=poll_interval
        )
        return order, code


# ----------------------------------------------------------------------
# tiny CLI demo (only runs when executed directly)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import os
    import sys

    token = os.environ.get("FIVESIM_TOKEN")
    if not token:
        print("set FIVESIM_TOKEN env var first", file=sys.stderr)
        sys.exit(1)

    client = FiveSimClient(token, product="discord", country="england", operator="any")

    print("balance:", client.balance())

    order, code = client.buy_and_wait(timeout=120, poll_interval=3)
    print("number:", order["phone"], "id:", order["id"])
    print("code:", code)

    # mark as used so 5sim knows it succeeded
    client.finish_order(order["id"])
    print("finished.")