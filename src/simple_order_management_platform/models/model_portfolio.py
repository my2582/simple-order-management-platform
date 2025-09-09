"""Model Portfolio and Rebalancing data models."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class OrderType(str, Enum):
    """Order types supported by IBKR."""
    MARKET = "MKT"
    LIMIT = "LMT"
    MARKET_ON_CLOSE = "MOC"


class OrderAction(str, Enum):
    """Order actions."""
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    """Time in force options."""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class SecurityType(str, Enum):
    """Security types."""
    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    FOREX = "CASH"
    INDEX = "IND"


class ModelPortfolioHolding(BaseModel):
    """Individual holding in a model portfolio."""
    
    symbol: str
    target_weight: Decimal = Field(..., ge=0, le=1, description="Target weight as decimal (0.3333 = 33.33%)")
    security_type: SecurityType = SecurityType.STOCK
    exchange: str = "SMART"
    currency: str = "USD"
    
    class Config:
        use_enum_values = True
        
    @validator('target_weight')
    def validate_weight(cls, v):
        """Ensure weight is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Weight must be between 0 and 1")
        return v


class ModelPortfolio(BaseModel):
    """Model portfolio definition with target allocations."""
    
    name: str
    description: Optional[str] = None
    holdings: List[ModelPortfolioHolding]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
        
    @validator('holdings')
    def validate_weights_sum_to_one(cls, v):
        """Ensure all weights sum to approximately 1.0 (100%)."""
        total_weight = sum(holding.target_weight for holding in v)
        if abs(total_weight - Decimal('1.0')) > Decimal('0.0001'):  # Allow small rounding errors
            raise ValueError(f"Holdings weights must sum to 1.0, got {total_weight}")
        return v
    
    def get_holding(self, symbol: str) -> Optional[ModelPortfolioHolding]:
        """Get holding by symbol."""
        for holding in self.holdings:
            if holding.symbol == symbol:
                return holding
        return None
    
    def get_target_weights(self) -> Dict[str, Decimal]:
        """Get target weights as symbol -> weight mapping."""
        return {holding.symbol: holding.target_weight for holding in self.holdings}


class AccountModelPortfolioMapping(BaseModel):
    """Mapping between accounts and model portfolios."""
    
    account_id: str
    model_portfolio_name: str
    assigned_at: datetime = Field(default_factory=datetime.now)
    active: bool = True
    
    class Config:
        use_enum_values = True


class RebalanceOrder(BaseModel):
    """Individual rebalance order."""
    
    account_id: str
    symbol: str
    action: OrderAction
    quantity: Decimal
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Decimal] = None
    security_type: SecurityType = SecurityType.STOCK
    exchange: str = "SMART"
    currency: str = "USD"
    basket_tag: Optional[str] = None
    order_ref: Optional[str] = None
    use_price_mgmt_algo: bool = True
    
    # Rebalancing metadata
    current_weight: Optional[Decimal] = None
    target_weight: Optional[Decimal] = None
    rebalance_day: Literal[1, 2] = 1
    
    class Config:
        use_enum_values = True
    
    @validator('quantity')
    def validate_quantity(cls, v):
        """Ensure quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v
    
    def to_ibkr_csv_row(self) -> Dict[str, str]:
        """Convert to IBKR CSV format."""
        return {
            'Action': self.action.value,
            'Quantity': str(int(self.quantity) if self.quantity == int(self.quantity) else self.quantity),
            'Symbol': self.symbol,
            'SecType': self.security_type.value,
            'Exchange': self.exchange,
            'Currency': self.currency,
            'TimeInForce': self.time_in_force.value,
            'OrderType': self.order_type.value,
            'LmtPrice': str(self.limit_price) if self.limit_price else '',
            'BasketTag': self.basket_tag or '',
            'Account': self.account_id,
            'UsePriceMgmtAlgo': 'TRUE' if self.use_price_mgmt_algo else 'FALSE',
            'OrderRef': self.order_ref or ''
        }


class RebalancePlan(BaseModel):
    """Complete rebalancing plan for multiple accounts."""
    
    model_portfolio_name: str
    execution_date: datetime = Field(default_factory=datetime.now)
    day_1_orders: List[RebalanceOrder] = Field(default_factory=list)
    day_2_orders: List[RebalanceOrder] = Field(default_factory=list)
    basket_tag: Optional[str] = None
    
    class Config:
        use_enum_values = True
    
    def get_all_orders(self) -> List[RebalanceOrder]:
        """Get all orders (Day 1 + Day 2)."""
        return self.day_1_orders + self.day_2_orders
    
    def get_orders_by_account(self, account_id: str) -> List[RebalanceOrder]:
        """Get all orders for specific account."""
        return [order for order in self.get_all_orders() if order.account_id == account_id]
    
    def get_day_orders(self, day: Literal[1, 2]) -> List[RebalanceOrder]:
        """Get orders for specific day."""
        return self.day_1_orders if day == 1 else self.day_2_orders


class RebalanceCalculation(BaseModel):
    """Rebalancing calculation result for a single account."""
    
    account_id: str
    model_portfolio_name: str
    total_portfolio_value: Decimal
    current_positions: Dict[str, Decimal]  # symbol -> current shares
    current_weights: Dict[str, Decimal]    # symbol -> current weight
    target_weights: Dict[str, Decimal]     # symbol -> target weight
    weight_differences: Dict[str, Decimal] # symbol -> target - current
    orders_required: Dict[str, Decimal]    # symbol -> shares to buy/sell
    calculation_timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    def get_symbols_to_rebalance(self, threshold: Decimal = Decimal('0.01')) -> List[str]:
        """Get symbols that need rebalancing (weight diff > threshold)."""
        return [
            symbol for symbol, diff in self.weight_differences.items()
            if abs(diff) > threshold
        ]
    
    def needs_rebalancing(self, threshold: Decimal = Decimal('0.01')) -> bool:
        """Check if portfolio needs rebalancing."""
        return len(self.get_symbols_to_rebalance(threshold)) > 0