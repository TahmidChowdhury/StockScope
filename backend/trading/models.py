from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.services.research import normalized_symbol


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Costs(Input):
    slippage_bps: float = Field(default=5, ge=0, le=500)
    spread_bps: float = Field(default=2, ge=0, le=500, description="Full bid-ask spread; half charged per side")
    commission: float = Field(default=0, ge=0, le=100)

    @property
    def impact(self):
        return (self.slippage_bps + self.spread_bps / 2) / 10000


class PortfolioInput(Input):
    name: str = Field(min_length=1, max_length=80)
    initial_cash: float = Field(default=10000, ge=100, le=100000000)
    benchmark: str = "SPY"
    costs: Costs = Field(default_factory=Costs)

    @field_validator("benchmark")
    @classmethod
    def symbol(cls, value):
        return normalized_symbol(value)

    @field_validator("name")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


class OrderInput(Input):
    client_order_id: str = Field(pattern=r"^[a-zA-Z0-9-]{8,80}$")
    symbol: str
    side: Literal["buy", "sell"]
    budget: float = Field(default=1000, ge=1, le=100000000)
    thesis: str = Field(min_length=1, max_length=2000)

    @field_validator("symbol")
    @classmethod
    def symbol_key(cls, value):
        return normalized_symbol(value)

    @field_validator("thesis")
    @classmethod
    def reason(cls, value):
        if not value.strip():
            raise ValueError("Record your reason before submitting")
        return value.strip()


class BacktestNameInput(Input):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def trimmed_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class BacktestInput(Input):
    name: Optional[str] = Field(default=None, max_length=80)
    strategy: Literal["buy_hold", "sma", "congress"] = "buy_hold"
    start: date
    end: date
    initial_cash: float = Field(default=10000, ge=100, le=100000000)
    benchmark: str = "SPY"
    symbols: list[str] = Field(default_factory=lambda: ["AAPL"], max_length=20)
    costs: Costs = Field(default_factory=Costs)
    fast_window: int = Field(default=20, ge=2, le=100)
    slow_window: int = Field(default=50, ge=3, le=250)
    member: str = Field(default="", max_length=150)
    trade_fraction: float = Field(default=0.1, gt=0, le=1)
    max_weight: float = Field(default=0.25, gt=0, le=1)
    disclosure_delay_days: int = Field(default=0, ge=0, le=90)
    allow_estimated_disclosure_dates: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def optional_name(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("symbols")
    @classmethod
    def unique_symbols(cls, values):
        return list(dict.fromkeys(normalized_symbol(v) for v in values))

    @field_validator("benchmark")
    @classmethod
    def benchmark_symbol(cls, value):
        return normalized_symbol(value)

    @model_validator(mode="after")
    def coherent(self):
        from backend.trading.market import market_today
        if self.end >= market_today():
            raise ValueError("End must precede today in New York; only completed daily sessions are supported")
        if self.end <= self.start or (self.end - self.start).days > 3660:
            raise ValueError("Choose an ordered date range of at most ten years")
        if self.strategy != "congress" and not self.symbols:
            raise ValueError("Choose at least one stock symbol")
        if self.strategy == "sma" and self.fast_window >= self.slow_window:
            raise ValueError("Fast window must be shorter than slow window")
        if self.strategy == "sma" and len(self.symbols) != 1:
            raise ValueError("SMA supports one stock per test")
        if self.strategy == "congress" and not self.member.strip():
            raise ValueError("Choose one member for a Congress test")
        return self


class CongressImport(Input):
    csv_text: str = Field(min_length=1, max_length=2000000)

    @field_validator("csv_text")
    @classmethod
    def byte_limit(cls, value):
        if len(value.encode("utf-8")) > 2000000:
            raise ValueError("CSV must be at most 2 MB of UTF-8 text")
        return value
