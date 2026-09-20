"""Internal paper broker with explicit fill assumptions and idempotency."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite

from brokers.base import BrokerOrder, Fill, OrderAction, OrderRequest, OrderStatus


@dataclass
class PaperPosition:
    symbol: str
    quantity: int
    average_price: float
    multiplier: float


class PaperBroker:
    def __init__(
        self,
        initial_equity: float = 10_000.0,
        slippage_bps: float = 15.0,
        partial_fill_rate: float = 0.0,
        fee_per_contract: float = 0.65,
        allow_uncovered_short: bool = False,
    ) -> None:
        if (
            not isfinite(initial_equity)
            or initial_equity <= 0
            or not isfinite(slippage_bps)
            or slippage_bps < 0
            or not 0 <= partial_fill_rate <= 1
            or not isfinite(fee_per_contract)
            or fee_per_contract < 0
        ):
            raise ValueError("invalid paper broker configuration")
        self.cash = float(initial_equity)
        self.initial_equity = float(initial_equity)
        self.slippage_bps = slippage_bps
        self.partial_fill_rate = partial_fill_rate
        self.fee_per_contract = fee_per_contract
        self.allow_uncovered_short = allow_uncovered_short
        self._orders: dict[str, BrokerOrder] = {}
        self._client_ids: dict[str, str] = {}
        self._positions: dict[str, PaperPosition] = {}
        self._equity_snapshots: list[tuple[datetime, float]] = [
            (datetime.now(UTC), self.cash)
        ]
        self._outage = False
        self._emergency_stop = False

    def set_outage(self, enabled: bool) -> None:
        self._outage = enabled

    @property
    def emergency_stop(self) -> bool:
        return self._emergency_stop

    def set_emergency_stop(self, enabled: bool) -> None:
        self._emergency_stop = enabled

    def submit(self, request: OrderRequest) -> BrokerOrder:
        existing_id = self._client_ids.get(request.client_order_id)
        if existing_id:
            return self._orders[existing_id]
        if self._outage:
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.UNKNOWN,
                reason="paper broker outage",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        if self._emergency_stop:
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.REJECTED,
                reason="paper emergency stop is active",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        if (
            request.quantity < 1
            or request.limit_price <= 0
            or request.bid < 0
            or request.ask < 0
            or request.ask < request.bid
            or request.multiplier <= 0
        ):
            order = BrokerOrder(
                str(len(self._orders) + 1), request, OrderStatus.REJECTED, reason="invalid order"
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        fill_quantity = request.quantity
        if self.partial_fill_rate > 0:
            fill_quantity = max(1, int(request.quantity * (1 - self.partial_fill_rate)))
        raw_price = request.ask if request.action is OrderAction.BUY else request.bid
        adjustment = raw_price * self.slippage_bps / 10_000
        fill_price = (
            raw_price + adjustment
            if request.action is OrderAction.BUY
            else max(0.01, raw_price - adjustment)
        )
        if request.action is OrderAction.BUY and fill_price > request.limit_price:
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.ACCEPTED,
                reason="limit not reached",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        if request.action is OrderAction.SELL and fill_price < request.limit_price:
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.ACCEPTED,
                reason="limit not reached",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        fees = self.fee_per_contract * fill_quantity
        notional = fill_price * fill_quantity * request.multiplier
        position = self._positions.get(request.symbol)
        if request.action is OrderAction.BUY and self.cash < notional + fees:
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.REJECTED,
                reason="insufficient buying power",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        if (
            request.action is OrderAction.SELL
            and not self.allow_uncovered_short
            and (position is None or position.quantity < fill_quantity)
        ):
            order = BrokerOrder(
                str(len(self._orders) + 1),
                request,
                OrderStatus.REJECTED,
                reason="uncovered short is disabled",
            )
            self._orders[order.order_id] = order
            self._client_ids[request.client_order_id] = order.order_id
            return order
        self.cash += -notional - fees if request.action is OrderAction.BUY else notional - fees
        signed = fill_quantity if request.action is OrderAction.BUY else -fill_quantity
        if position is None:
            self._positions[request.symbol] = PaperPosition(
                request.symbol, signed, fill_price, request.multiplier
            )
        else:
            position.quantity += signed
            if position.quantity == 0:
                del self._positions[request.symbol]
            elif signed > 0:
                position.average_price = (
                    position.average_price * max(0, position.quantity - signed)
                    + fill_price * signed
                ) / position.quantity
        order_id = str(len(self._orders) + 1)
        fill = Fill(
            order_id,
            request.client_order_id,
            request.symbol,
            request.action,
            fill_quantity,
            fill_price,
            fees,
            datetime.now(UTC),
        )
        status = (
            OrderStatus.FILLED
            if fill_quantity == request.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        order = BrokerOrder(order_id, request, status, fill_quantity, fill)
        self._orders[order_id] = order
        self._client_ids[request.client_order_id] = order_id
        self._equity_snapshots.append((datetime.now(UTC), self.equity()))
        return order

    def cancel(self, order_id: str) -> BrokerOrder:
        if order_id not in self._orders:
            raise KeyError(f"unknown paper order {order_id}")
        order = self._orders[order_id]
        if order.status in {OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED, OrderStatus.REJECTED}:
            return order
        cancelled = BrokerOrder(
            order.order_id,
            order.request,
            OrderStatus.CANCELLED,
            order.filled_quantity,
            order.fill,
            "cancelled by user",
        )
        self._orders[order_id] = cancelled
        return cancelled

    def positions(self) -> Sequence[dict[str, object]]:
        return [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "average_price": p.average_price,
                "multiplier": p.multiplier,
            }
            for p in self._positions.values()
        ]

    def orders(self) -> Sequence[dict[str, object]]:
        """Return a serializable snapshot of paper orders for the API/UI."""

        return [
            {
                "order_id": order.order_id,
                "client_order_id": order.request.client_order_id,
                "symbol": order.request.symbol,
                "action": order.request.action.value,
                "quantity": order.request.quantity,
                "filled_quantity": order.filled_quantity,
                "limit_price": order.request.limit_price,
                "bid": order.request.bid,
                "ask": order.request.ask,
                "multiplier": order.request.multiplier,
                "status": order.status.value,
                "reason": order.reason,
                "submitted_at": order.request.submitted_at.isoformat(),
                "fill": None
                if order.fill is None
                else {
                    "price": order.fill.price,
                    "fees": order.fill.fees,
                    "quantity": order.fill.quantity,
                    "timestamp": order.fill.timestamp.isoformat(),
                },
            }
            for order in self._orders.values()
        ]

    def equity(self, marks: dict[str, float] | None = None) -> float:
        total = self.cash
        for position in self._positions.values():
            mark = (marks or {}).get(position.symbol, position.average_price)
            total += position.quantity * mark * position.multiplier
        return total

    def equity_history(self) -> Sequence[dict[str, object]]:
        """Return recorded in-process equity snapshots for the paper UI."""

        return [
            {"label": timestamp.isoformat(), "value": value}
            for timestamp, value in self._equity_snapshots
        ]
