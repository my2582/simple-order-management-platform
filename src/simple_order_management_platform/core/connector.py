"""Interactive Brokers connection management."""

import logging
from typing import Optional
from ib_insync import IB
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.exceptions import ConnectionError

logger = logging.getLogger(__name__)


class IBConnector:
    """IB API connection manager"""
    
    def __init__(self, host: str, port: int, client_id: int, timeout: int = 10, alternative_ports: Optional[list] = None):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.alternative_ports = alternative_ports or []
        self.connected = False
        self.actual_port = None  # Store the port that actually worked
    
    def connect(self) -> bool:
        """Connect to IB with retry logic and multiple port attempts"""
        if self.connected:
            return True
        
        # Try primary port first, then alternatives
        ports_to_try = [self.port] + self.alternative_ports
        
        last_error = None
        for port in ports_to_try:
            try:
                logger.info(f"Attempting connection to {self.host}:{port} (Client ID: {self.client_id})")
                
                self.ib.connect(
                    self.host,
                    port,
                    clientId=self.client_id,
                    timeout=self.timeout
                )
                
                self.connected = True
                self.actual_port = port
                logger.info(f"✓ IB connection successful: {self.host}:{port} (Client ID: {self.client_id})")
                return True
                
            except Exception as e:
                logger.warning(f"✗ Connection failed on port {port}: {e}")
                last_error = e
                # Disconnect in case of partial connection
                try:
                    self.ib.disconnect()
                except:
                    pass
        
        # All ports failed
        self.connected = False
        error_msg = f"IB connection failed on all ports {ports_to_try}. Last error: {last_error}"
        logger.error(error_msg)
        
        # Provide helpful troubleshooting information
        logger.error("Troubleshooting tips:")
        logger.error("1. Ensure TWS or IB Gateway is running")
        logger.error("2. Check API settings in TWS/Gateway:")
        logger.error("   - Enable API in Global Configuration > API Settings")
        logger.error("   - Set Socket Port (7497 for TWS, 4002 for Gateway)")
        logger.error("   - Enable 'Read-Only API'")
        logger.error("3. Verify no firewall blocking the connection")
        
        raise ConnectionError(error_msg)
    
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
