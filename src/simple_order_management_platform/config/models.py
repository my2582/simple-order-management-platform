"""Configuration data models using Pydantic."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class DataFrequency(str, Enum):
    """Data frequency options."""
    DAILY = "daily"
    WEEKLY = "weekly"  
    MONTHLY = "monthly"


class DownloadSettings(BaseModel):
    """Download configuration settings."""
    duration: str = Field(default="3 Y")
    bar_size: str = Field(default="1 day")
    use_rth: bool = Field(default=True)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=2.0)


class DataPaths(BaseModel):
    """Data file paths configuration."""
    futures_universe: Optional[str] = Field(None, description="Futures universe file path")
    stocks_universe: Optional[str] = Field(None, description="Stocks universe file path")
    etfs_universe: Optional[str] = Field(None, description="ETFs universe file path")


class StrategyVersion(BaseModel):
    """Strategy version configuration."""
    data_paths: DataPaths
    data_frequency: DataFrequency
    instrument_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Strategy(BaseModel):
    """Strategy configuration."""
    name: str
    description: str
    versions: Dict[str, StrategyVersion]
    
    def get_latest_version(self) -> str:
        return max(self.versions.keys())
    
    def get_version_config(self, version: Optional[str] = None) -> StrategyVersion:
        if version is None:
            version = self.get_latest_version()
        return self.versions[version]


class ExchangeCorrections(BaseModel):
    """Exchange corrections configuration."""
    exchange_overrides: Dict[str, str] = Field(default_factory=dict)
    currency_corrections: Dict[str, str] = Field(default_factory=dict)
    symbol_overrides: Dict[str, str] = Field(default_factory=dict) 


class Corrections(BaseModel):
    """Global corrections configuration."""
    futures: Optional[ExchangeCorrections] = Field(default_factory=ExchangeCorrections)


class StrategiesConfig(BaseModel):
    """Complete strategies configuration."""
    strategies: Dict[str, Strategy]
    defaults: Optional[Dict[str, Any]] = Field(default_factory=dict)
    corrections: Optional[Corrections] = Field(default_factory=Corrections)
    
    def get_strategy(self, name: str) -> Strategy:
        if name not in self.strategies:
            available = list(self.strategies.keys())
            raise ValueError(f"Strategy '{name}' not found. Available: {available}")
        return self.strategies[name]
    
    def list_strategies(self) -> List[str]:
        return list(self.strategies.keys())


class AppConfig(BaseModel):
    """Application configuration."""
    app: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def ib_settings(self) -> Dict[str, Any]:
        return self.app.get("ib", {})
