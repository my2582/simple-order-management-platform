"""Portfolio and Position data models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Individual position in a portfolio."""
    
    account_id: str
    symbol: str
    contract_id: int
    exchange: str
    currency: str
    sec_type: str  # STK, FUT, OPT, etc.
    position: Decimal  # Number of shares/contracts
    market_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None  # position * market_price
    avg_cost: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    
    # Additional metadata
    local_symbol: Optional[str] = None
    multiplier: Optional[int] = None
    last_trade_date: Optional[str] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
        
    def get_absolute_position_value(self) -> Optional[Decimal]:
        """Get absolute value of position (for weight calculations)."""
        if self.market_value is not None:
            return abs(self.market_value)
        return None
    
    @classmethod
    def from_ib_portfolio_item(cls, item) -> 'Position':
        """Create Position from ib_insync portfolio item.
        
        Args:
            item: PortfolioItem from ib_insync
            
        Returns:
            Position with values in account base currency
        """
        return cls(
            account_id=item.account,
            symbol=item.contract.symbol,
            contract_id=item.contract.conId,
            exchange=item.contract.exchange or item.contract.primaryExchange or 'SMART',
            currency=item.contract.currency,
            sec_type=item.contract.secType,
            position=Decimal(str(item.position)),
            market_price=Decimal(str(item.marketPrice)) if hasattr(item, 'marketPrice') and item.marketPrice else None,
            market_value=Decimal(str(item.marketValue)) if hasattr(item, 'marketValue') and item.marketValue else None,
            avg_cost=Decimal(str(item.averageCost)) if hasattr(item, 'averageCost') and item.averageCost else None,
            unrealized_pnl=Decimal(str(item.unrealizedPNL)) if hasattr(item, 'unrealizedPNL') and item.unrealizedPNL else None,
            realized_pnl=Decimal(str(item.realizedPNL)) if hasattr(item, 'realizedPNL') and item.realizedPNL else None,
            local_symbol=getattr(item.contract, 'localSymbol', None),
            multiplier=None,  # Skip multiplier validation for now
            last_trade_date=getattr(item.contract, 'lastTradeDateOrContractMonth', None),
        )
    
    @classmethod
    def from_ib_position(cls, pos, market_price: Optional[Decimal] = None) -> 'Position':
        """Create Position from ib_insync Position object.
        
        Args:
            pos: Position object from ib_insync
            market_price: Current market price (optional)
            
        Returns:
            Position with values in account base currency
        """
        # Safe conversion for multiplier (can be empty string, None, or numeric)\n        def safe_int_convert(value):\n            if value is None or value == '' or value == '0':\n                return None\n            try:\n                return int(value)\n            except (ValueError, TypeError):\n                return None\n        \n        # Calculate market value if we have market price
        market_value = None
        unrealized_pnl = None
        
        if market_price and pos.position:
            market_value = Decimal(str(pos.position)) * market_price
            
            # Calculate unrealized PnL if we have avg cost
            if pos.avgCost:
                avg_cost = Decimal(str(pos.avgCost))
                unrealized_pnl = (market_price - avg_cost) * Decimal(str(pos.position))
        
        return cls(
            account_id=pos.account,
            symbol=pos.contract.symbol,
            contract_id=pos.contract.conId,
            exchange=pos.contract.exchange or pos.contract.primaryExchange or 'SMART',
            currency=pos.contract.currency,
            sec_type=pos.contract.secType,
            position=Decimal(str(pos.position)),
            market_price=market_price,
            market_value=market_value,
            avg_cost=Decimal(str(pos.avgCost)) if pos.avgCost else None,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=None,  # Not available in ib_insync Position object
            local_symbol=getattr(pos.contract, 'localSymbol', None),
            multiplier=safe_int_convert(getattr(pos.contract, 'multiplier', None)),
            last_trade_date=getattr(pos.contract, 'lastTradeDateOrContractMonth', None),
        )


class AccountSummary(BaseModel):
    """Account summary information."""
    
    account_id: str
    account_type: Optional[str] = None
    currency: str = "USD"
    
    # Key financial metrics
    net_liquidation: Optional[Decimal] = None
    total_cash_value: Optional[Decimal] = None
    settled_cash: Optional[Decimal] = None
    accrued_cash: Optional[Decimal] = None
    buying_power: Optional[Decimal] = None
    equity_with_loan_value: Optional[Decimal] = None
    gross_position_value: Optional[Decimal] = None
    
    # PnL information
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    @classmethod
    def from_ib_account_values(cls, account_values, account_id: str) -> 'AccountSummary':
        """Create AccountSummary from ib_insync account values.
        
        Args:
            account_values: List of account values from ib.accountValues()
            account_id: Account identifier
            
        Returns:
            AccountSummary with values in account base currency
        """
        # Convert account values list to dictionary for easier access
        values_dict = {}
        base_currency = 'SGD'  # Default to SGD
        
        for av in account_values:
            # Use base currency values (empty currency field means base currency)
            if av.currency == '' or av.currency == 'BASE':
                values_dict[av.tag] = av.value
                if av.currency == 'BASE' and hasattr(av, 'currency'):
                    # Try to get the actual base currency if available
                    pass
        
        # Map IBKR account value tags to our fields
        def safe_decimal(value_str: str) -> Optional[Decimal]:
            try:
                return Decimal(value_str) if value_str else None
            except (ValueError, TypeError):
                return None
        
        return cls(
            account_id=account_id,
            currency=base_currency,
            net_liquidation=safe_decimal(values_dict.get('NetLiquidation')),
            total_cash_value=safe_decimal(values_dict.get('TotalCashValue')),
            settled_cash=safe_decimal(values_dict.get('SettledCash')),
            accrued_cash=safe_decimal(values_dict.get('AccruedCash')),
            buying_power=safe_decimal(values_dict.get('BuyingPower')),
            equity_with_loan_value=safe_decimal(values_dict.get('EquityWithLoanValue')),
            gross_position_value=safe_decimal(values_dict.get('GrossPositionValue')),
            unrealized_pnl=safe_decimal(values_dict.get('UnrealizedPnL')),
            realized_pnl=safe_decimal(values_dict.get('RealizedPnL')),
        )


class PortfolioSnapshot(BaseModel):
    """Complete portfolio snapshot for a single account."""
    
    account_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    positions: List[Position] = Field(default_factory=list)
    account_summary: Optional[AccountSummary] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    def get_total_portfolio_value(self) -> Optional[Decimal]:
        """Get total portfolio value from account summary or calculated from positions."""
        if self.account_summary and self.account_summary.net_liquidation:
            return self.account_summary.net_liquidation
            
        # Fallback: calculate from positions
        total = Decimal(0)
        for position in self.positions:
            if position.market_value:
                total += position.market_value
                
        return total if total != 0 else None
    
    def get_cash_percentage(self) -> Optional[Decimal]:
        """Get cash percentage of portfolio."""
        if not self.account_summary:
            return None
            
        total_value = self.get_total_portfolio_value()
        cash_value = self.account_summary.total_cash_value
        
        if total_value and cash_value and total_value != 0:
            return (cash_value / total_value) * Decimal(100)
        
        return None
    
    def get_position_weights(self) -> Dict[str, Decimal]:
        """Get position weights as percentage of total portfolio."""
        weights = {}
        total_value = self.get_total_portfolio_value()
        
        if not total_value or total_value == 0:
            return weights
            
        for position in self.positions:
            if position.market_value and position.symbol:
                weight = (abs(position.market_value) / total_value) * Decimal(100)
                weights[position.symbol] = weight
                
        return weights
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get positions summary for Excel export."""
        summary = []
        weights = self.get_position_weights()
        
        for position in self.positions:
            if position.position == 0:  # Skip zero positions
                continue
                
            pos_data = {
                'Symbol': position.symbol,
                'Exchange': position.exchange,
                'Currency': position.currency,
                'SecType': position.sec_type,
                'Position': float(position.position),
                'Market_Price': float(position.market_price) if position.market_price else None,
                'Market_Value': float(position.market_value) if position.market_value else None,
                'Weight_Pct': float(weights.get(position.symbol, Decimal(0))),
                'Avg_Cost': float(position.avg_cost) if position.avg_cost else None,
                'Unrealized_PnL': float(position.unrealized_pnl) if position.unrealized_pnl else None,
                'Local_Symbol': position.local_symbol,
            }
            summary.append(pos_data)
            
        return {
            'positions': summary,
            'cash_percentage': float(self.get_cash_percentage() or Decimal(0)),
            'total_value': float(self.get_total_portfolio_value() or Decimal(0)),
            'account_id': self.account_id,
            'timestamp': self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_ib_connection(cls, ib, account: str = '') -> 'PortfolioSnapshot':
        """Create portfolio snapshot directly from ib_insync connection.
        
        Args:
            ib: Connected ib_insync IB instance
            account: Account ID (empty string for single account)
            
        Returns:
            PortfolioSnapshot with all values in account base currency (SGD)
        """
        try:
            import asyncio
            from ib_insync import util
            
            # Use ib.positions() to get all positions with account filter
            all_positions = ib.positions()
            
            # Filter positions by account if specified
            if account:
                account_positions = [pos for pos in all_positions if pos.account == account]
            else:
                # If no account specified, get all positions
                account_positions = all_positions
            
            # Get account values for the specific account
            account_values = ib.accountValues(account)
            
            # Create Position objects and get market data
            positions = []
            contracts_to_price = []
            
            for pos in account_positions:
                if pos.position == 0:
                    continue  # Skip zero positions
                
                # Add contract for market data request
                contracts_to_price.append(pos.contract)
                
                # Create basic position (market price will be added later)
                position = Position(
                    account_id=pos.account,
                    symbol=pos.contract.symbol,
                    contract_id=pos.contract.conId,
                    exchange=pos.contract.exchange or pos.contract.primaryExchange or 'SMART',
                    currency=pos.contract.currency,
                    sec_type=pos.contract.secType,
                    position=Decimal(str(pos.position)),
                    market_price=None,  # Will be filled later
                    market_value=None,  # Will be calculated later
                    avg_cost=Decimal(str(pos.avgCost)) if pos.avgCost else None,
                    unrealized_pnl=None,  # Will be calculated later
                    realized_pnl=None,
                    local_symbol=getattr(pos.contract, 'localSymbol', None),
                    multiplier=safe_int_convert(getattr(pos.contract, 'multiplier', None)),
                    last_trade_date=getattr(pos.contract, 'lastTradeDateOrContractMonth', None),
                )
                positions.append(position)
            
            # Get market data for all contracts
            if contracts_to_price:
                try:
                    # Request market data for all contracts
                    tickers = ib.reqTickers(*contracts_to_price)
                    
                    # Update positions with market prices
                    for i, ticker in enumerate(tickers):
                        if i < len(positions) and ticker.marketPrice():
                            market_price = Decimal(str(ticker.marketPrice()))
                            positions[i].market_price = market_price
                            
                            # Calculate market value in base currency (SGD)
                            if positions[i].position and market_price:
                                market_value = positions[i].position * market_price
                                positions[i].market_value = market_value
                                
                                # Calculate unrealized PnL if we have avg cost
                                if positions[i].avg_cost:
                                    unrealized_pnl = (market_price - positions[i].avg_cost) * positions[i].position
                                    positions[i].unrealized_pnl = unrealized_pnl
                                    
                except Exception as e:
                    print(f"Warning: Could not get market data for account {account}: {e}")
                    # Continue without market prices - positions will show avg cost only
            
            # Create account summary from account values
            account_summary = AccountSummary.from_ib_account_values(account_values, account or 'Default')
            
            return cls(
                account_id=account or 'Default',
                positions=positions,
                account_summary=account_summary,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            # Fallback to empty portfolio if there's an error
            print(f"Warning: Error creating portfolio snapshot for account {account}: {e}")
            return cls(
                account_id=account or 'Default',
                positions=[],
                account_summary=None,
                timestamp=datetime.now()
            )


class MultiAccountPortfolio(BaseModel):
    """Multiple account portfolio collection."""
    
    snapshots: List[PortfolioSnapshot] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    def add_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Add a portfolio snapshot."""
        self.snapshots.append(snapshot)
    
    def get_account_ids(self) -> List[str]:
        """Get list of all account IDs."""
        return [snapshot.account_id for snapshot in self.snapshots]
    
    def get_snapshot_by_account(self, account_id: str) -> Optional[PortfolioSnapshot]:
        """Get portfolio snapshot by account ID."""
        for snapshot in self.snapshots:
            if snapshot.account_id == account_id:
                return snapshot
        return None
    
    def get_combined_summary(self) -> Dict[str, Any]:
        """Get combined summary across all accounts."""
        total_value = Decimal(0)
        total_positions = 0
        
        for snapshot in self.snapshots:
            portfolio_value = snapshot.get_total_portfolio_value()
            if portfolio_value:
                total_value += portfolio_value
            total_positions += len([p for p in snapshot.positions if p.position != 0])
        
        return {
            'total_accounts': len(self.snapshots),
            'total_portfolio_value': float(total_value),
            'total_positions': total_positions,
            'timestamp': self.timestamp.isoformat(),
            'account_ids': self.get_account_ids(),
        }
    
    @classmethod
    def from_ib_connection(cls, ib) -> 'MultiAccountPortfolio':
        """Create multi-account portfolio from ib_insync connection.
        
        Args:
            ib: Connected ib_insync IB instance
            
        Returns:
            MultiAccountPortfolio with snapshots for all managed accounts
        """
        try:
            # Get all managed accounts
            managed_accounts = ib.managedAccounts()
            
            # Create portfolio snapshots for each account
            snapshots = []
            for account in managed_accounts:
                try:
                    snapshot = PortfolioSnapshot.from_ib_connection(ib, account)
                    snapshots.append(snapshot)
                except Exception as e:
                    print(f"Warning: Failed to get portfolio for account {account}: {e}")
                    continue
            
            return cls(
                snapshots=snapshots,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Error creating multi-account portfolio: {e}")
            return cls(
                snapshots=[],
                timestamp=datetime.now()
            )


# Utility functions for easy integration

def get_portfolio_snapshot(ib, account: str = '') -> PortfolioSnapshot:
    """
    Quick function to get portfolio snapshot from ib_insync connection.
    All values automatically in account base currency (SGD).
    
    Args:
        ib: Connected ib_insync IB instance
        account: Account ID (empty for single account)
    """
    return PortfolioSnapshot.from_ib_connection(ib, account)


def get_all_portfolios(ib) -> MultiAccountPortfolio:
    """
    Quick function to get all managed account portfolios.
    All values automatically in respective account base currencies.
    
    Args:
        ib: Connected ib_insync IB instance
    """
    return MultiAccountPortfolio.from_ib_connection(ib)


def export_portfolio_to_excel(portfolio: PortfolioSnapshot, filename: str) -> bool:
    """
    Export portfolio to Excel file.
    
    Args:
        portfolio: Portfolio snapshot to export
        filename: Output Excel filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import pandas as pd
        
        summary = portfolio.get_positions_summary()
        
        # Create DataFrames
        positions_df = pd.DataFrame(summary['positions'])
        
        # Account summary as a separate sheet
        account_data = {
            'Account_ID': [portfolio.account_id],
            'Total_Value': [summary['total_value']],
            'Cash_Percentage': [summary['cash_percentage']],
            'Timestamp': [summary['timestamp']]
        }
        account_df = pd.DataFrame(account_data)
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            positions_df.to_excel(writer, sheet_name='Positions', index=False)
            account_df.to_excel(writer, sheet_name='Account_Summary', index=False)
        
        return True
        
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return False