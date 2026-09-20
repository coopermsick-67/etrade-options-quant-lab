"""Documented E*TRADE OAuth 1.0a lifecycle.

The application returns an authorization URL; the user completes E*TRADE
authorization outside this process and supplies only the resulting verifier to
the local callback/CLI. No username, password, MFA code, or browser cookie is
accepted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

import requests
from requests_oauthlib import OAuth1Session


class ETradeOAuthError(RuntimeError):
    """Raised when the documented OAuth exchange fails."""


@dataclass(frozen=True)
class OAuthTokens:
    token: str
    token_secret: str
    callback_confirmed: bool | None = None


class ETradeOAuthClient:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        environment: str = "sandbox",
        timeout: float = 15.0,
    ) -> None:
        if environment not in {"sandbox", "production"}:
            raise ETradeOAuthError("environment must be sandbox or production")
        if not consumer_key or not consumer_secret:
            raise ETradeOAuthError("consumer key and secret are required")
        host = "https://apisb.etrade.com" if environment == "sandbox" else "https://api.etrade.com"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment
        self.timeout = timeout
        self.oauth_base_url = host
        self.authorization_url_base = "https://us.etrade.com/e/t/etws/authorize"

    def _session(
        self,
        token: str | None = None,
        token_secret: str | None = None,
        verifier: str | None = None,
    ) -> OAuth1Session:
        return OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=token,
            resource_owner_secret=token_secret,
            verifier=verifier,
            callback_uri="oob",
            signature_type="AUTH_HEADER",
        )

    @staticmethod
    def _parse_token_response(response: requests.Response) -> OAuthTokens:
        response.raise_for_status()
        values = parse_qs(response.text, strict_parsing=True)
        try:
            token = values["oauth_token"][0]
            token_secret = values["oauth_token_secret"][0]
        except (KeyError, IndexError) as exc:
            raise ETradeOAuthError("E*TRADE OAuth response omitted token fields") from exc
        confirmed = values.get("oauth_callback_confirmed", [None])[0]
        return OAuthTokens(
            token, token_secret, None if confirmed is None else confirmed.lower() == "true"
        )

    def get_request_token(self) -> OAuthTokens:
        session = self._session()
        response = session.get(
            f"{self.oauth_base_url}/oauth/request_token",
            headers={"oauth_callback": "oob"},
            timeout=self.timeout,
        )
        return self._parse_token_response(response)

    def build_authorization_url(self, request_token: OAuthTokens) -> str:
        query = urlencode({"key": self.consumer_key, "token": request_token.token})
        return f"{self.authorization_url_base}?{query}"

    def get_access_token(self, request_token: OAuthTokens, verifier: str) -> OAuthTokens:
        if not verifier.strip():
            raise ETradeOAuthError("verifier is required")
        session = self._session(request_token.token, request_token.token_secret, verifier.strip())
        response = session.get(f"{self.oauth_base_url}/oauth/access_token", timeout=self.timeout)
        return self._parse_token_response(response)

    def renew_access_token(self, access_token: OAuthTokens) -> str:
        session = self._session(access_token.token, access_token.token_secret)
        response = session.get(
            f"{self.oauth_base_url}/oauth/renew_access_token", timeout=self.timeout
        )
        response.raise_for_status()
        return response.text.strip()

    def revoke_access_token(self, access_token: OAuthTokens) -> str:
        session = self._session(access_token.token, access_token.token_secret)
        response = session.get(
            f"{self.oauth_base_url}/oauth/revoke_access_token", timeout=self.timeout
        )
        response.raise_for_status()
        return response.text.strip()
