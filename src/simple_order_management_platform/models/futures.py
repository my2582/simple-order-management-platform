"""Futures contract specific model."""

from enum import Enum
from typing import List, Optional
from ib_insync import ContFuture, TagValue
from pydantic import Field

from .base import BaseInstrument, InstrumentType


class AssetClass(str, Enum):
    """Asset classes for futures contracts."""
    EQUITY = "Equity"
    BONDS = "Bonds"
    COMMODITY = "Commodity"
    CURRENCY = "Currency"


class FuturesContract(BaseInstrument):
    """
    Futures contract model with back-adjustment support.
    """

    asset_class: AssetClass = Field(..., description="Asset class of futures contract")
    region: Optional[str] = Field(None, description="Geographic region")
    multiplier: Optional[float] = Field(1.0, description="Contract multiplier")

    # Futures-specific settings
    back_adjusted: Optional[bool] = Field(None, description="Use back-adjusted data")

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.FUTURES

    def to_ib_contract(self) -> ContFuture:
        """Creates IB continuous futures contract."""
        return ContFuture(
            symbol=self.symbol,
            exchange=self.exchange,
            currency=self.currency
        )

    def get_chart_options(self) -> List[TagValue]:
        """
        Returns futures-specific chart options.
        Continuous futures (ContFuture) are inherently back-adjusted.
        No chartOptions are needed or supported for back-adjustment.
        """
        return []  # Empty list - no chart options needed for continuous futures
