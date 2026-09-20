"""Documented E*TRADE REST client. No browser automation or private endpoints."""

from __future__ import annotations

from typing import Any

import requests
from requests_oauthlib import OAuth1


class ETradeConfigurationError(ValueError):
    pass


class ETradeClient:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        environment: str = "sandbox",
        timeout: float = 15.0,
    ) -> None:
        if environment not in {"sandbox", "production"}:
            raise ETradeConfigurationError("environment must be sandbox or production")
        if not all((consumer_key, consumer_secret, access_token, access_token_secret)):
            raise ETradeConfigurationError("all OAuth secrets are required")
        self.base_url = (
            "https://apisb.etrade.com/v1"
            if environment == "sandbox"
            else "https://api.etrade.com/v1"
        )
        self.environment = environment
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = OAuth1(
            consumer_key,
            consumer_secret,
            access_token,
            access_token_secret,
            signature_type="AUTH_HEADER",
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Accept": "application/json", **kwargs.pop("headers", {})}
        response = self.session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, headers=headers, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def list_accounts(self) -> dict[str, Any]:
        return self._request("GET", "/accounts/list")

    def get_balances(self, account_id_key: str) -> dict[str, Any]:
        return self._request("GET", f"/accounts/{account_id_key}/margin")

    def get_portfolio(self, account_id_key: str) -> dict[str, Any]:
        return self._request("GET", f"/accounts/{account_id_key}/portfolio")

    def get_quote(self, symbols: str, detail_flag: str = "ALL") -> dict[str, Any]:
        return self._request("GET", f"/market/quote/{symbols}", params={"detailFlag": detail_flag})

    def get_option_chain(
        self, symbol: str, expiry_year: int, expiry_month: int, **params: Any
    ) -> dict[str, Any]:
        query = {"symbol": symbol, "expiryYear": expiry_year, "expiryMonth": expiry_month, **params}
        return self._request("GET", "/market/optionchains", params=query)

    def get_option_expirations(self, symbol: str) -> dict[str, Any]:
        return self._request("GET", "/market/optionexpiredate", params={"symbol": symbol})

    def list_orders(self, account_id_key: str, **params: Any) -> dict[str, Any]:
        return self._request("GET", f"/accounts/{account_id_key}/orders", params=params)

    def get_order_status(self, account_id_key: str, **params: Any) -> dict[str, Any]:
        """Retrieve order status through the documented list-orders surface."""

        return self.list_orders(account_id_key, **params)

    def preview_order(self, account_id_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/accounts/{account_id_key}/orders/preview", json=payload)

    def place_order(self, account_id_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/accounts/{account_id_key}/orders/place", json=payload)

    def preview_changed_order(
        self, account_id_key: str, order_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/accounts/{account_id_key}/orders/{order_id}/change/preview",
            json=payload,
        )

    def place_changed_order(
        self, account_id_key: str, order_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/accounts/{account_id_key}/orders/{order_id}/change/place",
            json=payload,
        )

    def cancel_order(self, account_id_key: str, order_id: str) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/accounts/{account_id_key}/orders/cancel",
            json={"CancelOrderRequest": {"orderId": order_id}},
        )
