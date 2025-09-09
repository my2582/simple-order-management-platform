"""Model Portfolio Service for managing model portfolios and rebalancing."""

import logging
import yaml
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.model_portfolio import (
    ModelPortfolio, ModelPortfolioHolding, AccountModelPortfolioMapping,
    RebalanceOrder, RebalancePlan, RebalanceCalculation, OrderAction, OrderType
)
from ..models.portfolio import PortfolioSnapshot, MultiAccountPortfolio
from ..utils.exceptions import SimpleOrderManagementPlatformError

logger = logging.getLogger(__name__)


class ModelPortfolioService:
    """Service for managing model portfolios and generating rebalancing orders."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize model portfolio service.
        
        Args:
            config_path: Path to model portfolio configuration file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "model_portfolios.yaml"
        
        self.config_path = Path(config_path)
        self._model_portfolios: Dict[str, ModelPortfolio] = {}
        self._account_mappings: Dict[str, str] = {}
        self._settings: Dict = {}
        
        self._load_configuration()
    
    def _load_configuration(self):
        """Load model portfolio configuration from YAML file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Configuration file not found: {self.config_path}")
                return
                
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load model portfolios
            for name, mp_config in config.get('model_portfolios', {}).items():
                holdings = []
                for holding_config in mp_config.get('holdings', []):
                    holding = ModelPortfolioHolding(
                        symbol=holding_config['symbol'],
                        target_weight=Decimal(str(holding_config['target_weight'])),
                        security_type=holding_config.get('security_type', 'STK'),
                        exchange=holding_config.get('exchange', 'SMART'),
                        currency=holding_config.get('currency', 'USD')
                    )
                    holdings.append(holding)
                
                model_portfolio = ModelPortfolio(
                    name=name,
                    description=mp_config.get('description'),
                    holdings=holdings
                )
                self._model_portfolios[name] = model_portfolio
                logger.info(f"Loaded model portfolio: {name}")
            
            # Load account mappings
            self._account_mappings = config.get('account_mappings', {}) or {}
            
            # Load rebalancing settings
            self._settings = config.get('rebalancing_settings', {}) or {}
            
            logger.info(f"Loaded {len(self._model_portfolios)} model portfolios and "
                       f"{len(self._account_mappings)} account mappings")
            
        except Exception as e:
            logger.error(f"Error loading model portfolio configuration: {e}")
            raise SimpleOrderManagementPlatformError(f"Failed to load configuration: {e}")
    
    def get_model_portfolio(self, name: str) -> Optional[ModelPortfolio]:
        """Get model portfolio by name."""
        return self._model_portfolios.get(name)
    
    def list_model_portfolios(self) -> List[str]:
        """Get list of available model portfolio names."""
        return list(self._model_portfolios.keys())
    
    def get_account_model_portfolio(self, account_id: str) -> Optional[str]:
        """Get model portfolio name for account."""
        return self._account_mappings.get(account_id)
    
    def assign_account_to_model_portfolio(self, account_id: str, model_portfolio_name: str):
        """Assign account to model portfolio."""
        if model_portfolio_name not in self._model_portfolios:
            raise SimpleOrderManagementPlatformError(f"Model portfolio not found: {model_portfolio_name}")
        
        self._account_mappings[account_id] = model_portfolio_name
        logger.info(f"Assigned account {account_id} to model portfolio {model_portfolio_name}")
    
    def calculate_rebalancing(
        self,
        portfolio_snapshot: PortfolioSnapshot,
        model_portfolio_name: Optional[str] = None
    ) -> RebalanceCalculation:
        """Calculate rebalancing requirements for a portfolio.
        
        Args:
            portfolio_snapshot: Current portfolio snapshot
            model_portfolio_name: Model portfolio name (auto-detect if None)
            
        Returns:
            RebalanceCalculation with required trades
        """
        account_id = portfolio_snapshot.account_id
        
        # Get model portfolio
        if model_portfolio_name is None:
            model_portfolio_name = self.get_account_model_portfolio(account_id)
            if not model_portfolio_name:
                raise SimpleOrderManagementPlatformError(
                    f"No model portfolio assigned to account {account_id}"
                )
        
        model_portfolio = self.get_model_portfolio(model_portfolio_name)
        if not model_portfolio:
            raise SimpleOrderManagementPlatformError(
                f"Model portfolio not found: {model_portfolio_name}"
            )
        
        # Get current positions and portfolio value
        total_value = portfolio_snapshot.get_total_portfolio_value()
        if not total_value or total_value <= 0:
            raise SimpleOrderManagementPlatformError(
                f"Invalid portfolio value: {total_value}"
            )
        
        # Calculate current positions and weights
        current_positions = {}
        current_weights = {}
        
        for position in portfolio_snapshot.positions:
            if position.position != 0:  # Only non-zero positions
                current_positions[position.symbol] = position.position
                
                if position.market_value:
                    current_weight = position.market_value / total_value
                    current_weights[position.symbol] = current_weight
                else:
                    current_weights[position.symbol] = Decimal('0')
        
        # Get target weights
        target_weights = model_portfolio.get_target_weights()
        
        # Calculate weight differences and required orders
        weight_differences = {}
        orders_required = {}
        
        # Get current market prices for calculations
        position_prices = {
            pos.symbol: pos.market_price for pos in portfolio_snapshot.positions
            if pos.market_price and pos.market_price > 0
        }
        
        for symbol, target_weight in target_weights.items():
            current_weight = current_weights.get(symbol, Decimal('0'))
            weight_diff = target_weight - current_weight
            weight_differences[symbol] = weight_diff
            
            # Calculate required shares
            if symbol in position_prices and position_prices[symbol] > 0:
                target_value = total_value * target_weight
                current_shares = current_positions.get(symbol, Decimal('0'))
                target_shares = target_value / position_prices[symbol]
                shares_diff = target_shares - current_shares
                orders_required[symbol] = shares_diff
            else:
                logger.warning(f"No market price available for {symbol}, cannot calculate order")
                orders_required[symbol] = Decimal('0')
        
        return RebalanceCalculation(
            account_id=account_id,
            model_portfolio_name=model_portfolio_name,
            total_portfolio_value=total_value,
            current_positions=current_positions,
            current_weights=current_weights,
            target_weights=target_weights,
            weight_differences=weight_differences,
            orders_required=orders_required
        )
    
    def generate_rebalance_plan(
        self,
        rebalance_calculations: List[RebalanceCalculation],
        execution_date: Optional[datetime] = None
    ) -> RebalancePlan:
        """Generate complete rebalancing plan with Day 1 and Day 2 orders.
        
        Args:
            rebalance_calculations: List of rebalance calculations for accounts
            execution_date: Execution date (default: today)
            
        Returns:
            RebalancePlan with Day 1 and Day 2 orders
        """
        if not rebalance_calculations:
            raise SimpleOrderManagementPlatformError("No rebalance calculations provided")
        
        execution_date = execution_date or datetime.now()
        model_portfolio_name = rebalance_calculations[0].model_portfolio_name
        
        # Generate basket tag
        date_str = execution_date.strftime('%Y%m%d')
        basket_tag = f"EX_{date_str}_1"
        
        day_1_orders = []
        day_2_orders = []
        
        # Get rebalancing settings
        min_weight_threshold = Decimal(str(self._settings.get('day_1_min_weight_threshold', 0.05)))
        
        for calc in rebalance_calculations:
            account_id = calc.account_id
            
            # Find symbols that need rebalancing
            symbols_to_rebalance = calc.get_symbols_to_rebalance()
            
            # Separate symbols by target weight for Day 1/Day 2 logic
            high_weight_symbols = [
                symbol for symbol in symbols_to_rebalance
                if calc.target_weights[symbol] >= min_weight_threshold
            ]
            
            # Day 1: High weight symbols except the smallest one (if > 1 symbol)
            day_1_symbols = high_weight_symbols.copy()
            if len(high_weight_symbols) > 1:
                # Remove symbol with smallest target weight
                smallest_symbol = min(high_weight_symbols, key=lambda s: calc.target_weights[s])
                day_1_symbols.remove(smallest_symbol)
            
            # Generate Day 1 orders (MoC, integer quantities)
            for symbol in day_1_symbols:
                shares_needed = calc.orders_required[symbol]
                if abs(shares_needed) >= 1:  # Only if at least 1 share needed
                    integer_shares = int(shares_needed)  # Round down to integer
                    if integer_shares != 0:
                        order = RebalanceOrder(
                            account_id=account_id,
                            symbol=symbol,
                            action=OrderAction.BUY if integer_shares > 0 else OrderAction.SELL,
                            quantity=abs(Decimal(integer_shares)),
                            order_type=OrderType.MARKET_ON_CLOSE,
                            basket_tag=basket_tag,
                            current_weight=calc.current_weights.get(symbol, Decimal('0')),
                            target_weight=calc.target_weights[symbol],
                            rebalance_day=1
                        )
                        day_1_orders.append(order)
            
            # Day 2: All remaining adjustments (LIMIT orders with fractional shares)
            for symbol in symbols_to_rebalance:
                shares_needed = calc.orders_required[symbol]
                
                # Subtract Day 1 orders from total needed
                day_1_executed = Decimal('0')
                for day_1_order in day_1_orders:
                    if day_1_order.account_id == account_id and day_1_order.symbol == symbol:
                        executed_shares = day_1_order.quantity
                        if day_1_order.action == OrderAction.SELL:
                            executed_shares = -executed_shares
                        day_1_executed += executed_shares
                
                remaining_shares = shares_needed - day_1_executed
                
                if abs(remaining_shares) >= Decimal('0.001'):  # Minimum fractional threshold
                    # For Day 2, we'll use a limit price (to be set later with market data)
                    order = RebalanceOrder(
                        account_id=account_id,
                        symbol=symbol,
                        action=OrderAction.BUY if remaining_shares > 0 else OrderAction.SELL,
                        quantity=abs(remaining_shares),
                        order_type=OrderType.LIMIT,
                        basket_tag=basket_tag,
                        current_weight=calc.current_weights.get(symbol, Decimal('0')),
                        target_weight=calc.target_weights[symbol],
                        rebalance_day=2
                    )
                    day_2_orders.append(order)
        
        return RebalancePlan(
            model_portfolio_name=model_portfolio_name,
            execution_date=execution_date,
            day_1_orders=day_1_orders,
            day_2_orders=day_2_orders,
            basket_tag=basket_tag
        )
    
    def export_orders_to_ibkr_csv(
        self,
        rebalance_plan: RebalancePlan,
        output_file: str,
        day: Optional[int] = None
    ):
        """Export rebalancing orders to IBKR CSV format.
        
        Args:
            rebalance_plan: Rebalancing plan
            output_file: Output CSV file path
            day: Specific day to export (1 or 2), or None for all days
        """
        import csv
        
        orders_to_export = []
        if day == 1:
            orders_to_export = rebalance_plan.day_1_orders
        elif day == 2:
            orders_to_export = rebalance_plan.day_2_orders
        else:
            orders_to_export = rebalance_plan.get_all_orders()
        
        if not orders_to_export:
            logger.warning("No orders to export")
            return
        
        # IBKR CSV headers
        headers = [
            'Action', 'Quantity', 'Symbol', 'SecType', 'Exchange', 'Currency',
            'TimeInForce', 'OrderType', 'LmtPrice', 'BasketTag', 'Account',
            'UsePriceMgmtAlgo', 'OrderRef'
        ]
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for order in orders_to_export:
                row = order.to_ibkr_csv_row()
                writer.writerow(row)
        
        logger.info(f"Exported {len(orders_to_export)} orders to {output_file}")
    
    def calculate_multi_account_rebalancing(
        self,
        multi_portfolio: MultiAccountPortfolio,
        model_portfolio_name: Optional[str] = None
    ) -> List[RebalanceCalculation]:
        """Calculate rebalancing for multiple accounts.
        
        Args:
            multi_portfolio: Multi-account portfolio data
            model_portfolio_name: Model portfolio name (auto-detect per account if None)
            
        Returns:
            List of rebalance calculations for each account
        """
        calculations = []
        
        for snapshot in multi_portfolio.snapshots:
            try:
                calc = self.calculate_rebalancing(snapshot, model_portfolio_name)
                calculations.append(calc)
            except Exception as e:
                logger.error(f"Failed to calculate rebalancing for account {snapshot.account_id}: {e}")
                continue
        
        return calculations