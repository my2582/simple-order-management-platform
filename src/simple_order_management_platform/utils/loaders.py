"""Enhanced universe and instrument loading utilities."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

from ..models.base import InstrumentType, BaseInstrument
from ..models.futures import FuturesContract, AssetClass
from ..config.loader import config_loader
from ..utils.exceptions import MarketDataPlatformError

logger = logging.getLogger(__name__)


def load_instruments_from_strategy(
    strategy_name: str,
    version: Optional[str] = None,
    instrument_types: Optional[List[InstrumentType]] = None
) -> Dict[InstrumentType, List[BaseInstrument]]:
    """Load instruments for a strategy from universe files."""
    
    if instrument_types is None:
        instrument_types = list(InstrumentType)
    
    logger.info(f"Loading instruments for strategy '{strategy_name}', version: {version}")
    
    try:
        strategy, merged_config, actual_version = config_loader.get_strategy_config(
            strategy_name, version
        )
    except Exception as e:
        raise MarketDataPlatformError(f"Failed to load strategy config: {e}")
    
    logger.info(f"Using strategy version: {actual_version}")
    
    instruments_by_type = {}
    
    for instrument_type in instrument_types:
        try:
            instruments = _load_instruments_by_type(
                instrument_type=instrument_type,
                strategy_config=merged_config,
                strategy_name=strategy_name
            )
            
            if instruments:
                instruments_by_type[instrument_type] = instruments
                logger.info(f"Loaded {len(instruments)} {instrument_type.value} instruments")
            else:
                logger.info(f"No {instrument_type.value} instruments found")
                
        except Exception as e:
            logger.error(f"Failed to load {instrument_type.value} instruments: {e}")
            continue
    
    return instruments_by_type


def _load_instruments_by_type(
    instrument_type: InstrumentType,
    strategy_config,
    strategy_name: str
) -> List[BaseInstrument]:
    """Load instruments of a specific type with flexible column support."""
    
    # Get universe file path
    universe_path = None
    if instrument_type == InstrumentType.FUTURES:
        universe_path = getattr(strategy_config.data_paths, 'futures_universe', None)
    elif instrument_type == InstrumentType.STOCKS:
        universe_path = getattr(strategy_config.data_paths, 'stocks_universe', None)
    elif instrument_type == InstrumentType.ETFS:
        universe_path = getattr(strategy_config.data_paths, 'etfs_universe', None)
    
    if not universe_path:
        logger.debug(f"No universe file configured for {instrument_type.value}")
        return []
    
    universe_file = Path(universe_path)
    if not universe_file.exists():
        logger.warning(f"Universe file not found: {universe_path}")
        return []
    
    try:
        df = _load_universe_file(universe_file)
        logger.debug(f"Loaded universe file: {universe_file.name} ({len(df)} rows)")
    except Exception as e:
        raise MarketDataPlatformError(f"Failed to read universe file {universe_path}: {e}")
    
    # Filter by instrument type if Type column exists
    if 'Type' in df.columns:
        type_filter = 'Futures' if instrument_type == InstrumentType.FUTURES else instrument_type.value.title()
        df = df[df['Type'].astype(str).str.contains(type_filter, case=False, na=False)].copy()
    
    if df.empty:
        logger.info(f"No {instrument_type.value} found in universe file")
        return []
    
    # Convert to instrument objects
    instruments = []
    corrections = config_loader.load_strategies_config().corrections
    
    for _, row in df.iterrows():
        try:
            instrument = _create_instrument(
                row=row,
                instrument_type=instrument_type,
                strategy_config=strategy_config,
                corrections=corrections
            )
            instruments.append(instrument)
            
        except Exception as e:
            symbol = row.get('IBSymbol') or row.get('Symbol', 'Unknown')
            logger.warning(f"Failed to create {instrument_type.value} instrument {symbol}: {e}")
            continue
    
    return instruments


def _load_universe_file(file_path: Path) -> pd.DataFrame:
    """Load universe file with flexible format support."""
    
    if file_path.suffix.lower() == '.csv':
        df = pd.read_csv(file_path)
    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _create_instrument(row, instrument_type: InstrumentType, strategy_config, corrections):
    """Create instrument object with flexible column name support."""
    
    # Flexible symbol extraction (supports both IBSymbol and Symbol)
    symbol = str(row.get('IBSymbol') or row.get('Symbol', '')).strip()
    
    # Flexible exchange/currency extraction (supports both plain and IB-prefixed columns)
    original_exchange = str(row.get('Exchange') or row.get('IBExchange', '')).strip()
    original_currency = str(row.get('Currency') or row.get('IBCurrency', '')).strip()
    
    # Flexible multiplier extraction
    raw_multiplier = row.get('Multiplier', row.get('IBMultiplier', 1))
    multiplier = float(raw_multiplier) if pd.notna(raw_multiplier) else 1.0
    
    # Description
    description = str(row.get('Instrument name') or row.get('Description', symbol)).strip()
    
    # Apply corrections (including symbol overrides)
    instrument_corrections = getattr(corrections, instrument_type.value, None)
    if instrument_corrections:
        exchange_overrides = getattr(instrument_corrections, 'exchange_overrides', {})
        currency_corrections = getattr(instrument_corrections, 'currency_corrections', {})
        symbol_overrides = getattr(instrument_corrections, 'symbol_overrides', {})
    else:
        exchange_overrides = {}
        currency_corrections = {}
        symbol_overrides = {}
    
    # Apply symbol override first (Excel is primary, overrides are corrections)
    final_symbol = symbol_overrides.get(symbol, symbol)
    corrected_exchange = exchange_overrides.get(final_symbol, original_exchange)
    corrected_currency = currency_corrections.get(final_symbol, original_currency)
    
    # Common fields
    common_fields = {
        'symbol': final_symbol,
        'exchange': corrected_exchange,
        'currency': corrected_currency,
        'original_exchange': original_exchange,
        'original_currency': original_currency,
        'description': description,
        'multiplier': multiplier,
    }
    
    # Apply instrument-specific settings
    instrument_settings = getattr(strategy_config, 'instrument_settings', {})
    type_settings = instrument_settings.get(instrument_type.value, {})
    
    if type_settings:
        common_fields.update({
            'duration': type_settings.get('duration', '2 Y'),
            'bar_size': type_settings.get('bar_size', '1 day'),
            'use_rth': type_settings.get('use_rth', True),
        })
    
    # Create instrument-specific objects
    if instrument_type == InstrumentType.FUTURES:
        asset_class_str = str(row.get('Asset class') or row.get('AssetClass', 'Equity'))
        try:
            asset_class = AssetClass(asset_class_str)
        except ValueError:
            asset_class = AssetClass.EQUITY
        
        return FuturesContract(
            **common_fields,
            asset_class=asset_class,
            region=str(row.get('Region', '')) if pd.notna(row.get('Region')) else None,
            back_adjusted=type_settings.get('back_adjusted', True)
        )
    
    else:
        raise ValueError(f"Instrument type {instrument_type.value} not yet implemented")
