"""Base provider abstract class for market data sources."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

from ..models.base import BaseInstrument

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """
    Abstract base class for all market data providers.
    Defines the interface that all data providers must implement.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the data provider."""
        pass
    
    @abstractmethod
    def supports(self, instrument: BaseInstrument) -> bool:
        """
        Check if provider supports the given instrument type.
        
        Args:
            instrument: The instrument to check support for
            
        Returns:
            True if instrument type is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_instrument(self, instrument: BaseInstrument) -> bool:
        """
        Validate instrument against provider's system.
        
        Args:
            instrument: The instrument to validate
            
        Returns:
            True if instrument is valid and tradeable, False otherwise
        """
        pass
    
    @abstractmethod
    def download_data(
        self, 
        instrument: BaseInstrument,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
        """
        Download historical data for a single instrument.
        
        Args:
            instrument: The instrument to download data for
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            
        Returns:
            Tuple of (success, dataframe, error_message)
        """
        pass
    
    def download_multiple(
        self,
        instruments: List[BaseInstrument],
        max_retries: int = 3,
        retry_delay: float = 2.0,
        validate_first: bool = True,
        delay_between_requests: float = 1.0
    ) -> Dict[str, Tuple[bool, Optional[pd.DataFrame], Optional[str]]]:
        """
        Download data for multiple instruments with built-in validation and error handling.
        
        Args:
            instruments: List of instruments to download
            max_retries: Maximum retry attempts per instrument
            retry_delay: Delay between retries
            validate_first: Whether to validate instruments before downloading
            delay_between_requests: Delay between individual requests to avoid rate limits
            
        Returns:
            Dictionary mapping symbol to (success, dataframe, error_message)
        """
        results = {}
        total_instruments = len(instruments)
        
        logger.info(f"Starting batch download for {total_instruments} instruments")
        
        for i, instrument in enumerate(instruments):
            symbol = instrument.symbol
            logger.info(f"Processing [{i+1}/{total_instruments}] {symbol}")
            
            # Check if provider supports this instrument type
            if not self.supports(instrument):
                error_msg = f"Unsupported instrument type: {instrument.instrument_type.value}"
                logger.warning(f"[{symbol}] {error_msg}")
                results[symbol] = (False, None, error_msg)
                continue
            
            # Optional validation step
            if validate_first:
                if not self.validate_instrument(instrument):
                    error_msg = instrument.error_message or "Validation failed"
                    logger.warning(f"[{symbol}] Validation failed: {error_msg}")
                    results[symbol] = (False, None, error_msg)
                    continue
            
            # Download data
            success, data, error = self.download_data(
                instrument=instrument,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            
            results[symbol] = (success, data, error)
            
            # Rate limiting delay (except for last item)
            if i < total_instruments - 1 and delay_between_requests > 0:
                import time
                time.sleep(delay_between_requests)
        
        # Summary logging
        successful = sum(1 for success, _, _ in results.values() if success)
        failed = total_instruments - successful
        logger.info(f"Batch download completed: {successful} successful, {failed} failed")
        
        return results
    
    def health_check(self) -> bool:
        """
        Perform a health check on the provider connection.
        Default implementation returns True - providers should override.
        
        Returns:
            True if provider is healthy and ready, False otherwise
        """
        return True
