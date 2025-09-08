"""Refactored portfolio service using ib_insync with SGD base currency."""

import logging
from datetime import datetime
from decimal import Decimal
import decimal
from typing import List, Dict, Any, Optional
from ib_insync import IB

from ..models.portfolio import (
    Position, AccountSummary, PortfolioSnapshot, MultiAccountPortfolio
)
from ..providers.ib import IBProvider
from ..utils.exceptions import SimpleOrderManagementPlatformError


logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for downloading and managing portfolio positions using ib_insync (all in SGD base currency)."""
    
    def __init__(self, ib_provider: IBProvider, use_cached_prices: bool = False):
        """Initialize portfolio service.
        
        Args:
            ib_provider: Interactive Brokers provider instance
            use_cached_prices: Whether to use cached prices (legacy parameter for compatibility)
        """
        self.ib_provider = ib_provider
        self.ib: IB = ib_provider.connector.ib
        self.use_cached_prices = use_cached_prices  # Keep for backward compatibility
    
    def get_all_accounts(self) -> List[str]:
        """Get all managed account IDs.
        
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
    
    def get_account_portfolio(self, account_id: str) -> List:
        """Get portfolio for specific account.
        
        Args:
            account_id: Account ID to get portfolio for
            
        Returns:
            List of Position objects from ib_insync
            
        Raises:
            SimpleOrderManagementPlatformError: If unable to retrieve portfolio
        """
        try:
            logger.info(f"Requesting portfolio for account: {account_id}")
            
            # REVERT TO ORIGINAL WORKING METHOD: Use positions() as it actually works
            # IB Gateway Read-Only setting provides the safety we need
            logger.debug(f"Using positions() method (original working approach)")
            
            # Get all positions and filter by account (ORIGINAL METHOD THAT WORKED)
            all_positions = self.ib.positions()
            account_positions = [pos for pos in all_positions if pos.account == account_id]
            
            # Wait for data to be received
            self.ib.sleep(1)
            
            logger.info(f"Retrieved {len(account_positions)} positions for account {account_id}")
            return account_positions
            
        except Exception as e:
            logger.error(f"Error retrieving portfolio for account {account_id}: {e}")
            raise SimpleOrderManagementPlatformError(
                f"Failed to get portfolio for account {account_id}: {e}"
            )
    
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get account summary information.
        
        Args:
            account_id: Account ID to get summary for
            
        Returns:
            Dictionary with account summary data
            
        Raises:
            SimpleOrderManagementPlatformError: If unable to retrieve account summary
        """
        try:
            logger.info(f"Requesting account summary for: {account_id}")
            
            # REVERT TO ORIGINAL: Use accountSummary() as it provides structured data
            # IB Gateway Read-Only setting will protect us from write operations
            logger.debug(f"Using accountSummary() method (original working approach)")
            
            # Define the tags we want to retrieve  
            tags = [
                'NetLiquidation', 'TotalCashValue', 'SettledCash', 'AccruedCash',
                'BuyingPower', 'EquityWithLoanValue', 'GrossPositionValue',
                'UnrealizedPnL', 'RealizedPnL', 'AccountType'
            ]
            
            # Request account summary (ORIGINAL METHOD THAT WORKED)
            summary_items = self.ib.accountSummary(account_id)
            
            # Wait for data
            self.ib.sleep(1)
            
            # Convert to dictionary
            summary_dict = {}
            for item in summary_items:
                if item.account == account_id:
                    summary_dict[item.tag] = item.value
                    
            logger.info(f"Retrieved account summary for {account_id}: {len(summary_dict)} items")
            return summary_dict
            
        except Exception as e:
            logger.error(f"Error retrieving account summary for {account_id}: {e}")
            raise SimpleOrderManagementPlatformError(
                f"Failed to get account summary for {account_id}: {e}"
            )
    
    def _convert_ib_position_to_position(self, ib_position, account_id: str) -> Position:
        """Convert ib_insync Position object to Position model.
        
        Args:
            ib_position: ib_insync Position object  
            account_id: Account ID for this position
            
        Returns:
            Position model object
        """
        try:
            contract = ib_position.contract
            
            # Position objects have marketPrice and marketValue (unlike Portfolio objects)
            # This is why the original method worked better!
            
            market_price = None
            market_value = None
            
            # Method 1: Use Position object's built-in marketPrice if available
            if hasattr(ib_position, 'marketPrice') and ib_position.marketPrice:
                market_price = ib_position.marketPrice
                logger.debug(f"Using Position marketPrice for {contract.symbol}: {market_price}")
            
            # Method 2: Use Position object's built-in marketValue if available  
            if hasattr(ib_position, 'marketValue') and ib_position.marketValue:
                market_value = ib_position.marketValue
                logger.debug(f"Using Position marketValue for {contract.symbol}: {market_value}")
            
            # Method 3: Try cached prices if configured
            if not market_price and self.use_cached_prices:
                try:
                    from ..services.market_data_service import market_data_service
                    cached_price_data = market_data_service.get_cached_price(contract.symbol)
                    if cached_price_data:
                        market_price = cached_price_data['close_price']
                        logger.debug(f"Using cached price for {contract.symbol}: {market_price}")
                except Exception as e:
                    logger.debug(f"Could not get cached price for {contract.symbol}: {e}")
            
            # Method 4: Fallback to avgCost if no other price available
            if not market_price and hasattr(ib_position, 'avgCost') and ib_position.avgCost:
                market_price = ib_position.avgCost
                logger.debug(f"Using avgCost as market price for {contract.symbol}: {market_price}")
                
            # Calculate market value if not already available
            if not market_value and market_price and ib_position.position:
                multiplier = getattr(contract, 'multiplier', 1)
                if multiplier and multiplier != '':
                    try:
                        multiplier = int(multiplier)
                    except (ValueError, TypeError):
                        multiplier = 1
                else:
                    multiplier = 1
                    
                market_value = Decimal(str(market_price)) * Decimal(str(ib_position.position)) * Decimal(str(multiplier))
            
            # Safely handle None and NaN values
            def safe_decimal(value):
                if value is None:
                    return None
                try:
                    decimal_val = Decimal(str(value))
                    return decimal_val if decimal_val.is_finite() else None
                except (ValueError, TypeError, decimal.InvalidOperation):
                    return None
            
            position = Position(
                account_id=account_id,
                symbol=contract.symbol,
                contract_id=contract.conId,
                exchange=contract.exchange or '',
                currency=contract.currency or 'USD',
                sec_type=contract.secType or 'STK',
                position=Decimal(str(ib_position.position)),
                market_price=safe_decimal(market_price),
                market_value=safe_decimal(market_value),
                avg_cost=safe_decimal(ib_position.avgCost),
                unrealized_pnl=safe_decimal(getattr(ib_position, 'unrealizedPNL', None)),  # Position objects have PnL
                realized_pnl=safe_decimal(getattr(ib_position, 'realizedPNL', None)),
                local_symbol=getattr(contract, 'localSymbol', None),
                multiplier=int(getattr(contract, 'multiplier', 1)) if getattr(contract, 'multiplier', '') != '' else None,
                last_trade_date=getattr(contract, 'lastTradeDateOrContractMonth', None),
            )
            
            return position
            
        except Exception as e:
            logger.error(f"Error converting IB position to Position model: {e}")
            logger.error(f"IB Position data: {ib_position}")
            raise SimpleOrderManagementPlatformError(f"Failed to convert position data: {e}")
    
    def _convert_account_summary_dict_to_model(self, summary_dict: Dict[str, Any], account_id: str) -> AccountSummary:
        """Convert account summary dictionary to AccountSummary model.
        
        Args:
            summary_dict: Dictionary with account summary data
            account_id: Account ID
            
        Returns:
            AccountSummary model object
        """
        def safe_decimal(value: str) -> Optional[Decimal]:
            """Safely convert string to Decimal."""
            try:
                return Decimal(str(value)) if value and value != '' else None
            except (ValueError, TypeError):
                return None
        
        return AccountSummary(
            account_id=account_id,
            account_type=summary_dict.get('AccountType'),
            currency='USD',  # Default, could be extracted from currency-specific tags
            net_liquidation=safe_decimal(summary_dict.get('NetLiquidation')),
            total_cash_value=safe_decimal(summary_dict.get('TotalCashValue')),
            settled_cash=safe_decimal(summary_dict.get('SettledCash')),
            accrued_cash=safe_decimal(summary_dict.get('AccruedCash')),
            buying_power=safe_decimal(summary_dict.get('BuyingPower')),
            equity_with_loan_value=safe_decimal(summary_dict.get('EquityWithLoanValue')),
            gross_position_value=safe_decimal(summary_dict.get('GrossPositionValue')),
            unrealized_pnl=safe_decimal(summary_dict.get('UnrealizedPnL')),
            realized_pnl=safe_decimal(summary_dict.get('RealizedPnL')),
        )
    
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
            # Use the existing proven working method instead of from_ib_connection\n            # Get positions using the working logic\n            ib_positions = self.get_account_portfolio(account_id)\n            \n            # Convert to Position objects using the proven converter\n            positions = []\n            for ib_pos in ib_positions:\n                if ib_pos.position != 0:  # Skip zero positions\n                    position = self._convert_ib_position_to_position(ib_pos, account_id)\n                    positions.append(position)\n            \n            # Get account summary using the working logic\n            summary_dict = self.get_account_summary(account_id)\n            account_summary = self._convert_account_summary_dict_to_model(summary_dict, account_id)\n            \n            # Create snapshot using proven working components\n            snapshot = PortfolioSnapshot(\n                account_id=account_id,\n                positions=positions,\n                account_summary=account_summary,\n                timestamp=datetime.now()\n            )
            
            active_positions = [p for p in snapshot.positions if p.position != 0]
            total_value = snapshot.get_total_portfolio_value() or 0
            logger.info(f"Successfully downloaded portfolio for {account_id}: "
                       f"{len(active_positions)} active positions, "
                       f"Total value: SGD {total_value:,.2f}")
            
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
                accounts = self.get_all_accounts()
                multi_portfolio = MultiAccountPortfolio(timestamp=datetime.now())
                
                for account_id in accounts:
                    try:
                        snapshot = self.download_account_portfolio(account_id)
                        multi_portfolio.add_snapshot(snapshot)
                        logger.info(f"Successfully downloaded portfolio for account: {account_id}")
                    except Exception as e:
                        logger.error(f"Failed to download portfolio for account {account_id}: {e}")
                        continue
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