"""YAML configuration file loader."""

import logging
from pathlib import Path
from typing import Optional, Tuple
import yaml

from .models import StrategiesConfig, AppConfig, Strategy, StrategyVersion

logger = logging.getLogger(__name__)


class ConfigLoader:
    """YAML configuration loader."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.cwd() / "config"
        
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")
    
    def load_yaml(self, file_path: Path) -> dict:
        """Load YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            return content
        except Exception as e:
            logger.error(f"Failed to load configuration {file_path}: {e}")
            raise
    
    def load_strategies_config(self) -> StrategiesConfig:
        """Load strategies configuration."""
        file_path = self.config_dir / "strategies.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Strategies configuration file not found: {file_path}")
        
        config_data = self.load_yaml(file_path)
        return StrategiesConfig(**config_data)
    
    def load_app_config(self) -> AppConfig:
        """Load application configuration."""
        file_path = self.config_dir / "app.yaml"
        if not file_path.exists():
            return AppConfig()
        
        config_data = self.load_yaml(file_path)
        return AppConfig(**config_data)
    
    def get_strategy_config(
        self, 
        strategy_name: str, 
        version: Optional[str] = None
    ) -> Tuple[Strategy, StrategyVersion, str]:
        """Get strategy configuration with merged version settings."""
        strategies_config = self.load_strategies_config()
        strategy = strategies_config.get_strategy(strategy_name)
        
        if version is None:
            version = strategy.get_latest_version()
        
        strategy_version = strategy.get_version_config(version)
        
        return strategy, strategy_version, version


# Global configuration loader instance
config_loader = ConfigLoader()
