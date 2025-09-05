"""Abstract base models for financial instruments."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


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
    Abstract base class for all financial instruments.
    Defines common fields and abstract methods for instrument-specific logic.
    """

    # Common fields for all instruments
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange where instrument is traded")
    currency: str = Field(..., description="Base currency")
    description: str = Field(..., description="Instrument description")

    # Original information from universe file (before corrections)
    original_exchange: str = Field(..., description="Original exchange from input file")
    original_currency: str = Field(..., description="Original currency from input file")

    # Download settings
    duration: str = Field(default="1 Y", description="Historical data duration")
    bar_size: str = Field(default="1 day", description="Bar size for data")
    use_rth: bool = Field(default=True, description="Use regular trading hours only")

    # Processing status and results
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data_points: int = Field(0, description="Number of downloaded data points")
    download_time: Optional[datetime] = Field(None, description="Download timestamp")

    @property
    @abstractmethod
    def instrument_type(self) -> InstrumentType:
        """Returns the specific instrument type."""
        pass

    @abstractmethod
    def to_ib_contract(self) -> Any:
        """Converts to ib_insync Contract object."""
        pass

    @abstractmethod
    def get_chart_options(self) -> List[Any]:
        """Returns instrument-specific chart options for historical data."""
        pass

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
