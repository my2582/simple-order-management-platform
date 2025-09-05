"""Multi-asset data download orchestrator."""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd

from ..models.base import InstrumentType
from ..providers.base import BaseProvider
from ..utils.loaders import load_instruments_from_strategy
from ..utils.exceptions import MarketDataPlatformError

logger = logging.getLogger(__name__)


class DataOrchestrator:
    """
    Coordinates multi-asset data downloads across different instrument types.
    Manages the overall workflow from strategy configuration to data export.
    """
    
    def __init__(self, provider: BaseProvider):
        """
        Initialize orchestrator with a data provider.
        
        Args:
            provider: The data provider to use for downloads
        """
        self.provider = provider
        
        # Verify provider health
        if not self.provider.health_check():
            raise MarketDataPlatformError(f"Provider {self.provider.name} failed health check")
        
        logger.info(f"DataOrchestrator initialized with provider: {self.provider.name}")
    
    def download_strategy_data(
        self,
        strategy_name: str,
        version: Optional[str] = None,
        instrument_types: Optional[List[InstrumentType]] = None,
        validate_instruments: bool = True,
        test_mode: bool = False
    ) -> Dict[str, Dict[str, Tuple[bool, Optional[pd.DataFrame], Optional[str]]]]:
        """
        Download data for a strategy across multiple instrument types.
        
        Args:
            strategy_name: Name of the strategy to execute
            version: Strategy version (defaults to latest)
            instrument_types: List of instrument types to download (defaults to all)
            validate_instruments: Whether to validate instruments before download
            test_mode: If True, limit to first 3 instruments per type
            
        Returns:
            Dictionary mapping instrument_type -> symbol -> (success, dataframe, error)
        """
        
        if instrument_types is None:
            instrument_types = list(InstrumentType)
        
        logger.info(f"=== Starting multi-asset download for strategy '{strategy_name}' ===")
        logger.info(f"Target instrument types: {[t.value for t in instrument_types]}")
        
        # Load instruments by type from strategy configuration
        try:
            instruments_by_type = load_instruments_from_strategy(
                strategy_name=strategy_name,
                version=version,
                instrument_types=instrument_types
            )
        except Exception as e:
            raise MarketDataPlatformError(f"Failed to load instruments for strategy '{strategy_name}': {e}")
        
        if not instruments_by_type:
            raise MarketDataPlatformError(f"No instruments found for strategy '{strategy_name}'")
        
        results_by_type = {}
        total_instruments = 0
        
        # Process each instrument type
        for instrument_type, instruments in instruments_by_type.items():
            if not instruments:
                logger.info(f"No {instrument_type.value} instruments found, skipping")
                continue
            
            # Apply test mode limiting
            if test_mode and len(instruments) > 3:
                instruments = instruments[:3]
                logger.info(f"Test mode: limiting {instrument_type.value} to {len(instruments)} instruments")
            
            total_instruments += len(instruments)
            
            logger.info(f"\n--- Processing {instrument_type.value.title()} ({len(instruments)} instruments) ---")
            
            # Check provider support for this instrument type
            if instruments and not self.provider.supports(instruments[0]):
                error_msg = f"Provider {self.provider.name} does not support {instrument_type.value}"
                logger.warning(error_msg)
                
                # Create failure results for all instruments of this type
                results_by_type[instrument_type.value] = {
                    inst.symbol: (False, None, error_msg) for inst in instruments
                }
                continue
            
            # Download data for this instrument type
            try:
                results = self.provider.download_multiple(
                    instruments=instruments,
                    max_retries=3,
                    retry_delay=2.0,
                    validate_first=validate_instruments,
                    delay_between_requests=1.5
                )
                
                results_by_type[instrument_type.value] = results
                
            except Exception as e:
                logger.error(f"Failed to download {instrument_type.value} data: {e}")
                # Create failure results for all instruments of this type
                results_by_type[instrument_type.value] = {
                    inst.symbol: (False, None, f"Download failed: {str(e)}") for inst in instruments
                }
        
        # Generate summary statistics
        self._log_download_summary(results_by_type, total_instruments)
        
        return results_by_type
    
    def _log_download_summary(
        self, 
        results_by_type: Dict[str, Dict[str, Tuple[bool, Optional[pd.DataFrame], Optional[str]]]],
        total_instruments: int
    ) -> None:
        """Log summary of download results."""
        
        total_successful = 0
        total_failed = 0
        
        logger.info(f"\n=== Download Summary ===")
        
        for instrument_type, results in results_by_type.items():
            successful = sum(1 for success, _, _ in results.values() if success)
            failed = len(results) - successful
            
            total_successful += successful
            total_failed += failed
            
            logger.info(f"{instrument_type.title()}: {successful} successful, {failed} failed")
            
            # Log failed instruments for debugging
            if failed > 0:
                failed_symbols = [symbol for symbol, (success, _, _) in results.items() if not success]
                logger.warning(f"  Failed {instrument_type}: {', '.join(failed_symbols[:5])}"
                             f"{'...' if len(failed_symbols) > 5 else ''}")
        
        success_rate = (total_successful / total_instruments * 100) if total_instruments > 0 else 0
        logger.info(f"Overall: {total_successful}/{total_instruments} successful ({success_rate:.1f}%)")
        
        if total_failed > 0:
            logger.warning(f"Total failures: {total_failed}")
