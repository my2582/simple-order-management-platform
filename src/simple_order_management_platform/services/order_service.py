"""Order generation service for creating trade orders based on model portfolios."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd

from ..models.portfolio import PortfolioSnapshot
from ..models.model_portfolio import ModelPortfolio
from ..utils.exceptions import SimpleOrderManagementPlatformError


logger = logging.getLogger(__name__)


class OrderItem:
    """Individual order item."""
    
    def __init__(
        self,
        account_id: str,
        symbol: str,
        action: str,  # BUY or SELL
        quantity: Optional[int] = None,
        amount: Optional[Decimal] = None,
        order_type: str = "MKT",  # Market order by default
        notes: str = "",
    ):
        self.account_id = account_id
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.amount = amount  # Dollar amount for fractional shares
        self.order_type = order_type
        self.notes = notes
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            'Account_ID': self.account_id,
            'Symbol': self.symbol,
            'Action': self.action,
            'Quantity': self.quantity,
            'Amount': float(self.amount) if self.amount else None,
            'Order_Type': self.order_type,
            'Notes': self.notes,
            'Timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }


class OrderBatch:
    """Collection of orders for batch execution."""
    
    def __init__(self, name: str = ""):
        self.name = name or f"OrderBatch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.orders: List[OrderItem] = []
        self.created_at = datetime.now()
    
    def add_order(self, order: OrderItem) -> None:
        """Add an order to the batch."""
        self.orders.append(order)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get batch summary."""
        total_buy_amount = sum(
            order.amount for order in self.orders 
            if order.action == 'BUY' and order.amount
        )
        total_sell_amount = sum(
            abs(order.amount) for order in self.orders 
            if order.action == 'SELL' and order.amount
        )
        
        accounts = set(order.account_id for order in self.orders)
        symbols = set(order.symbol for order in self.orders)
        
        return {
            'batch_name': self.name,
            'total_orders': len(self.orders),
            'buy_orders': len([o for o in self.orders if o.action == 'BUY']),
            'sell_orders': len([o for o in self.orders if o.action == 'SELL']),
            'total_buy_amount': float(total_buy_amount),
            'total_sell_amount': float(total_sell_amount),
            'net_amount': float(total_buy_amount - total_sell_amount),
            'accounts_involved': list(accounts),
            'symbols_involved': list(symbols),
            'created_at': self.created_at.isoformat(),
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert orders to pandas DataFrame."""
        if not self.orders:
            return pd.DataFrame()
        
        return pd.DataFrame([order.to_dict() for order in self.orders])
    
    def save_to_csv(self, output_path: Path) -> Path:
        """Save order batch to CSV file."""
        df = self.to_dataframe()
        if df.empty:
            raise SimpleOrderManagementPlatformError("No orders to export")
        
        df.to_csv(output_path, index=False)
        logger.info(f"Order batch saved to: {output_path}")
        return output_path


class OrderService:
    """Service for generating trading orders based on model portfolios and current positions."""
    
    def __init__(self, model_portfolio_manager: ModelPortfolioManager):
        """Initialize order service.
        
        Args:
            model_portfolio_manager: Manager containing model portfolios
        """
        self.model_portfolio_manager = model_portfolio_manager
    
    def generate_rebalancing_orders(
        self,
        account_id: str,
        portfolio_id: str,
        current_snapshot: PortfolioSnapshot,
        target_amount: Decimal,
        min_trade_amount: Decimal = Decimal('100')
    ) -> OrderBatch:
        """Generate rebalancing orders to match model portfolio.
        
        Args:
            account_id: Account ID to generate orders for
            portfolio_id: Model portfolio ID to target
            current_snapshot: Current portfolio positions
            target_amount: Total target investment amount
            min_trade_amount: Minimum trade amount threshold
            
        Returns:
            OrderBatch with generated orders
        """
        # Get model portfolio
        model_portfolio = self.model_portfolio_manager.get_portfolio(portfolio_id)
        if not model_portfolio:
            raise SimpleOrderManagementPlatformError(f"Model portfolio '{portfolio_id}' not found")
        
        # Get current positions as {symbol: market_value} dict
        current_positions = {}
        for position in current_snapshot.positions:
            if position.market_value and position.symbol:
                current_positions[position.symbol] = position.market_value
        
        # Calculate required trades
        trades = calculate_rebalancing_orders(
            model_portfolio=model_portfolio,
            current_positions=current_positions,
            target_amount=target_amount,
            min_trade_amount=min_trade_amount
        )
        
        # Create order batch
        batch_name = f"Rebalance_{account_id}_{portfolio_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        order_batch = OrderBatch(batch_name)
        
        # Generate orders from trades
        for symbol, trade_amount in trades.items():
            if trade_amount == 0:
                continue
            
            action = "BUY" if trade_amount > 0 else "SELL"
            amount = abs(trade_amount)
            
            notes = f"Rebalance to {portfolio_id} model"
            if symbol in model_portfolio.get_target_amounts(target_amount):
                target_weight = None
                for holding in model_portfolio.holdings:
                    if holding.get_instrument_identifier() == symbol:
                        target_weight = holding.weight
                        break
                if target_weight:
                    notes += f" (target: {target_weight}%)"
            
            order = OrderItem(
                account_id=account_id,
                symbol=symbol,
                action=action,
                amount=amount,
                order_type="MKT",
                notes=notes
            )
            
            order_batch.add_order(order)
        
        logger.info(f"Generated {len(order_batch.orders)} rebalancing orders for account {account_id}")
        return order_batch
    
    def generate_deposit_orders(
        self,
        account_id: str,
        portfolio_id: str,
        deposit_amount: Decimal
    ) -> OrderBatch:
        """Generate orders for new deposit allocation.
        
        Args:
            account_id: Account ID for the deposit
            portfolio_id: Model portfolio ID to follow
            deposit_amount: Amount being deposited
            
        Returns:
            OrderBatch with generated orders
        """
        # Get model portfolio
        model_portfolio = self.model_portfolio_manager.get_portfolio(portfolio_id)
        if not model_portfolio:
            raise SimpleOrderManagementPlatformError(f"Model portfolio '{portfolio_id}' not found")
        
        # Calculate target amounts for deposit
        target_amounts = model_portfolio.get_target_amounts(deposit_amount)
        
        # Create order batch
        batch_name = f"Deposit_{account_id}_{portfolio_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        order_batch = OrderBatch(batch_name)
        
        # Generate buy orders for each holding
        for symbol, amount in target_amounts.items():
            if amount <= 0:
                continue
            
            # Find the weight for notes
            target_weight = None
            for holding in model_portfolio.holdings:
                if holding.get_instrument_identifier() == symbol:
                    target_weight = holding.weight
                    break
            
            notes = f"New deposit allocation to {portfolio_id}"
            if target_weight:
                notes += f" ({target_weight}% target weight)"
            
            order = OrderItem(
                account_id=account_id,
                symbol=symbol,
                action="BUY",
                amount=amount,
                order_type="MKT",
                notes=notes
            )
            
            order_batch.add_order(order)
        
        logger.info(f"Generated {len(order_batch.orders)} deposit orders for ${deposit_amount} in account {account_id}")
        return order_batch
    
    def generate_withdrawal_orders(
        self,
        account_id: str,
        current_snapshot: PortfolioSnapshot,
        withdrawal_amount: Decimal,
        proportional: bool = True
    ) -> OrderBatch:
        """Generate orders for withdrawal.
        
        Args:
            account_id: Account ID for the withdrawal
            current_snapshot: Current portfolio positions
            withdrawal_amount: Amount to withdraw
            proportional: If True, sell proportionally; if False, sell largest positions first
            
        Returns:
            OrderBatch with generated orders
        """
        # Calculate current total value
        total_value = current_snapshot.get_total_portfolio_value()
        if not total_value or total_value <= 0:
            raise SimpleOrderManagementPlatformError("Cannot determine current portfolio value")
        
        if withdrawal_amount > total_value:
            raise SimpleOrderManagementPlatformError(
                f"Withdrawal amount ${withdrawal_amount} exceeds portfolio value ${total_value}"
            )
        
        # Create order batch
        batch_name = f"Withdrawal_{account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        order_batch = OrderBatch(batch_name)
        
        # Calculate positions to sell
        remaining_to_sell = withdrawal_amount
        
        if proportional:
            # Sell proportionally from all positions
            withdrawal_ratio = withdrawal_amount / total_value
            
            for position in current_snapshot.positions:
                if not position.market_value or position.market_value <= 0 or position.symbol is None:
                    continue
                
                sell_amount = position.market_value * withdrawal_ratio
                if sell_amount <= 0:
                    continue
                
                order = OrderItem(
                    account_id=account_id,
                    symbol=position.symbol,
                    action="SELL",
                    amount=sell_amount,
                    order_type="MKT",
                    notes=f"Proportional withdrawal (${withdrawal_amount} total)"
                )
                
                order_batch.add_order(order)
                
        else:
            # Sell largest positions first
            positions_by_value = sorted(
                [p for p in current_snapshot.positions if p.market_value and p.market_value > 0 and p.symbol],
                key=lambda x: x.market_value,
                reverse=True
            )
            
            for position in positions_by_value:
                if remaining_to_sell <= 0:
                    break
                
                sell_amount = min(remaining_to_sell, position.market_value)
                
                order = OrderItem(
                    account_id=account_id,
                    symbol=position.symbol,
                    action="SELL",
                    amount=sell_amount,
                    order_type="MKT",
                    notes=f"Withdrawal - largest positions first (${withdrawal_amount} total)"
                )
                
                order_batch.add_order(order)
                remaining_to_sell -= sell_amount
        
        logger.info(f"Generated {len(order_batch.orders)} withdrawal orders for ${withdrawal_amount} from account {account_id}")
        return order_batch
    
    @classmethod
    def load_model_portfolios_from_csv(cls, csv_path: str) -> 'OrderService':
        """Create OrderService by loading model portfolios from CSV.
        
        Args:
            csv_path: Path to MP_Master.csv file
            
        Returns:
            OrderService instance
        """
        manager = ModelPortfolioManager.load_from_csv(csv_path)
        return cls(manager)