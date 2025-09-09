"""Enhanced master universe data management with robust file handling."""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import importlib.util

from ..models.base import InstrumentType
from ..models.futures import FuturesContract, AssetClass
from ..providers.base import BaseProvider
from ..config.loader import config_loader

logger = logging.getLogger(__name__)


class MasterUniverseManager:
    """Manages master universe data and centralized storage."""
    
    def __init__(self):
        self.master_dir = Path("config/universes")
        self.data_dir = Path("data/master") 
        self.metadata_dir = Path("data/metadata")
        
        # Create directories
        for dir_path in [self.master_dir, self.data_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def load_master_universe(self, asset_type: str) -> pd.DataFrame:
        """Load master universe for asset type with type filtering."""
        file_path = self.master_dir / f"{asset_type}_master_universe.xlsx"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Master universe not found: {file_path}")
        
        df = pd.read_excel(file_path)
        
        # Filter to correct type if Type column exists
        if 'Type' in df.columns:
            if asset_type == 'futures':
                df = df[df['Type'].astype(str).str.contains('Futures', case=False, na=False)].copy()
            elif asset_type == 'stocks':
                df = df[df['Type'].astype(str).str.contains('Stock', case=False, na=False)].copy()
            elif asset_type == 'etfs':
                df = df[df['Type'].astype(str).str.contains('ETF', case=False, na=False)].copy()
        
        logger.info(f"Loaded {asset_type} master universe: {len(df)} instruments")
        return df
    
    def update_master_data(
        self, 
        provider: BaseProvider, 
        asset_types: List[str], 
        force_update: bool = False
    ) -> Dict[str, Dict]:
        """Update master data for specified asset types."""
        
        results = {}
        
        for asset_type in asset_types:
            try:
                result = self._update_asset_type(provider, asset_type, force_update)
                results[asset_type] = result
                
            except Exception as e:
                logger.error(f"Failed to update {asset_type}: {e}")
                results[asset_type] = {'success': False, 'error': str(e)}
        
        # Update metadata
        self._update_metadata(results)
        
        return results
    
    def _update_asset_type(
        self, 
        provider: BaseProvider, 
        asset_type: str, 
        force_update: bool
    ) -> Dict:
        """Update data for single asset type."""
        
        logger.info(f"Updating {asset_type} master data")
        
        # Load master universe with type filtering
        df_universe = self.load_master_universe(asset_type)
        
        # Get symbols that need updating
        symbols_to_update = self._get_symbols_to_update(
            df_universe, asset_type, force_update
        )
        
        if not symbols_to_update:
            logger.info(f"No {asset_type} symbols need updating")
            return {'success': True, 'updated': 0, 'skipped': len(df_universe)}
        
        logger.info(f"Updating {len(symbols_to_update)} {asset_type} symbols")
        
        # Download and save each symbol
        updated_count = 0
        for symbol_info in symbols_to_update:
            try:
                success = self._download_and_save_symbol(provider, symbol_info, asset_type)
                if success:
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to update {symbol_info['IBSymbol']}: {e}")
        
        return {
            'success': True, 
            'updated': updated_count,
            'total': len(symbols_to_update)
        }
    
    def _get_symbols_to_update(
        self, 
        df_universe: pd.DataFrame, 
        asset_type: str, 
        force_update: bool
    ) -> List[Dict]:
        """Get symbols that need updating with multi-format support."""
        
        if force_update:
            return df_universe.to_dict('records')
        
        # Check for stale data (older than 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        symbols_to_update = []
        
        for _, row in df_universe.iterrows():
            symbol = str(row['IBSymbol']).strip()
            
            # Check both parquet and csv formats
            parquet_path = self.data_dir / asset_type / f"{symbol}.parquet"
            csv_path = self.data_dir / asset_type / f"{symbol}.csv"
            
            def is_stale(path: Path) -> bool:
                if not path.exists():
                    return True
                file_time = datetime.fromtimestamp(path.stat().st_mtime)
                return file_time < cutoff_time
            
            # Update if both formats are missing or stale
            if is_stale(parquet_path) and is_stale(csv_path):
                symbols_to_update.append(row.to_dict())
        
        return symbols_to_update
    
    def _download_and_save_symbol(
        self, 
        provider: BaseProvider, 
        symbol_info: Dict, 
        asset_type: str
    ) -> bool:
        """Download and save data for single symbol with format fallback."""
        
        # Create instrument object
        if asset_type == 'futures':
            instrument = self._create_futures_instrument(symbol_info)
        else:
            raise NotImplementedError(f"Asset type {asset_type} not implemented yet")
        
        # Download data
        success, df, error = provider.download_data(instrument)
        
        if success and df is not None:
            # Save with format fallback
            output_dir = self.data_dir / asset_type
            output_dir.mkdir(parents=True, exist_ok=True)
            
            final_symbol = instrument.symbol
            base_path = output_dir / final_symbol
            
            saved_path = self._save_dataframe_with_fallback(df, base_path)
            logger.info(f"Saved {final_symbol}: {len(df)} records -> {saved_path.name}")
            return True
        else:
            logger.error(f"Failed to download {symbol_info['IBSymbol']}: {error}")
            return False
    
    def _save_dataframe_with_fallback(self, df: pd.DataFrame, base_path: Path) -> Path:
        """Save DataFrame with parquet-first, CSV fallback strategy."""
        
        # Try parquet first (most efficient)
        try:
            if importlib.util.find_spec("pyarrow") is not None:
                parquet_path = base_path.with_suffix(".parquet")
                df.to_parquet(parquet_path, compression="snappy")
                return parquet_path
        except Exception as e:
            logger.warning(f"Parquet save failed for {base_path.name}, falling back to CSV: {e}")
        
        # Fallback to CSV
        csv_path = base_path.with_suffix(".csv")
        df.to_csv(csv_path, index=True)
        return csv_path
    
    def _create_futures_instrument(self, symbol_info: Dict) -> FuturesContract:
        """Create futures instrument from symbol info with corrections."""
        
        # Apply corrections from config
        strategies_config = config_loader.load_strategies_config()
        corrections = strategies_config.corrections.futures if strategies_config.corrections else None
        
        symbol = str(symbol_info['IBSymbol']).strip()
        original_exchange = str(symbol_info['Exchange']).strip()
        original_currency = str(symbol_info['Currency']).strip()
        
        if corrections:
            exchange_overrides = getattr(corrections, 'exchange_overrides', {})
            currency_corrections = getattr(corrections, 'currency_corrections', {})
            symbol_overrides = getattr(corrections, 'symbol_overrides', {})
        else:
            exchange_overrides = {}
            currency_corrections = {}
            symbol_overrides = {}
        
        # Apply corrections
        final_symbol = symbol_overrides.get(symbol, symbol)
        corrected_exchange = exchange_overrides.get(final_symbol, original_exchange)
        corrected_currency = currency_corrections.get(final_symbol, original_currency)
        
        return FuturesContract(
            symbol=final_symbol,
            exchange=corrected_exchange,
            currency=corrected_currency,
            original_exchange=original_exchange,
            original_currency=original_currency,
            description=str(symbol_info.get('Instrument name', symbol)),
            asset_class=AssetClass(str(symbol_info.get('Asset class', 'Equity'))),
            region=str(symbol_info.get('Region', '')) if pd.notna(symbol_info.get('Region')) else None,
            multiplier=float(symbol_info.get('Multiplier', 1)) if pd.notna(symbol_info.get('Multiplier')) else 1.0,
            duration="2 Y",
            bar_size="1 day",
            use_rth=True,
            back_adjusted=True
        )
    
    def _update_metadata(self, results: Dict):
        """Update metadata files."""
        metadata = {
            'last_update': datetime.now().isoformat(),
            'results': results,
            'total_symbols': sum(r.get('updated', 0) for r in results.values() if r.get('success'))
        }
        
        metadata_path = self.metadata_dir / "last_update.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_status(self) -> Dict:
        """Get current master universe status."""
        status = {}
        
        for asset_type in ['futures', 'stocks', 'etfs']:
            try:
                universe_path = self.master_dir / f"{asset_type}_master_universe.xlsx"
                if universe_path.exists():
                    df = pd.read_excel(universe_path)
                    
                    # Count data files
                    data_dir = self.data_dir / asset_type
                    data_files = []
                    if data_dir.exists():
                        data_files.extend(list(data_dir.glob("*.parquet")))
                        data_files.extend(list(data_dir.glob("*.csv")))
                    
                    status[asset_type] = {
                        'symbol_count': len(df),
                        'data_files': len(data_files),
                        'last_updated': self._get_last_update_time(),
                        'status': 'Ready' if data_files else 'Needs Update'
                    }
                else:
                    status[asset_type] = {
                        'symbol_count': 0,
                        'data_files': 0,
                        'last_updated': None,
                        'status': 'Not Configured'
                    }
            except Exception as e:
                status[asset_type] = {
                    'symbol_count': 0,
                    'data_files': 0,
                    'last_updated': None,
                    'status': f'Error: {e}'
                }
        
        return status
    
    def _get_last_update_time(self) -> Optional[str]:
        """Get last update time."""
        try:
            metadata_path = self.metadata_dir / "last_update.json"
            if metadata_path.exists():
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                return metadata.get('last_update')
        except:
            pass
        return None
