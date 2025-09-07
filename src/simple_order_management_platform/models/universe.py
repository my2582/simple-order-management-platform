"""Universe data models for asset classification and metadata."""

import pandas as pd
from typing import Dict, List, Optional, Set, Union
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UniverseInstrument:
    """Individual instrument in the universe."""
    
    asset_class: str
    region: str
    instrument_name: str
    ib_symbol: str
    ib_security_type: str
    exchange: str
    currency: str
    instrument_type: str
    instrument: str
    multiplier: Optional[float]
    created_from: str
    created_date: str
    last_updated: str
    used_by_strategies: str
    data_status: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'UniverseInstrument':
        """Create instance from dictionary."""
        return cls(
            asset_class=str(data.get('Asset class', '')),
            region=str(data.get('Region', '')),
            instrument_name=str(data.get('Instrument name', '')),
            ib_symbol=str(data.get('IBSymbol', '')),
            ib_security_type=str(data.get('IBSecurityType', '')),
            exchange=str(data.get('Exchange', '')),
            currency=str(data.get('Currency', '')),
            instrument_type=str(data.get('Type', '')),
            instrument=str(data.get('Instrument', '')),
            multiplier=data.get('Multiplier'),
            created_from=str(data.get('created_from', '')),
            created_date=str(data.get('created_date', '')),
            last_updated=str(data.get('last_updated', '')),
            used_by_strategies=str(data.get('used_by_strategies', '')),
            data_status=str(data.get('data_status', ''))
        )


class UniverseManager:
    """Manager for loading and querying universe data."""
    
    def __init__(self, universes_dir: Union[str, Path] = None):
        """Initialize universe manager.
        
        Args:
            universes_dir: Directory containing universe Excel files
        """
        if universes_dir is None:
            universes_dir = Path("./config/universes")
        
        self.universes_dir = Path(universes_dir)
        self.instruments: Dict[str, UniverseInstrument] = {}
        self.asset_class_mapping: Dict[str, str] = {}
        self._load_all_universes()
    
    def _load_all_universes(self) -> None:
        """Load all universe files from the directory."""
        if not self.universes_dir.exists():
            logger.warning(f"Universe directory not found: {self.universes_dir}")
            return
        
        universe_files = list(self.universes_dir.glob("*universe.xlsx"))
        
        if not universe_files:
            logger.warning(f"No universe files found in: {self.universes_dir}")
            return
        
        for universe_file in universe_files:
            try:
                self._load_universe_file(universe_file)
                logger.info(f"Loaded universe file: {universe_file.name}")
            except Exception as e:
                logger.error(f"Failed to load universe file {universe_file}: {e}")
    
    def _load_universe_file(self, file_path: Path) -> None:
        """Load a single universe Excel file."""
        df = pd.read_excel(file_path)
        
        for _, row in df.iterrows():
            instrument = UniverseInstrument.from_dict(row.to_dict())
            
            # Use IBSymbol as the key (IBKR Symbol identifier)
            if instrument.ib_symbol:
                self.instruments[instrument.ib_symbol] = instrument
                self.asset_class_mapping[instrument.ib_symbol] = instrument.asset_class
    
    def get_instrument(self, ib_symbol: str) -> Optional[UniverseInstrument]:
        """Get instrument by IBKR symbol."""
        return self.instruments.get(ib_symbol)
    
    def get_asset_class(self, ib_symbol: str) -> Optional[str]:
        """Get asset class for IBKR symbol."""
        return self.asset_class_mapping.get(ib_symbol)
    
    def get_instruments_by_asset_class(self, asset_class: str) -> List[UniverseInstrument]:
        """Get all instruments in a specific asset class."""
        return [
            instrument for instrument in self.instruments.values()
            if instrument.asset_class.lower() == asset_class.lower()
        ]
    
    def get_all_asset_classes(self) -> Set[str]:
        """Get all unique asset classes."""
        return set(self.asset_class_mapping.values())
    
    def get_all_ib_symbols(self) -> Set[str]:
        """Get all IBKR symbols in the universe."""
        return set(self.instruments.keys())
    
    def get_universe_summary(self) -> Dict[str, int]:
        """Get summary statistics of the universe."""
        asset_class_counts = {}
        for asset_class in self.asset_class_mapping.values():
            asset_class_counts[asset_class] = asset_class_counts.get(asset_class, 0) + 1
        
        return {
            'total_instruments': len(self.instruments),
            'total_asset_classes': len(self.get_all_asset_classes()),
            'asset_class_breakdown': asset_class_counts
        }
    
    def validate_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """Validate if symbols exist in universe."""
        return {symbol: symbol in self.instruments for symbol in symbols}
    
    def get_missing_symbols(self, symbols: List[str]) -> List[str]:
        """Get list of symbols not found in universe."""
        return [symbol for symbol in symbols if symbol not in self.instruments]


# Global instance for easy access
universe_manager = UniverseManager()


def get_asset_class(ib_symbol: str) -> Optional[str]:
    """Convenience function to get asset class for a symbol."""
    return universe_manager.get_asset_class(ib_symbol)


def get_instrument_info(ib_symbol: str) -> Optional[UniverseInstrument]:
    """Convenience function to get instrument information."""
    return universe_manager.get_instrument(ib_symbol)


def validate_universe_symbols(symbols: List[str]) -> Dict[str, str]:
    """Validate symbols and return their asset classes."""
    result = {}
    for symbol in symbols:
        asset_class = get_asset_class(symbol)
        result[symbol] = asset_class if asset_class else "Unknown"
    
    return result