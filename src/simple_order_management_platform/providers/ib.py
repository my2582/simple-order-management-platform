"""Interactive Brokers data provider implementation."""

import time
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any
import pandas as pd
from ib_insync import util, IB, Stock
import logging

from .base import BaseProvider
from ..models.base import BaseInstrument, InstrumentType, ProcessingStatus
from ..core.connector import IBConnector

logger = logging.getLogger(__name__)


class IBProvider(BaseProvider):
    """
    Interactive Brokers implementation of BaseProvider.
    Handles validation and data download via IB API with instrument-specific optimizations.
    """

    def __init__(self, connector: IBConnector):
        self.connector = connector
        self.ib: IB = connector.ib

    @property
    def name(self) -> str:
        return "Interactive Brokers"

    def supports(self, instrument: BaseInstrument) -> bool:
        """Check if IB supports the instrument type."""
        supported_types = {
            InstrumentType.FUTURES,
            InstrumentType.STOCKS,
            InstrumentType.ETFS
        }
        return instrument.instrument_type in supported_types

    def health_check(self) -> bool:
        """Check if IB connection is healthy."""
        return self.connector.is_connected()

    def validate_instrument(self, instrument: BaseInstrument) -> bool:
        """Validate instrument against IB system."""
        try:
            ib_contract = instrument.to_ib_contract()
            contract_details = self.ib.reqContractDetails(ib_contract)

            if contract_details:
                logger.info(f"✓ [{instrument.symbol}] Contract validation successful")
                instrument.status = ProcessingStatus.VALIDATED
                return True
            else:
                logger.warning(f"✗ [{instrument.symbol}] Contract not found")
                instrument.status = ProcessingStatus.FAILED
                instrument.error_message = "Contract not found"
                return False

        except Exception as e:
            logger.error(f"✗ [{instrument.symbol}] Validation failed: {e}")
            instrument.status = ProcessingStatus.FAILED
            instrument.error_message = f"Validation error: {str(e)}"
            return False

    def download_data(
        self,
        instrument: BaseInstrument,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
        """Download historical data for single instrument with instrument-specific optimizations."""

        instrument.status = ProcessingStatus.DOWNLOADING
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                logger.info(f"[{instrument.symbol}] Downloading {instrument.instrument_type.value} data "
                           f"(attempt {attempt + 1}/{max_retries})")

                # Get IB contract and instrument-specific options
                ib_contract = instrument.to_ib_contract()
                chart_options = instrument.get_chart_options()

                # Instrument-specific whatToShow selection
                what_to_show = self._get_what_to_show(instrument)

                # Request historical data with instrument-specific settings
                bars = self.ib.reqHistoricalData(
                    ib_contract,
                    endDateTime='',
                    durationStr=instrument.duration,
                    barSizeSetting=instrument.bar_size,
                    whatToShow=what_to_show,
                    useRTH=instrument.use_rth,
                    formatDate=1,
                    chartOptions=chart_options
                )

                if not bars:
                    if attempt < max_retries - 1:
                        logger.warning(f"[{instrument.symbol}] No data, retrying in {retry_delay}s")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"No data available for {instrument.symbol}")

                # Convert to DataFrame and clean
                df = util.df(bars)
                df = df.drop(columns=['average', 'barCount'], errors='ignore')

                # Set date as index
                if 'date' in df.columns:
                    df.set_index('date', inplace=True)

                # Data quality check
                if len(df) < 10:
                    if attempt < max_retries - 1:
                        logger.warning(f"[{instrument.symbol}] Insufficient data ({len(df)} points), retrying")
                        time.sleep(retry_delay)
                        continue

                # Success - update instrument status
                instrument.status = ProcessingStatus.SUCCESS
                instrument.data_points = len(df)
                instrument.download_time = datetime.now()

                duration = time.time() - start_time
                logger.info(f"[{instrument.symbol}] ✓ Download successful: {len(df)} points in {duration:.2f}s")
                return True, df, None

            except Exception as e:
                error_msg = f"Download error (attempt {attempt + 1}): {str(e)}"
                logger.error(f"[{instrument.symbol}] {error_msg}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    instrument.status = ProcessingStatus.FAILED
                    instrument.error_message = error_msg
                    return False, None, error_msg

        return False, None, "Unexpected error in download loop"

    def _get_what_to_show(self, instrument: BaseInstrument) -> str:
        """
        Determine the appropriate 'whatToShow' parameter based on instrument type.
        """
        
        if instrument.instrument_type == InstrumentType.FUTURES:
            return 'TRADES'
        elif instrument.instrument_type in (InstrumentType.STOCKS, InstrumentType.ETFS):
            return 'ADJUSTED_LAST'
        else:
            logger.warning(f"Unknown instrument type {instrument.instrument_type}, using TRADES")
            return 'TRADES'
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current prices for a list of symbols using universe data.
        
        Args:
            symbols: List of symbol strings to get prices for
            
        Returns:
            Dictionary mapping symbol -> price data
        """
        prices_dict = {}
        
        # Import universe manager
        from ..models.universe import universe_manager
        
        for symbol in symbols:
            try:
                # Get instrument info from universe
                instrument = universe_manager.get_instrument(symbol)
                if not instrument:
                    logger.warning(f"Symbol {symbol} not found in universe, skipping")
                    continue
                
                # Create appropriate contract based on instrument type
                contract = self._create_contract_from_universe(instrument)
                if not contract:
                    logger.warning(f"Could not create contract for {symbol}, skipping")
                    continue
                
                # Get market data
                ticker = self.ib.reqMktData(contract, '', False, False)
                
                # Wait for data (shorter wait time for efficiency)
                self.ib.sleep(1)
                
                # Get the price
                close_price = ticker.marketPrice()
                if close_price and close_price > 0:
                    prices_dict[symbol] = {
                        'close_price': float(close_price),
                        'currency': instrument.currency,
                        'data_date': datetime.now().date().isoformat()
                    }
                    logger.debug(f"Got price for {symbol}: {close_price} {instrument.currency}")
                else:
                    # Try last price or close price
                    last_price = ticker.last
                    if last_price and last_price > 0:
                        prices_dict[symbol] = {
                            'close_price': float(last_price),
                            'currency': instrument.currency,
                            'data_date': datetime.now().date().isoformat()
                        }
                        logger.debug(f"Got last price for {symbol}: {last_price} {instrument.currency}")
                    else:
                        logger.warning(f"No valid price data for {symbol}")
                
                # Cancel market data
                self.ib.cancelMktData(contract)
                
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")
                continue
        
        return prices_dict
    
    def _create_contract_from_universe(self, instrument) -> Optional[Any]:
        """Create appropriate IB contract from universe instrument data."""
        try:
            from ib_insync import Stock, Future, Option, Index
            
            symbol = instrument.ib_symbol
            exchange = instrument.exchange
            currency = instrument.currency
            asset_class = instrument.asset_class.lower()
            
            if asset_class in ['equity', 'etf']:
                return Stock(symbol, exchange, currency)
            elif asset_class in ['commodity', 'futures']:
                # For futures, we may need additional parsing
                return Future(symbol, exchange, currency)
            elif asset_class == 'bonds':
                # Bonds might be handled differently
                return Stock(symbol, exchange, currency)  # Fallback to stock for now
            elif asset_class == 'option':
                # Options need special parsing - for now skip complex options
                logger.debug(f"Skipping option symbol {symbol} - complex parsing required")
                return None
            else:
                # Default to stock
                return Stock(symbol, exchange, currency)
                
        except Exception as e:
            logger.warning(f"Error creating contract for {instrument.ib_symbol}: {e}")
            return None
