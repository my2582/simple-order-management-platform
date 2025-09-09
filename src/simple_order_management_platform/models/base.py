"""Refactored base models using ib_insync for financial instruments."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from ib_insync import Contract


class InstrumentType(str, Enum):
    """Enumeration for different instrument types."""
    FUTURES = "futures"
    STOCKS = "stocks"
    ETFS = "etfs"


class ProcessingStatus(str, Enum):
    """Enumeration for processing status."""
    PENDING = "pending"
    VALIDATED = "validated"
    DOWNLOADING = "downloading"
    SUCCESS = "success"
    FAILED = "failed"


class BaseInstrument(BaseModel, ABC):
    """
    Simplified base class using ib_insync Contract objects.
    Reduces complexity by leveraging ib_insync's built-in contract handling.
    """

    # Core contract information
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange where instrument is traded")
    currency: str = Field(..., description="Base currency")
    description: str = Field(..., description="Instrument description")

    # Original information from universe file (before corrections)
    original_exchange: str = Field(..., description="Original exchange from input file")
    original_currency: str = Field(..., description="Original currency from input file")

    # Simplified download settings - ib_insync handles most complexity
    duration: str = Field(default="1 Y", description="Historical data duration")
    bar_size: str = Field(default="1 day", description="Bar size for data")
    use_rth: bool = Field(default=True, description="Use regular trading hours only")

    # Processing status and results
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data_points: int = Field(0, description="Number of downloaded data points")
    download_time: Optional[datetime] = Field(None, description="Download timestamp")

    # Store the actual ib_insync contract for easy access (not included in serialization)
    ib_contract_cache: Optional[Contract] = Field(None, exclude=True)

    @property
    @abstractmethod
    def instrument_type(self) -> InstrumentType:
        """Returns the specific instrument type."""
        pass

    @abstractmethod
    def create_ib_contract(self) -> Contract:
        """Creates ib_insync Contract object - simplified from to_ib_contract."""
        pass

    def get_ib_contract(self) -> Contract:
        """Get or create ib_insync Contract object with caching."""
        if self.ib_contract_cache is None:
            self.ib_contract_cache = self.create_ib_contract()
        return self.ib_contract_cache

    @abstractmethod
    def get_chart_options(self) -> List[Any]:
        """Returns instrument-specific chart options for historical data."""
        pass

    def download_historical_data(self, ib_connection, **kwargs) -> bool:
        """
        Download historical data using ib_insync - simplified interface.
        
        Args:
            ib_connection: Connected ib_insync IB instance
            **kwargs: Additional parameters for reqHistoricalData
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.status = ProcessingStatus.DOWNLOADING
            
            contract = self.get_ib_contract()
            
            # Use ib_insync's simplified historical data request
            bars = ib_connection.reqHistoricalData(
                contract=contract,
                endDateTime='',  # Current time
                durationStr=self.duration,
                barSizeSetting=self.bar_size,
                whatToShow='TRADES',
                useRTH=self.use_rth,
                formatDate=1,
                chartOptions=self.get_chart_options(),
                **kwargs
            )
            
            if bars:
                self.data_points = len(bars)
                self.status = ProcessingStatus.SUCCESS
                self.download_time = datetime.now()
                return True
            else:
                self.status = ProcessingStatus.FAILED
                self.error_message = "No data returned"
                return False
                
        except Exception as e:
            self.status = ProcessingStatus.FAILED
            self.error_message = str(e)
            return False

    def validate_contract(self, ib_connection) -> bool:
        """
        Validate contract using ib_insync - much simpler than manual validation.
        
        Args:
            ib_connection: Connected ib_insync IB instance
        
        Returns:
            bool: True if contract is valid, False otherwise
        """
        try:
            contract = self.get_ib_contract()
            
            # ib_insync automatically handles contract validation
            qualified_contracts = ib_connection.qualifyContracts(contract)
            
            if qualified_contracts:
                self.status = ProcessingStatus.VALIDATED
                # Update contract with qualified information
                self.ib_contract_cache = qualified_contracts[0]
                return True
            else:
                self.status = ProcessingStatus.FAILED
                self.error_message = "Contract validation failed"
                return False
                
        except Exception as e:
            self.status = ProcessingStatus.FAILED
            self.error_message = f"Validation error: {str(e)}"
            return False

    # Keep the original to_ib_contract method for backward compatibility
    def to_ib_contract(self) -> Contract:
        """Legacy method - use create_ib_contract instead."""
        return self.create_ib_contract()

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
