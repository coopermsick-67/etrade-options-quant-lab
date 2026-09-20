from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
import requests

from brokers.etrade.client import ETradeAPIError, ETradeClient
from brokers.etrade.oauth import ETradeOAuthClient, OAuthTokens
from data.normalization.models import ContractType, OptionQuote
from data.validation.quality import validate_option_quote


def option_quote(**overrides: object) -> OptionQuote:
    values: dict[str, object] = {
        "underlying_symbol": "SPY",
        "option_symbol": "SPY-TEST-CALL-500",
        "option_type": ContractType.CALL,
        "strike": 500.0,
        "expiration": date.today() + timedelta(days=10),
        "timestamp": datetime.now(UTC),
        "bid": 1.0,
        "ask": 1.1,
        "last": 1.05,
        "volume": 100,
        "open_interest": 1000,
    }
    values.update(overrides)
    return OptionQuote(**values)  # type: ignore[arg-type]


def test_data_quality_rejects_stale_crossed_and_expired_quotes() -> None:
    stale = option_quote(timestamp=datetime.now(UTC) - timedelta(minutes=10))
    crossed = option_quote(bid=1.2, ask=1.1)
    expired = option_quote(expiration=date.today() - timedelta(days=1))
    assert "stale quote" in validate_option_quote(stale, stale_seconds=60).reasons
    assert "crossed market" in validate_option_quote(crossed).reasons
    assert "expired contract" in validate_option_quote(expired).reasons


def test_etrade_oauth_url_and_token_parser_are_documented_shapes() -> None:
    client = ETradeOAuthClient("consumer", "secret", environment="sandbox")
    request_token = OAuthTokens("request-token", "request-secret", True)
    assert "https://us.etrade.com/e/t/etws/authorize?" in client.build_authorization_url(
        request_token
    )
    assert "key=consumer" in client.build_authorization_url(request_token)
    response = Mock()
    response.text = "oauth_token=access&oauth_token_secret=secret&oauth_callback_confirmed=true"
    response.raise_for_status.return_value = None
    parsed = client._parse_token_response(response)
    assert parsed == OAuthTokens("access", "secret", True)


def test_etrade_oauth_parser_does_not_hide_malformed_responses() -> None:
    client = ETradeOAuthClient("consumer", "secret")
    response = Mock()
    response.text = "unexpected=true"
    response.raise_for_status.return_value = None
    with pytest.raises(RuntimeError):
        client._parse_token_response(response)


def test_etrade_client_wraps_transport_errors_and_quotes_path_identifiers() -> None:
    client = ETradeClient("consumer", "secret", "access", "access-secret")
    response = Mock()
    response.status_code = 401
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    client.session = Mock()
    client.session.request.return_value = response
    with pytest.raises(ETradeAPIError) as error:
        client.get_balances("account/key")
    assert error.value.status_code == 401
    called_url = client.session.request.call_args.args[1]
    assert "/accounts/account%2Fkey/balance" in called_url
    called_kwargs = client.session.request.call_args.kwargs
    assert called_kwargs["params"] == {"instType": "BROKERAGE", "realTimeNAV": "true"}


def test_etrade_client_quotes_path_symbols_without_allowing_path_injection() -> None:
    client = ETradeClient("consumer", "secret", "access", "access-secret")
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"QuoteResponse": {"QuoteData": []}}
    client.session = Mock()
    client.session.request.return_value = response
    client.get_quote("SPY/../../accounts")
    called_url = client.session.request.call_args.args[1]
    assert "/market/quote/SPY%2F..%2F..%2Faccounts" in called_url


def test_etrade_client_accepts_documented_empty_204_responses() -> None:
    client = ETradeClient("consumer", "secret", "access", "access-secret")
    response = Mock()
    response.status_code = 204
    response.raise_for_status.return_value = None
    client.session = Mock()
    client.session.request.return_value = response
    assert client.list_accounts() == {}
