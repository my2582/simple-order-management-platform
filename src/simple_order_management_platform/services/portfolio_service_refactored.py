"""Refactored portfolio service using ib_insync with SGD base currency."""

import logging
from datetime import datetime
from typing import List, Optional
from ib_insync import IB

from ..models.portfolio import (
    PortfolioSnapshot, MultiAccountPortfolio
)
from ..providers.ib import IBProvider
from ..utils.exceptions import SimpleOrderManagementPlatformError

logger = logging.getLogger(__name__)


class PortfolioServiceRefactored:
    """Service for downloading and managing portfolio positions using ib_insync (all in SGD base currency)."""
    
    def __init__(self, ib_provider: IBProvider, use_cached_prices: bool = False):
        """Initialize portfolio service.
        
        Args:
            ib_provider: Interactive Brokers provider instance
            use_cached_prices: Whether to use cached prices (legacy parameter for compatibility)
        """
        self.ib_provider = ib_provider
        self.ib: IB = ib_provider.connector.ib
        self.use_cached_prices = use_cached_prices  # Keep for compatibility
    
    def get_all_accounts(self) -> List[str]:
        """Get all managed account IDs using ib_insync.
        
        Returns:
            List of account IDs
            
        Raises:
            SimpleOrderManagementPlatformError: If unable to retrieve accounts
        """
        try:
            accounts = self.ib.managedAccounts()
            if not accounts:
                raise SimpleOrderManagementPlatformError("No managed accounts found")
                
            logger.info(f"Found {len(accounts)} managed accounts: {accounts}")
            return accounts
            
        except Exception as e:
            logger.error(f"Error retrieving managed accounts: {e}")
            raise SimpleOrderManagementPlatformError(f"Failed to get accounts: {e}")
    
    def download_account_portfolio(self, account_id: str) -> PortfolioSnapshot:
        """Download complete portfolio snapshot for a single account using ib_insync.
        
        Args:
            account_id: Account ID to download portfolio for
            
        Returns:
            PortfolioSnapshot with positions and account summary (all values in SGD base currency)
            
        Raises:
            SimpleOrderManagementPlatformError: If download fails
        """
        try:
            logger.info(f"Downloading portfolio snapshot for account: {account_id} using ib_insync")
            
            # Use the new ib_insync-based portfolio snapshot method
            # All monetary values are automatically in account base currency (SGD)
            snapshot = PortfolioSnapshot.from_ib_connection(self.ib, account_id)
            
            logger.info(f"Successfully downloaded portfolio for {account_id}: "
                       f"{len(snapshot.get_active_positions())} active positions, "
                       f"Total value: SGD {snapshot.get_total_portfolio_value():,.2f}")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error downloading portfolio for account {account_id}: {e}")
            raise SimpleOrderManagementPlatformError(
                f"Failed to download portfolio for account {account_id}: {e}"
            )
    
    def download_all_portfolios(self, account_ids: Optional[List[str]] = None) -> MultiAccountPortfolio:
        """Download portfolio snapshots for all or specified accounts using ib_insync.
        
        Args:
            account_ids: Optional list of specific account IDs. If None, downloads all accounts.
            
        Returns:
            MultiAccountPortfolio with snapshots for all accounts (all values in SGD base currency)
            
        Raises:
            SimpleOrderManagementPlatformError: If download fails
        """
        try:
            if account_ids is None:
                # Use ib_insync's automatic account discovery
                logger.info("Downloading all managed account portfolios using ib_insync")
                multi_portfolio = MultiAccountPortfolio.from_ib_connection(self.ib)
            else:
                # Download specified accounts only
                logger.info(f"Downloading portfolios for {len(account_ids)} specified accounts: {account_ids}")
                multi_portfolio = MultiAccountPortfolio(timestamp=datetime.now())
                
                # Download each account's portfolio
                for account_id in account_ids:
                    try:
                        snapshot = self.download_account_portfolio(account_id)
                        multi_portfolio.add_snapshot(snapshot)
                        logger.info(f"Successfully downloaded portfolio for account: {account_id}")
                    except Exception as e:
                        logger.error(f"Failed to download portfolio for account {account_id}: {e}")
                        # Continue with other accounts even if one fails
                        continue
            
            if not multi_portfolio.snapshots:
                raise SimpleOrderManagementPlatformError("No portfolios were successfully downloaded")
            
            combined_summary = multi_portfolio.get_combined_summary()
            logger.info(f"Successfully downloaded {combined_summary['total_accounts']} portfolios, "
                       f"Total value: SGD {combined_summary['total_portfolio_value']:,.2f}")
            return multi_portfolio
            
        except Exception as e:
            logger.error(f"Error downloading portfolios: {e}")
            raise SimpleOrderManagementPlatformError(f"Failed to download portfolios: {e}")


# Quick utility functions
def get_portfolio_snapshot_simple(ib: IB, account: str = '') -> PortfolioSnapshot:
    """
    Quick function to get portfolio snapshot directly from ib_insync.
    All values automatically in account base currency (SGD).
    
    Args:
        ib: Connected ib_insync IB instance
        account: Account ID (empty for single account)
    """
    return PortfolioSnapshot.from_ib_connection(ib, account)


def get_all_portfolios_simple(ib: IB) -> MultiAccountPortfolio:
    """
    Quick function to get all managed account portfolios directly from ib_insync.
    All values automatically in account base currency (SGD).
    
    Args:
        ib: Connected ib_insync IB instance
    """
    return MultiAccountPortfolio.from_ib_connection(ib)