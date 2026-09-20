from hypothesis import given
from hypothesis import strategies as st

from quant.pricing.black_scholes import OptionType, bs_price


@given(
    spot=st.floats(min_value=1, max_value=500, allow_nan=False, allow_infinity=False),
    strike=st.floats(min_value=1, max_value=500, allow_nan=False, allow_infinity=False),
    time=st.floats(min_value=0.01, max_value=3, allow_nan=False, allow_infinity=False),
    volatility=st.floats(min_value=0.01, max_value=2, allow_nan=False, allow_infinity=False),
)
def test_call_price_is_nonnegative_and_increases_with_spot(
    spot: float, strike: float, time: float, volatility: float
) -> None:
    price = bs_price(spot, strike, time, 0.02, volatility, OptionType.CALL)
    higher = bs_price(spot * 1.001, strike, time, 0.02, volatility, OptionType.CALL)
    assert price >= 0
    assert higher >= price
