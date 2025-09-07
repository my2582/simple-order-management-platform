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
        active_tickers = []
        
        # Import universe manager
        from ..models.universe import universe_manager
        
        logger.info(f"Starting price download for {len(symbols)} symbols")
        
        # First, create all contracts and request market data
        symbol_to_ticker = {}
        
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
                
                # Validate contract first
                try:
                    contract_details = self.ib.reqContractDetails(contract)
                    if not contract_details:
                        logger.warning(f"Contract validation failed for {symbol}, trying qualified contract")
                        # Try to qualify the contract
                        qualified_contracts = self.ib.qualifyContracts(contract)
                        if not qualified_contracts:
                            logger.warning(f"Could not qualify contract for {symbol}, skipping")
                            continue
                        contract = qualified_contracts[0]
                        logger.info(f"Using qualified contract for {symbol}: {contract}")
                    else:
                        logger.debug(f"Contract validated for {symbol}")
                except Exception as e:
                    logger.warning(f"Contract validation error for {symbol}: {e}, skipping")
                    continue
                
                # Request market data - try delayed data if real-time fails
                # Use empty string for generic ticks, snapshot=False for streaming
                ticker = self.ib.reqMktData(contract, '', False, False)
                if ticker:
                    symbol_to_ticker[symbol] = (ticker, instrument)
                    active_tickers.append(ticker)
                    logger.debug(f"Requested market data for {symbol}")
                else:
                    logger.warning(f"Failed to request market data for {symbol}")
                
            except Exception as e:
                logger.warning(f"Failed to setup market data for {symbol}: {e}")
                continue
        
        if not active_tickers:
            logger.error("No valid contracts created for any symbols")
            return prices_dict
        
        # Wait for market data to populate
        logger.info(f"Waiting for market data for {len(active_tickers)} contracts...")
        
        # Use progressive waiting with multiple checks
        for wait_round in range(3):
            self.ib.sleep(1)  # Wait 1 second at a time
            # Check if we have any data yet
            data_count = sum(1 for _, (ticker, _) in symbol_to_ticker.items() 
                           if hasattr(ticker, 'last') and ticker.last and not str(ticker.last).lower() in ['nan', 'none'])
            logger.debug(f"Wait round {wait_round + 1}: {data_count}/{len(symbol_to_ticker)} tickers have data")
            if data_count > len(symbol_to_ticker) * 0.3:  # If 30% have data, proceed
                break
        
        # Collect prices
        for symbol, (ticker, instrument) in symbol_to_ticker.items():
            try:
                # Try multiple price sources with better validation
                price = None
                price_source = None
                
                # Helper function to validate price
                def is_valid_price(p):
                    try:
                        return p is not None and float(p) > 0 and str(p).lower() not in ['nan', 'none', 'inf', '-inf']
                    except (ValueError, TypeError):
                        return False
                
                # 1. Try last traded price (most reliable)
                if hasattr(ticker, 'last') and is_valid_price(ticker.last):
                    price = float(ticker.last)
                    price_source = 'last'
                
                # 2. Try market price (mid price)
                elif hasattr(ticker, 'marketPrice'):
                    try:
                        market_price = ticker.marketPrice()
                        if is_valid_price(market_price):
                            price = float(market_price)
                            price_source = 'market'
                    except Exception:
                        pass
                
                # 3. Try close price
                elif hasattr(ticker, 'close') and is_valid_price(ticker.close):
                    price = float(ticker.close)
                    price_source = 'close'
                
                # 4. Try bid/ask midpoint
                elif (hasattr(ticker, 'bid') and hasattr(ticker, 'ask') and 
                      is_valid_price(ticker.bid) and is_valid_price(ticker.ask)):
                    price = (float(ticker.bid) + float(ticker.ask)) / 2
                    price_source = 'bid_ask_mid'
                
                # 5. Try delayed prices (for subscription issues)
                elif hasattr(ticker, 'delayedLast') and is_valid_price(ticker.delayedLast):
                    price = float(ticker.delayedLast)
                    price_source = 'delayed_last'
                
                elif hasattr(ticker, 'delayedClose') and is_valid_price(ticker.delayedClose):
                    price = float(ticker.delayedClose)
                    price_source = 'delayed_close'
                
                if price and price > 0:
                    prices_dict[symbol] = {
                        'close_price': float(price),
                        'currency': instrument.currency,
                        'data_date': datetime.now().date().isoformat(),
                        'price_source': price_source
                    }
                    logger.info(f"✓ {symbol}: {price:.4f} {instrument.currency} ({price_source})")
                else:
                    # Provide detailed debug info for failed symbols
                    debug_info = {
                        'last': getattr(ticker, 'last', 'N/A'),
                        'bid': getattr(ticker, 'bid', 'N/A'),
                        'ask': getattr(ticker, 'ask', 'N/A'),
                        'close': getattr(ticker, 'close', 'N/A'),
                        'delayed_last': getattr(ticker, 'delayedLast', 'N/A'),
                        'contract': str(ticker.contract)
                    }
                    logger.warning(f"✗ {symbol}: No valid price data available. Debug: {debug_info}")
                
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")
                continue
        
        # Cancel all market data subscriptions
        for ticker, _ in symbol_to_ticker.values():
            try:
                self.ib.cancelMktData(ticker.contract)
            except Exception as e:
                logger.debug(f"Error canceling market data: {e}")
        
        success_rate = len(prices_dict) / len(symbols) * 100 if symbols else 0
        logger.info(f"Price download completed: {len(prices_dict)}/{len(symbols)} symbols ({success_rate:.1f}% success rate)")
        
        return prices_dict
    
    def _create_contract_from_universe(self, instrument) -> Optional[Any]:
        """Create appropriate IB contract from universe instrument data."""
        try:
            from ib_insync import Stock, Future, Option, Index, Contract
            
            symbol = instrument.ib_symbol
            security_type = instrument.ib_security_type
            exchange = self._normalize_exchange_name(instrument.exchange, security_type)
            currency = instrument.currency
            asset_class = instrument.asset_class.lower()
            
            logger.debug(f"Creating contract for {symbol}: class={asset_class}, type={security_type}, exchange={exchange}")
            
            # Handle different asset classes based on security type FIRST (more specific)
            if security_type == 'FUT':
                # Futures - try multiple approaches for IBKR compatibility
                try:
                    # Method 1: Try with symbol as continuous contract
                    contract = Future(symbol=symbol, exchange=exchange, currency=currency)
                    logger.debug(f"Created Future contract with symbol: {contract}")
                    return contract
                except Exception:
                    try:
                        # Method 2: Try with localSymbol for continuous futures
                        contract = Future(localSymbol=symbol, exchange=exchange, currency=currency)
                        logger.debug(f"Created Future contract with localSymbol: {contract}")
                        return contract
                    except Exception:
                        # Method 3: Generic contract for complex futures
                        contract = Contract()
                        contract.symbol = symbol
                        contract.secType = 'FUT'
                        contract.exchange = exchange
                        contract.currency = currency
                        logger.debug(f"Created generic Future contract: {contract}")
                        return contract
                
            elif security_type == 'STK' or asset_class in ['equity', 'etf']:
                # Stocks and ETFs - use SMART routing for better success
                if exchange in ['US', 'NASDAQ', 'ARCA'] and currency == 'USD':
                    contract = Stock(symbol, 'SMART', currency)
                    contract.primaryExchange = exchange if exchange != 'US' else 'NASDAQ'
                else:
                    contract = Stock(symbol, exchange, currency)
                logger.debug(f"Created Stock contract: {contract}")
                return contract
                
            elif security_type == 'IND' or asset_class == 'index':
                # Index
                contract = Index(symbol, exchange, currency)
                logger.debug(f"Created Index contract: {contract}")
                return contract
                
            elif security_type == 'OPT' or asset_class == 'option':
                # Options - skip for now as they need strike, expiry, etc.
                logger.debug(f"Skipping option symbol {symbol} - requires strike/expiry data")
                return None
                
            elif security_type == 'BOND' or asset_class == 'bonds':
                # Bonds - try as generic contract first
                contract = Contract()
                contract.symbol = symbol
                contract.secType = 'BOND'
                contract.exchange = exchange
                contract.currency = currency
                logger.debug(f"Created Bond contract: {contract}")
                return contract
                
            elif security_type == 'CASH' or asset_class == 'forex':
                # Forex
                contract = Contract()
                contract.symbol = symbol
                contract.secType = 'CASH'
                contract.exchange = 'IDEALPRO'  # Standard forex exchange
                contract.currency = currency
                logger.debug(f"Created Forex contract: {contract}")
                return contract
                
            else:
                # Try to guess from symbol patterns or default to stock
                logger.warning(f"Unknown security type '{security_type}' for {symbol}, defaulting to Stock")
                contract = Stock(symbol, exchange, currency)
                return contract
                
        except Exception as e:
            logger.warning(f"Error creating contract for {instrument.ib_symbol}: {e}")
            return None
    
    def _normalize_exchange_name(self, exchange: str, security_type: str = None) -> str:
        """Normalize exchange names to IBKR expected values."""
        # Handle problematic 'US' exchange for stocks
        if exchange == 'US' and security_type in ['STK', 'FUND']:
            return 'SMART'  # Use SMART routing for generic US exchange
        
        exchange_mapping = {
            'NASDAQ': 'NASDAQ',
            'NYSE': 'NYSE', 
            'ARCA': 'ARCA',
            'BATS': 'BATS',
            'SMART': 'SMART',
            'US': 'SMART',  # Map US to SMART routing
            'CME': 'CME',
            'CBOT': 'CBOT',
            'NYMEX': 'NYMEX',
            'COMEX': 'COMEX',
            'ICE': 'ICE',
            'EUREX': 'EUREX',
            'SGX': 'SGX',
            'OSE': 'OSE',
            'OSE.JPN': 'OSE.JPN',
            'TSE': 'TSE',
            'XETR': 'XETR',
            'LSE': 'LSE',
            'LSEETF': 'LSEETF',
            'HKFE': 'HKFE'
        }
        
        # First try exact match
        if exchange in exchange_mapping:
            return exchange_mapping[exchange]
        
        # Then try uppercase match
        return exchange_mapping.get(exchange.upper(), 'SMART')