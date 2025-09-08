"""Refactored futures contract model using ib_insync."""

from enum import Enum
from typing import List, Optional
from ib_insync import ContFuture, Future, TagValue
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
    Simplified futures contract model using ib_insync ContFuture.
    Leverages ib_insync's built-in continuous futures handling.
    """

    asset_class: AssetClass = Field(..., description="Asset class of futures contract")
    region: Optional[str] = Field(None, description="Geographic region")
    multiplier: Optional[float] = Field(1.0, description="Contract multiplier")

    # Futures-specific settings - simplified since ContFuture is inherently back-adjusted
    back_adjusted: Optional[bool] = Field(True, description="Use back-adjusted data (always True for ContFuture)")

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.FUTURES

    def create_ib_contract(self) -> ContFuture:
        """
        Creates ib_insync continuous futures contract.
        Much simpler than manual contract creation - ib_insync handles all complexity.
        """
        return ContFuture(
            symbol=self.symbol,
            exchange=self.exchange,
            currency=self.currency
        )
    
    # Keep backward compatibility
    def to_ib_contract(self) -> ContFuture:
        """Legacy method - use create_ib_contract instead."""
        return self.create_ib_contract()

    def get_chart_options(self) -> List[TagValue]:
        """
        Returns futures-specific chart options.
        ib_insync ContFuture automatically handles back-adjustment,
        so no special chart options needed.
        """
        return []  # ib_insync handles back-adjustment automatically

    def get_contract_details(self, ib_connection) -> dict:
        """
        Get detailed contract information using ib_insync.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            
        Returns:
            dict: Contract details including specifications
        """
        try:
            contract = self.get_ib_contract()
            details = ib_connection.reqContractDetails(contract)
            
            if details:
                detail = details[0]  # First match
                return {
                    'symbol': contract.symbol,
                    'exchange': contract.exchange,
                    'currency': contract.currency,
                    'multiplier': detail.contract.multiplier,
                    'min_tick': detail.minTick,
                    'price_magnifier': detail.priceMagnifier,
                    'long_name': detail.longName,
                    'contract_month': getattr(detail.contract, 'lastTradeDateOrContractMonth', ''),
                    'trading_hours': detail.tradingHours,
                    'time_zone': detail.timeZoneId
                }
            return {}
            
        except Exception as e:
            return {'error': str(e)}

    def get_front_month_contract(self, ib_connection):
        """
        Get the current front month contract for this continuous future.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            
        Returns:
            Contract: Front month futures contract
        """
        try:
            # ib_insync can help us find the front month contract
            
            # Create a generic future contract to find available contracts
            future = Future(
                symbol=self.symbol,
                exchange=self.exchange,
                currency=self.currency
            )
            
            # Get contract details to find available expiries
            details = ib_connection.reqContractDetails(future)
            
            if details:
                # Sort by expiry date to get front month
                sorted_details = sorted(
                    details,
                    key=lambda d: d.contract.lastTradeDateOrContractMonth
                )
                return sorted_details[0].contract
                
            return None
            
        except Exception as e:
            print(f"Error getting front month contract: {e}")
            return None

    @classmethod
    def from_universe_data(cls, universe_instrument) -> 'FuturesContract':
        """
        Create FuturesContract from universe data.
        Simplified creation using ib_insync patterns.
        
        Args:
            universe_instrument: UniverseInstrument object
            
        Returns:
            FuturesContract instance
        """
        return cls(
            symbol=universe_instrument.ib_symbol,
            exchange=universe_instrument.exchange,
            currency=universe_instrument.currency,
            description=universe_instrument.instrument_name,
            original_exchange=universe_instrument.exchange,
            original_currency=universe_instrument.currency,
            asset_class=AssetClass(universe_instrument.asset_class),
            region=universe_instrument.region,
            multiplier=universe_instrument.multiplier
        )

    def download_with_rollover_data(self, ib_connection, include_individual_months: bool = False):
        """
        Download both continuous and individual month data.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            include_individual_months: Whether to also download individual month contracts
            
        Returns:
            dict: Downloaded data for continuous and optionally individual contracts
        """
        results = {}
        
        # Download continuous contract data
        success = self.download_historical_data(ib_connection)
        results['continuous'] = {
            'success': success,
            'data_points': self.data_points,
            'error': self.error_message
        }
        
        if include_individual_months:
            # Get front month contract and download its data
            front_month = self.get_front_month_contract(ib_connection)
            
            if front_month:
                try:
                    bars = ib_connection.reqHistoricalData(
                        contract=front_month,
                        endDateTime='',
                        durationStr=self.duration,
                        barSizeSetting=self.bar_size,
                        whatToShow='TRADES',
                        useRTH=self.use_rth,
                        formatDate=1
                    )
                    
                    results['front_month'] = {
                        'success': bool(bars),
                        'data_points': len(bars) if bars else 0,
                        'contract': front_month.lastTradeDateOrContractMonth,
                        'symbol': front_month.localSymbol
                    }
                    
                except Exception as e:
                    results['front_month'] = {
                        'success': False,
                        'error': str(e)
                    }
        
        return results
