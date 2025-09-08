"""Refactored stock contract model using ib_insync."""

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
    Simplified stock contract model using ib_insync Stock.
    Leverages ib_insync's smart routing and contract handling.
    """

    asset_class: StockAssetClass = Field(..., description="Asset class of stock contract")
    region: Optional[str] = Field(None, description="Geographic region")
    multiplier: Optional[float] = Field(1.0, description="Contract multiplier")
    primary_exchange: Optional[str] = Field(None, description="Primary exchange for routing")

    @property
    def instrument_type(self) -> InstrumentType:
        return InstrumentType.STOCKS

    def create_ib_contract(self) -> Stock:
        """
        Creates ib_insync stock contract with smart routing.
        ib_insync automatically handles routing complexity.
        """
        # ib_insync Stock object with smart configuration
        stock = Stock(
            symbol=self.symbol,
            exchange=self._get_smart_exchange(),
            currency=self.currency
        )
        
        # Set primary exchange for better routing
        primary_exch = self._get_primary_exchange()
        if primary_exch:
            stock.primaryExchange = primary_exch
            
        return stock
    
    # Keep backward compatibility
    def to_ib_contract(self) -> Stock:
        """Legacy method - use create_ib_contract instead."""
        return self.create_ib_contract()

    def _get_smart_exchange(self) -> str:
        """Get the best exchange for routing - ib_insync pattern."""
        # For US stocks, use SMART routing for better execution
        if self.currency == 'USD' and self.exchange in ['US', 'NASDAQ', 'NYSE', 'ARCA', 'BATS']:
            return 'SMART'
        # For other markets, use the specific exchange
        return self.exchange

    def _get_primary_exchange(self) -> Optional[str]:
        """Get primary exchange for US stocks."""
        if self.currency != 'USD':
            return None
            
        # Use provided primary exchange or derive from exchange
        if self.primary_exchange:
            return self.primary_exchange
            
        # Map exchange to primary exchange
        exchange_mapping = {
            'US': 'NASDAQ',
            'NASDAQ': 'NASDAQ',
            'NYSE': 'NYSE',
            'ARCA': 'ARCA',
            'BATS': 'BATS'
        }
        
        return exchange_mapping.get(self.exchange, 'NASDAQ')

    def get_chart_options(self) -> List[TagValue]:
        """
        Returns stock-specific chart options.
        ib_insync stocks typically don't need special chart options.
        """
        return []  # No special chart options needed for stocks

    def get_market_data_snapshot(self, ib_connection) -> dict:
        """
        Get real-time market data snapshot using ib_insync.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            
        Returns:
            dict: Current market data
        """
        try:
            contract = self.get_ib_contract()
            
            # Request market data - ib_insync handles subscription automatically
            ticker = ib_connection.reqMktData(contract, '', False, False)
            
            # Wait for data or timeout
            ib_connection.sleep(2)  # Give time for data to arrive
            
            return {
                'symbol': self.symbol,
                'last_price': ticker.last,
                'bid': ticker.bid,
                'ask': ticker.ask,
                'bid_size': ticker.bidSize,
                'ask_size': ticker.askSize,
                'volume': ticker.volume,
                'high': ticker.high,
                'low': ticker.low,
                'close': ticker.close,
                'open': ticker.open
            }
            
        except Exception as e:
            return {'symbol': self.symbol, 'error': str(e)}

    def get_contract_details(self, ib_connection) -> dict:
        """
        Get detailed contract information using ib_insync.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            
        Returns:
            dict: Contract details and specifications
        """
        try:
            contract = self.get_ib_contract()
            details = ib_connection.reqContractDetails(contract)
            
            if details:
                detail = details[0]  # Usually only one for stocks
                return {
                    'symbol': contract.symbol,
                    'exchange': contract.exchange,
                    'primary_exchange': contract.primaryExchange,
                    'currency': contract.currency,
                    'sec_type': contract.secType,
                    'con_id': detail.contract.conId,
                    'min_tick': detail.minTick,
                    'price_magnifier': detail.priceMagnifier,
                    'long_name': detail.longName,
                    'industry': detail.industry,
                    'category': detail.category,
                    'subcategory': detail.subcategory,
                    'market_cap': getattr(detail, 'marketCap', None),
                    'trading_hours': detail.tradingHours,
                    'time_zone': detail.timeZoneId
                }
            return {}
            
        except Exception as e:
            return {'error': str(e)}

    def check_market_status(self, ib_connection) -> dict:
        """
        Check if market is open for this stock.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            
        Returns:
            dict: Market status information
        """
        try:
            contract = self.get_ib_contract()
            
            # Get current market data to check if market is active
            ticker = ib_connection.reqMktData(contract, '', True, False)  # Snapshot only
            ib_connection.sleep(1)
            
            # Check if we're getting live data
            is_live = hasattr(ticker, 'last') and ticker.last is not None and ticker.last > 0
            
            return {
                'symbol': self.symbol,
                'is_market_open': is_live,
                'last_price': getattr(ticker, 'last', None),
                'timestamp': ticker.time if hasattr(ticker, 'time') else None
            }
            
        except Exception as e:
            return {'symbol': self.symbol, 'error': str(e), 'is_market_open': False}

    @classmethod
    def from_universe_data(cls, universe_instrument) -> 'StockContract':
        """
        Create StockContract from universe data.
        Simplified creation using ib_insync patterns.
        
        Args:
            universe_instrument: UniverseInstrument object
            
        Returns:
            StockContract instance
        """
        # Determine asset class from universe data
        asset_class = StockAssetClass.ETF if 'ETF' in universe_instrument.instrument_type.upper() else StockAssetClass.EQUITY
        
        return cls(
            symbol=universe_instrument.ib_symbol,
            exchange=universe_instrument.exchange,
            currency=universe_instrument.currency,
            description=universe_instrument.instrument_name,
            original_exchange=universe_instrument.exchange,
            original_currency=universe_instrument.currency,
            asset_class=asset_class,
            region=universe_instrument.region,
            multiplier=universe_instrument.multiplier,
            primary_exchange=None  # Will be derived automatically
        )

    def download_with_fundamentals(self, ib_connection, include_fundamentals: bool = True):
        """
        Download historical data and optionally fundamental data.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            include_fundamentals: Whether to also fetch fundamental data
            
        Returns:
            dict: Downloaded data and fundamental information
        """
        results = {}
        
        # Download historical price data
        success = self.download_historical_data(ib_connection)
        results['historical_data'] = {
            'success': success,
            'data_points': self.data_points,
            'error': self.error_message
        }
        
        if include_fundamentals and success:
            try:
                contract = self.get_ib_contract()
                
                # Request fundamental data (if available)
                fundamental_data = ib_connection.reqFundamentalData(
                    contract, 'ReportSnapshot', []
                )
                
                results['fundamentals'] = {
                    'success': bool(fundamental_data),
                    'data': fundamental_data if fundamental_data else None
                }
                
            except Exception as e:
                results['fundamentals'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results