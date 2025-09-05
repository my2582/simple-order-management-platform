"""Interactive Brokers connection management."""

import logging
from typing import Optional
from ib_insync import IB
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.exceptions import ConnectionError

logger = logging.getLogger(__name__)


class IBConnector:
    """IB API connection manager"""
    
    def __init__(self, host: str, port: int, client_id: int, timeout: int = 10):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.connected = False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def connect(self) -> bool:
        """Connect to IB with retry logic"""
        try:
            if self.connected:
                return True
                
            self.ib.connect(
                self.host,
                self.port,
                clientId=self.client_id,
                timeout=self.timeout
            )
            self.connected = True
            logger.info(f"✓ IB connection successful: {self.host}:{self.port} (Client ID: {self.client_id})")
            return True
            
        except Exception as e:
            logger.error(f"✗ IB connection failed: {e}")
            self.connected = False
            raise ConnectionError(f"IB connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from IB"""
        if self.connected and self.ib.isConnected():
            self.ib.disconnect()
            self.connected = False
            logger.info("IB connection closed")
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connected and self.ib.isConnected()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
