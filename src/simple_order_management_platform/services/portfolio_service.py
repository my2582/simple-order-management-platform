"""Portfolio service for downloading and managing portfolio positions."""

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
    """Service for downloading and managing portfolio positions from IBKR."""
    
    def __init__(self, ib_provider: IBProvider):
        """Initialize portfolio service.
        
        Args:
            ib_provider: Interactive Brokers provider instance
        """
        self.ib_provider = ib_provider
        self.ib: IB = ib_provider.connector.ib
    
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
            
            # Get all positions and filter by account
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
            
            # Define the tags we want to retrieve
            tags = [
                'NetLiquidation', 'TotalCashValue', 'SettledCash', 'AccruedCash',
                'BuyingPower', 'EquityWithLoanValue', 'GrossPositionValue',
                'UnrealizedPnL', 'RealizedPnL', 'AccountType'
            ]
            
            # Request account summary
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
    
    def _convert_ib_portfolio_to_position(self, ib_position, account_id: str) -> Position:
        """Convert ib_insync Position object to Position model.
        
        Args:
            ib_position: ib_insync Position object
            account_id: Account ID for this position
            
        Returns:
            Position model object
        """
        try:
            contract = ib_position.contract
            
            # Use avgCost as fallback for market price when live data unavailable
            market_price = None
            market_value = None
            
            # Try to get market price, but fallback to avgCost if unavailable
            try:
                # For delayed/paper trading, use avgCost as market price approximation
                if hasattr(ib_position, 'avgCost') and ib_position.avgCost:
                    market_price = ib_position.avgCost
                    logger.debug(f"Using avgCost as market price for {contract.symbol}: {market_price}")
                
            except Exception as e:
                logger.warning(f"Could not determine market price for {contract.symbol}: {e}")
                
            # Calculate market value
            if market_price and ib_position.position:
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
                unrealized_pnl=None,  # Position object doesn't have PnL info
                realized_pnl=None,
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
        """Download complete portfolio snapshot for a single account.
        
        Args:
            account_id: Account ID to download portfolio for
            
        Returns:
            PortfolioSnapshot with positions and account summary
            
        Raises:
            SimpleOrderManagementPlatformError: If download fails
        """
        try:
            logger.info(f"Downloading portfolio snapshot for account: {account_id}")
            
            # Get portfolio positions
            ib_portfolio = self.get_account_portfolio(account_id)
            
            # Convert to Position objects
            positions = []
            cached_price_count = 0
            for ib_position in ib_portfolio:
                try:
                    position = self._convert_ib_portfolio_to_position(ib_position, account_id)
                    
                    # Apply cached prices if configured
                    if self.use_cached_prices and position.symbol:
                        cached_price_data = market_data_service.get_cached_price(position.symbol)
                        if cached_price_data:
                            # Update market price with cached price
                            old_price = position.market_price
                            position.market_price = Decimal(str(cached_price_data['close_price']))
                            
                            # Update market value
                            if position.position and position.market_price:
                                position.market_value = position.position * position.market_price
                            
                            cached_price_count += 1
                            logger.debug(f"Updated {position.symbol}: {old_price} -> {position.market_price} (cached)")
                        else:
                            logger.warning(f"No cached price found for {position.symbol}, using live data")
                    
                    positions.append(position)
                except Exception as e:
                    logger.warning(f"Failed to convert position {ib_position}: {e}")
                    continue
            
            if self.use_cached_prices and cached_price_count > 0:
                logger.info(f"Applied cached prices to {cached_price_count}/{len(positions)} positions")
            
            # Get account summary
            try:
                summary_dict = self.get_account_summary(account_id)
                account_summary = self._convert_account_summary_dict_to_model(summary_dict, account_id)
            except Exception as e:
                logger.warning(f"Failed to get account summary for {account_id}: {e}")
                account_summary = None
            
            # Create portfolio snapshot
            snapshot = PortfolioSnapshot(
                account_id=account_id,
                timestamp=datetime.now(),
                positions=positions,
                account_summary=account_summary
            )
            
            logger.info(f"Successfully downloaded portfolio for {account_id}: "
                       f"{len(positions)} positions, "
                       f"Total value: {snapshot.get_total_portfolio_value()}")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error downloading portfolio for account {account_id}: {e}")
            raise SimpleOrderManagementPlatformError(
                f"Failed to download portfolio for account {account_id}: {e}"
            )
    
    def download_all_portfolios(self, account_ids: Optional[List[str]] = None) -> MultiAccountPortfolio:
        """Download portfolio snapshots for all or specified accounts.
        
        Args:
            account_ids: Optional list of specific account IDs. If None, downloads all accounts.
            
        Returns:
            MultiAccountPortfolio with snapshots for all accounts
            
        Raises:
            SimpleOrderManagementPlatformError: If download fails
        """
        try:
            # Get accounts to process
            if account_ids is None:
                account_ids = self.get_all_accounts()
            
            logger.info(f"Downloading portfolios for {len(account_ids)} accounts: {account_ids}")
            
            # Create multi-account portfolio
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
            
            logger.info(f"Successfully downloaded {len(multi_portfolio.snapshots)} portfolios")
            return multi_portfolio
            
        except Exception as e:
            logger.error(f"Error downloading portfolios: {e}")
            raise SimpleOrderManagementPlatformError(f"Failed to download portfolios: {e}")