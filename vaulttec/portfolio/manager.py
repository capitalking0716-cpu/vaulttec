"""Portfolio manager — holdings, P&L, allocation. Paper money only."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Holding:
    symbol: str
    quantity: float
    avg_cost: float


@dataclass
class Portfolio:
    cash: float
    holdings: dict = field(default_factory=dict)  # symbol -> Holding

    def value(self, prices: dict) -> float:
        total = self.cash
        for symbol, h in self.holdings.items():
            total += h.quantity * prices.get(symbol, h.avg_cost)
        return total

    def exposure(self, prices: dict) -> float:
        return sum(h.quantity * prices.get(s, h.avg_cost) for s, h in self.holdings.items())

    def buy(self, symbol: str, quantity: float, price: float) -> None:
        cost = quantity * price
        if cost > self.cash:
            raise ValueError("Not enough virtual cash for this paper trade.")
        self.cash -= cost
        if symbol in self.holdings:
            h = self.holdings[symbol]
            h.avg_cost = (h.avg_cost * h.quantity + cost) / (h.quantity + quantity)
            h.quantity += quantity
        else:
            self.holdings[symbol] = Holding(symbol, quantity, price)

    def sell(self, symbol: str, quantity: float, price: float) -> float:
        """Sell a holding; returns realised P&L on the sold shares."""
        h = self.holdings.get(symbol)
        if h is None or h.quantity < quantity:
            raise ValueError("Not enough shares to sell.")
        pnl = (price - h.avg_cost) * quantity
        h.quantity -= quantity
        if h.quantity == 0:
            del self.holdings[symbol]
        self.cash += quantity * price
        return pnl

    def allocation(self, prices: dict) -> dict:
        total = self.value(prices)
        if total <= 0:
            return {}
        return {s: round(h.quantity * prices.get(s, h.avg_cost) / total * 100, 1)
                for s, h in self.holdings.items()}
