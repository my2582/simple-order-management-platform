"""Stock contract specific model."""

from enum import Enum
from typing import List, Optional
from ib_insync import Stock, TagValue
from pydantic import Field

from .base import BaseInstrument, InstrumentType


class StockAssetClass(str, Enum):
    """Asset classes for stock contracts."""
    EQUITY = "Equity"
    ETF = "ETF"


class StockContract(BaseInstrument):
    """
    Stock contract model for equities and ETFs.
    """

    asset_class: StockAssetClass = Field(..., description="Asset class of stock contract")
    region: Optional[str] = Field(None, description="Geographic region")
    multiplier: Optional[float] = Field(1.0, description="Contract multiplier")
    primary_exchange: Optional[str] = Field(None, description="Primary exchange for routing")

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.STOCKS

    def to_ib_contract(self) -> Stock:
        """Creates IB stock contract."""
        # For US stocks, use SMART routing with primary exchange
        if self.currency == 'USD' and self.exchange in ['US', 'NASDAQ', 'NYSE', 'ARCA', 'BATS']:
            # Use SMART routing for better execution
            exchange = 'SMART'
            primary_exchange = self.primary_exchange or self.exchange
            
            # Map generic 'US' to specific primary exchange
            if primary_exchange == 'US':
                primary_exchange = 'NASDAQ'  # Default to NASDAQ for generic US
                
            contract = Stock(
                symbol=self.symbol,
                exchange=exchange,
                currency=self.currency
            )
            contract.primaryExchange = primary_exchange
            return contract
        else:
            # For non-US stocks, use the exchange directly
            return Stock(
                symbol=self.symbol,
                exchange=self.exchange,
                currency=self.currency
            )

    def get_chart_options(self) -> List[TagValue]:
        """
        Returns stock-specific chart options.
        For stocks, we typically don't need special chart options.
        """
        return []  # Empty list - no special chart options needed for stocks