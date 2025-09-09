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
        """Get portfolio for specific account using PortfolioItem objects.
        
        Args:
            account_id: Account ID to get portfolio for
            
        Returns:
            List of PortfolioItem objects from ib_insync with base currency values
            
        Raises:
            SimpleOrderManagementPlatformError: If unable to retrieve portfolio
        """
        try:
            logger.info(f"Requesting portfolio for account: {account_id}")
            
            # Use ib.portfolio() to get PortfolioItem objects with base currency values
            # This is critical for accurate weight calculations as it provides values in account's base currency
            logger.debug(f"Using portfolio() method to get base currency values with optimizations")
            
            # Get all portfolio items and filter by account
            all_portfolio_items = self.ib.portfolio()
            account_portfolio = [item for item in all_portfolio_items if item.account == account_id]
            
            # Optimized wait time to reduce timeout risk (0.5s instead of 1s)
            self.ib.sleep(0.5)
            
            logger.info(f"Retrieved {len(account_portfolio)} portfolio items for account {account_id}")
            return account_portfolio
            
        except Exception as e:
            logger.error(f"Error retrieving portfolio for account {account_id}: {e}")
            raise SimpleOrderManagementPlatformError(
                f"Failed to get portfolio for account {account_id}: {e}"
            )
    
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get account summary information in base currency.
        
        Args:
            account_id: Account ID to get summary for
            
        Returns:
            Dictionary with account summary data in account's base currency
            
        Raises:
            SimpleOrderManagementPlatformError: If unable to retrieve account summary
        """
        try:
            logger.info(f"Requesting account summary for: {account_id}")
            
            # Use reqAccountSummary() with '$LEDGER' group to get base currency values
            # This ensures all values are converted to the account's base currency (SGD in this case)
            logger.debug(f"Using reqAccountSummary() with $LEDGER group for base currency values")
            
            # Define the tags we want to retrieve in base currency  
            tags = [
                'NetLiquidation', 'TotalCashValue', 'SettledCash', 'AccruedCash',
                'BuyingPower', 'EquityWithLoanValue', 'GrossPositionValue',
                'UnrealizedPnL', 'RealizedPnL', 'AccountType'
            ]
            
            # Request account summary using $LEDGER group for base currency conversion
            summary_items = self.ib.reqAccountSummary(group='$LEDGER', tags=','.join(tags))
            
            # Wait for data
            self.ib.sleep(2)  # Extra time to ensure all data is received
            
            # Convert to dictionary, filtering for the specific account
            summary_dict = {}
            for item in summary_items:
                if item.account == account_id:
                    summary_dict[item.tag] = item.value
                    logger.debug(f"Account {account_id} - {item.tag}: {item.value} {item.currency}")
                    
            logger.info(f"Retrieved account summary for {account_id}: {len(summary_dict)} items in base currency")
            return summary_dict
            
        except Exception as e:
            logger.error(f"Error retrieving account summary for {account_id}: {e}")
            # Fallback to original method if reqAccountSummary fails
            try:
                logger.warning(f"Falling back to original accountSummary() method for {account_id}")
                summary_items = self.ib.accountSummary(account_id)
                self.ib.sleep(1)
                
                summary_dict = {}
                for item in summary_items:
                    if item.account == account_id:
                        summary_dict[item.tag] = item.value
                        
                logger.info(f"Retrieved account summary (fallback) for {account_id}: {len(summary_dict)} items")
                return summary_dict
            except Exception as fallback_e:
                logger.error(f"Fallback method also failed for {account_id}: {fallback_e}")
                raise SimpleOrderManagementPlatformError(
                    f"Failed to get account summary for {account_id}: {e}, fallback: {fallback_e}"
                )
    
    def _convert_ib_portfolio_item_to_position(self, ib_portfolio_item, account_id: str) -> Position:
        """Convert ib_insync PortfolioItem object to Position model.
        
        Args:
            ib_portfolio_item: ib_insync PortfolioItem object with base currency values
            account_id: Account ID for this position
            
        Returns:
            Position model object
        """
        try:
            contract = ib_portfolio_item.contract
            
            # PortfolioItem objects provide marketPrice and marketValue in account's base currency
            # This ensures accurate weight calculations across different instrument currencies
>>>>>>> 9546905 (Fix currency conversion issue and add Amt_Matrix sheet)
            
            market_price = None
            market_value = None
            
            # Method 1: Use PortfolioItem's built-in marketPrice (in base currency)
            if hasattr(ib_portfolio_item, 'marketPrice') and ib_portfolio_item.marketPrice:
                market_price = ib_portfolio_item.marketPrice
                logger.debug(f"Using PortfolioItem marketPrice for {contract.symbol}: {market_price}")
            
            # Method 2: Use PortfolioItem's built-in marketValue (in base currency)
            if hasattr(ib_portfolio_item, 'marketValue') and ib_portfolio_item.marketValue:
                market_value = ib_portfolio_item.marketValue
                logger.debug(f"Using PortfolioItem marketValue for {contract.symbol}: {market_value}")
            
            # Method 3: Try cached prices if configured (only as fallback)
            if not market_price and self.use_cached_prices:
                try:
                    from ..services.market_data_service import market_data_service
                    cached_price_data = market_data_service.get_cached_price(contract.symbol)
                    if cached_price_data:
                        market_price = cached_price_data['close_price']
                        logger.debug(f"Using cached price for {contract.symbol}: {market_price}")
                        # Note: cached price may not be in base currency - this is why PortfolioItem is preferred
                except Exception as e:
                    logger.debug(f"Could not get cached price for {contract.symbol}: {e}")
            
            # Method 4: Fallback to averageCost if no other price available  
            if not market_price and hasattr(ib_portfolio_item, 'averageCost') and ib_portfolio_item.averageCost:
                market_price = ib_portfolio_item.averageCost
                logger.debug(f"Using averageCost as market price for {contract.symbol}: {market_price}")
                
            # Calculate market value if not already available (should not be needed with PortfolioItem)
            if not market_value and market_price and ib_portfolio_item.position:
                multiplier = getattr(contract, 'multiplier', 1)
                if multiplier and multiplier != '':
                    try:
                        multiplier = int(multiplier)
                    except (ValueError, TypeError):
                        multiplier = 1
                else:
                    multiplier = 1
                    
                market_value = Decimal(str(market_price)) * Decimal(str(ib_portfolio_item.position)) * Decimal(str(multiplier))
            
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
                position=Decimal(str(ib_portfolio_item.position)),
                market_price=safe_decimal(market_price),
                market_value=safe_decimal(market_value),
                avg_cost=safe_decimal(ib_portfolio_item.averageCost),
                unrealized_pnl=safe_decimal(getattr(ib_portfolio_item, 'unrealizedPNL', None)),  # PortfolioItem objects have PnL
                realized_pnl=safe_decimal(getattr(ib_portfolio_item, 'realizedPNL', None)),
                local_symbol=getattr(contract, 'localSymbol', None),
                multiplier=int(getattr(contract, 'multiplier', 1)) if getattr(contract, 'multiplier', '') != '' else None,
                last_trade_date=getattr(contract, 'lastTradeDateOrContractMonth', None),
            )
            
            return position
            
        except Exception as e:
            logger.error(f"Error converting IB PortfolioItem to Position model: {e}")
            logger.error(f"IB PortfolioItem data: {ib_portfolio_item}")
            raise SimpleOrderManagementPlatformError(f"Failed to convert portfolio item data: {e}")
    
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
            currency='SGD',  # Base currency (Singapore Dollar) as mentioned in requirements
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
            
            # Get portfolio positions for this account
            ib_portfolio = self.get_account_portfolio(account_id)
            
            # Convert PortfolioItem objects to Position objects
            positions = []
            cached_price_count = 0
            for ib_portfolio_item in ib_portfolio:
                try:
                    position = self._convert_ib_portfolio_item_to_position(ib_portfolio_item, account_id)
                    
                    # Cached prices are already applied in _convert_ib_portfolio_item_to_position
                    if self.use_cached_prices and position.market_price:
                        cached_price_count += 1
                    
                    positions.append(position)
                    logger.debug(f"Converted position: {position.symbol} = {position.market_value}")
                except Exception as e:
                    logger.warning(f"Failed to convert portfolio item {ib_portfolio_item}: {e}")
                    continue
            
            # Get account summary
            summary_dict = self.get_account_summary(account_id)
            account_summary = self._convert_account_summary_dict_to_model(summary_dict, account_id)
            
            # Create portfolio snapshot
            snapshot = PortfolioSnapshot(
                account_id=account_id,
                positions=positions,
                account_summary=account_summary,
                timestamp=datetime.now()
            )
            
            active_positions = [p for p in positions if p.position != 0]
            total_value = snapshot.get_total_portfolio_value() or Decimal(0)
            
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
            # Create multi-portfolio container
            multi_portfolio = MultiAccountPortfolio(timestamp=datetime.now())
            
            # Determine which accounts to download
            if account_ids is None:
                logger.info("Downloading all managed account portfolios using ib_insync")
                account_ids = self.get_all_accounts()
            else:
                logger.info(f"Downloading portfolios for {len(account_ids)} specified accounts: {account_ids}")
            
            # Download each account's portfolio
            successful_downloads = 0
            for account_id in account_ids:
                try:
                    logger.info(f"Downloading portfolio for account: {account_id}")
                    snapshot = self.download_account_portfolio(account_id)
                    multi_portfolio.add_snapshot(snapshot)
                    successful_downloads += 1
                    logger.info(f"Successfully downloaded portfolio for account: {account_id}")
                except Exception as e:
                    logger.error(f"Failed to download portfolio for account {account_id}: {e}")
                    # Continue with other accounts even if one fails
                    continue
            
            if successful_downloads == 0:
                raise SimpleOrderManagementPlatformError("No portfolios were successfully downloaded")
            
            combined_summary = multi_portfolio.get_combined_summary()
            logger.info(f"Successfully downloaded {combined_summary['total_accounts']} portfolios, "
                       f"Total value: SGD {combined_summary['total_portfolio_value']:,.2f}")
            return multi_portfolio
            
        except Exception as e:
            logger.error(f"Error downloading portfolios: {e}")
            raise SimpleOrderManagementPlatformError(f"Failed to download portfolios: {e}")