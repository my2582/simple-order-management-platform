"""Market Data Platform service for managing cached price data."""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import json
from decimal import Decimal

from ..auth.permissions import UserRole, get_role_ibkr_params, Permission, require_permission
from ..core.connector import IBConnector
from ..providers.ib import IBProvider
from ..models.universe import universe_manager
from ..config.loader import config_loader
from ..integrations.sharepoint import create_sharepoint_integration
from ..integrations.email import create_email_integration

logger = logging.getLogger(__name__)


class MarketDataCache:
    """Cache manager for market data prices."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize market data cache.
        
        Args:
            cache_dir: Directory to store cached data
        """
        if cache_dir is None:
            app_config = config_loader.load_app_config()
            data_dir = Path(app_config.app.get("directories", {}).get("data_dir", "./data"))
            cache_dir = data_dir / "market_data_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file paths
        self.prices_file = self.cache_dir / "current_prices.csv"
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Load existing cache
        self.prices_data = self._load_prices_cache()
        self.metadata = self._load_metadata()
    
    def _load_prices_cache(self) -> pd.DataFrame:
        """Load prices from cache file."""
        if self.prices_file.exists():
            try:
                df = pd.read_csv(self.prices_file)
                logger.info(f"Loaded {len(df)} cached prices from {self.prices_file}")
                return df
            except Exception as e:
                logger.error(f"Failed to load price cache: {e}")
        
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            'symbol', 'close_price', 'currency', 'last_updated', 
            'data_date', 'asset_class', 'exchange'
        ])
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                logger.info(f"Loaded cache metadata: {metadata.get('last_update', 'Unknown')}")
                return metadata
            except Exception as e:
                logger.error(f"Failed to load cache metadata: {e}")
        
        return {
            'last_update': None,
            'data_date': None,
            'symbols_count': 0,
            'update_source': None
        }
    
    def update_prices(self, prices_dict: Dict[str, Dict[str, Any]]) -> None:
        """Update cached prices with new data.
        
        Args:
            prices_dict: Dictionary mapping symbol -> price data
        """
        current_time = datetime.now().isoformat()
        
        # Convert to DataFrame
        rows = []
        for symbol, price_data in prices_dict.items():
            # Get asset class from universe
            instrument = universe_manager.get_instrument(symbol)
            asset_class = instrument.asset_class if instrument else 'Unknown'
            exchange = instrument.exchange if instrument else 'Unknown'
            
            rows.append({
                'symbol': symbol,
                'close_price': float(price_data.get('close_price', 0)),
                'currency': price_data.get('currency', 'USD'),
                'last_updated': current_time,
                'data_date': price_data.get('data_date', datetime.now().date().isoformat()),
                'asset_class': asset_class,
                'exchange': exchange
            })
        
        self.prices_data = pd.DataFrame(rows)
        
        # Update metadata
        self.metadata.update({
            'last_update': current_time,
            'data_date': rows[0]['data_date'] if rows else None,
            'symbols_count': len(rows),
            'update_source': 'IBKR API'
        })
        
        # Save to files
        self._save_cache()
    
    def _save_cache(self) -> None:
        """Save cache to files."""
        try:
            # Save prices
            self.prices_data.to_csv(self.prices_file, index=False)
            
            # Save metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info(f"Saved {len(self.prices_data)} prices to cache")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price for a symbol."""
        if self.prices_data.empty:
            return None
        
        price_row = self.prices_data[self.prices_data['symbol'] == symbol]
        if price_row.empty:
            return None
        
        row = price_row.iloc[0]
        return {
            'symbol': row['symbol'],
            'close_price': row['close_price'],
            'currency': row['currency'],
            'last_updated': row['last_updated'],
            'data_date': row['data_date'],
            'asset_class': row['asset_class'],
            'exchange': row['exchange']
        }
    
    def get_all_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached prices."""
        if self.prices_data.empty:
            return {}
        
        result = {}
        for _, row in self.prices_data.iterrows():
            result[row['symbol']] = {
                'close_price': row['close_price'],
                'currency': row['currency'],
                'last_updated': row['last_updated'],
                'data_date': row['data_date'],
                'asset_class': row['asset_class'],
                'exchange': row['exchange']
            }
        
        return result
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache."""
        age_hours = None
        if self.metadata.get('last_update'):
            try:
                last_update = datetime.fromisoformat(self.metadata['last_update'])
                age_hours = (datetime.now() - last_update).total_seconds() / 3600
            except:
                pass
        
        return {
            **self.metadata,
            'cache_age_hours': age_hours,
            'cache_file_exists': self.prices_file.exists(),
            'cached_symbols': len(self.prices_data) if not self.prices_data.empty else 0
        }
    
    def is_cache_fresh(self, max_age_hours: float = 24.0) -> bool:
        """Check if cache is fresh enough."""
        info = self.get_cache_info()
        age_hours = info.get('cache_age_hours')
        
        if age_hours is None:
            return False
        
        return age_hours <= max_age_hours


class MarketDataService:
    """Service for managing market data updates and caching."""
    
    def __init__(self):
        """Initialize market data service."""
        self.cache = MarketDataCache()
        self.sharepoint = create_sharepoint_integration()
        self.email = create_email_integration()
    
    @require_permission(Permission.MARKET_DATA)
    def update_universe_prices(
        self,
        force_update: bool = False,
        max_age_hours: float = 24.0
    ) -> Dict[str, Any]:
        """Update prices for all universe symbols.
        
        Args:
            force_update: Force update even if cache is fresh
            max_age_hours: Maximum cache age in hours before update
            
        Returns:
            Dictionary with update results
        """
        start_time = datetime.now()
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'symbols_updated': 0,
            'symbols_failed': 0,
            'cache_was_fresh': False,
            'errors': [],
            'data_date': None
        }
        
        try:
            # Check if update is needed
            if not force_update and self.cache.is_cache_fresh(max_age_hours):
                result['cache_was_fresh'] = True
                result['success'] = True
                cache_info = self.cache.get_cache_info()
                result['symbols_updated'] = cache_info['cached_symbols']
                result['data_date'] = cache_info['data_date']
                logger.info(f"Cache is fresh ({cache_info['cache_age_hours']:.1f}h old), skipping update")
                return result
            
            # Get all universe symbols
            universe_symbols = universe_manager.get_all_ib_symbols()
            if not universe_symbols:
                result['errors'].append("No universe symbols found")
                return result
            
            logger.info(f"Updating prices for {len(universe_symbols)} universe symbols")
            
            # Download prices from IBKR
            prices_dict = self._download_prices_from_ibkr(universe_symbols)
            
            # Update cache
            if prices_dict:
                self.cache.update_prices(prices_dict)
                result['symbols_updated'] = len(prices_dict)
                result['symbols_failed'] = len(universe_symbols) - len(prices_dict)
                result['success'] = True
                result['data_date'] = datetime.now().date().isoformat()
                
                logger.info(f"Updated {result['symbols_updated']} symbols, "
                           f"{result['symbols_failed']} failed")
            else:
                result['errors'].append("No price data downloaded")
        
        except Exception as e:
            error_msg = f"Market data update failed: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        result['end_time'] = datetime.now().isoformat()
        result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def _download_prices_from_ibkr(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Download current prices from IBKR for given symbols."""
        prices_dict = {}
        
        try:
            # Get IBKR connection parameters for trade assistant role
            ibkr_params = get_role_ibkr_params(UserRole.TRADE_ASSISTANT)
            
            with IBConnector(**ibkr_params) as connector:
                provider = IBProvider(connector)
                
                # Download prices in batches to avoid overwhelming the API
                batch_size = 20
                for i in range(0, len(symbols), batch_size):
                    batch_symbols = symbols[i:i + batch_size]
                    
                    try:
                        batch_prices = provider.get_current_prices(batch_symbols)
                        prices_dict.update(batch_prices)
                        
                        logger.info(f"Downloaded prices for batch {i//batch_size + 1}: "
                                   f"{len(batch_prices)}/{len(batch_symbols)} symbols")
                    
                    except Exception as e:
                        logger.warning(f"Failed to download batch {i//batch_size + 1}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Failed to connect to IBKR for price download: {e}")
        
        return prices_dict
    
    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price for a symbol."""
        return self.cache.get_price(symbol)
    
    def get_cached_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get cached prices for multiple symbols."""
        result = {}
        for symbol in symbols:
            price_data = self.cache.get_price(symbol)
            if price_data:
                result[symbol] = price_data
        
        return result
    
    def get_all_cached_prices(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached prices."""
        return self.cache.get_all_prices()
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        return self.cache.get_cache_info()
    
    def export_market_data_report(self) -> Optional[Path]:
        """Export current market data to Excel report."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_data_report_{timestamp}.xlsx"
            
            # Get output directory
            app_config = config_loader.load_app_config()
            output_dir = Path(app_config.app.get("directories", {}).get("output_dir", "./data/output"))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / filename
            
            # Prepare data for export
            prices_df = self.cache.prices_data.copy()
            
            if prices_df.empty:
                logger.warning("No cached prices to export")
                return None
            
            # Add universe information
            prices_df['instrument_name'] = prices_df['symbol'].apply(
                lambda s: universe_manager.get_instrument(s).instrument_name 
                if universe_manager.get_instrument(s) else s
            )
            
            # Create Excel file
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main prices sheet
                prices_df.to_excel(writer, sheet_name='Market_Data', index=False)
                
                # Summary sheet
                summary_data = self._create_market_data_summary()
                summary_df = pd.DataFrame(summary_data, columns=['Field', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            logger.info(f"Market data report exported: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to export market data report: {e}")
            return None
    
    def _create_market_data_summary(self) -> List[List[Any]]:
        """Create summary information for market data report."""
        cache_info = self.cache.get_cache_info()
        universe_summary = universe_manager.get_universe_summary()
        
        summary_data = [
            ['Market Data Summary', ''],
            ['Export Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S SGT')],
            ['Data Date', cache_info.get('data_date', 'Unknown')],
            ['Last Update', cache_info.get('last_update', 'Unknown')],
            ['Cache Age (hours)', f"{cache_info.get('cache_age_hours', 0):.1f}"],
            ['', ''],
            ['Universe Information', ''],
            ['Total Universe Symbols', universe_summary['total_instruments']],
            ['Cached Symbols', cache_info['cached_symbols']],
            ['Coverage', f"{cache_info['cached_symbols'] / universe_summary['total_instruments'] * 100:.1f}%" 
             if universe_summary['total_instruments'] > 0 else '0%'],
            ['', ''],
            ['Asset Class Breakdown', '']
        ]
        
        # Add asset class breakdown
        if not self.cache.prices_data.empty:
            asset_class_counts = self.cache.prices_data['asset_class'].value_counts()
            for asset_class, count in asset_class_counts.items():
                summary_data.append([f"  - {asset_class}", count])
        
        return summary_data
    
    def send_market_data_notification(self, update_result: Dict[str, Any]) -> bool:
        """Send market data update notification via email."""
        try:
            # Export market data report
            report_path = self.export_market_data_report()
            
            if not report_path:
                logger.error("Failed to generate market data report for email")
                return False
            
            # Upload to SharePoint if available
            sharepoint_path = None
            if self.sharepoint.is_available():
                sharepoint_path = self.sharepoint.upload_market_data(report_path, "daily_prices")
            
            # Prepare email summary
            email_summary = {
                'symbols_updated': update_result.get('symbols_updated', 0),
                'symbols_failed': update_result.get('symbols_failed', 0),
                'price_date': update_result.get('data_date', 'Unknown'),
                'duration_seconds': update_result.get('duration_seconds', 0),
                'sharepoint_path': str(sharepoint_path) if sharepoint_path else None
            }
            
            # Send email
            app_config = config_loader.load_app_config()
            recipient = app_config.app.get('email', {}).get('recipient', 'minsu.yeom@arkifinance.com')
            
            success = self.email.send_market_data_report(
                recipient_email=recipient,
                data_file_path=report_path,
                data_summary=email_summary
            )
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to send market data notification: {e}")
            return False


# Global instance for easy access
market_data_service = MarketDataService()