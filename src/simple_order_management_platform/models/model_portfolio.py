"""Model Portfolio data models."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import pandas as pd


class ModelPortfolioHolding(BaseModel):
    """Individual holding in a model portfolio."""
    
    portfolio_id: str
    bucket_name: str
    isin: Optional[str] = None
    ticker: Optional[str] = None
    weight: Decimal  # Weight as percentage (e.g., 33.33 for 33.33%)
    effective_date: str  # Date in string format as stored in CSV
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    @validator('weight', pre=True)
    def validate_weight(cls, v):
        """Ensure weight is a Decimal."""
        return Decimal(str(v))
    
    def get_normalized_weight(self) -> Decimal:
        """Get weight as decimal (e.g., 0.3333 for 33.33%)."""
        return self.weight / Decimal(100)
    
    def get_instrument_identifier(self) -> str:
        """Get the best available instrument identifier."""
        return self.ticker or self.isin or f"UNKNOWN_{self.portfolio_id}"


class ModelPortfolio(BaseModel):
    """Complete model portfolio definition."""
    
    portfolio_id: str
    bucket_name: str
    holdings: List[ModelPortfolioHolding] = Field(default_factory=list)
    effective_date: str
    total_weight: Optional[Decimal] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    def add_holding(self, holding: ModelPortfolioHolding) -> None:
        """Add a holding to the portfolio."""
        self.holdings.append(holding)
        self._recalculate_total_weight()
    
    def _recalculate_total_weight(self) -> None:
        """Recalculate total weight of all holdings."""
        self.total_weight = sum(holding.weight for holding in self.holdings)
    
    def get_holdings_summary(self) -> Dict[str, Any]:
        """Get holdings summary for display/export."""
        return {
            'portfolio_id': self.portfolio_id,
            'bucket_name': self.bucket_name,
            'effective_date': self.effective_date,
            'total_holdings': len(self.holdings),
            'total_weight': float(self.total_weight or 0),
            'holdings': [
                {
                    'instrument': holding.get_instrument_identifier(),
                    'ticker': holding.ticker,
                    'isin': holding.isin,
                    'weight_pct': float(holding.weight),
                    'weight_decimal': float(holding.get_normalized_weight()),
                }
                for holding in self.holdings
            ]
        }
    
    def is_weight_balanced(self, tolerance: Decimal = Decimal('0.01')) -> bool:
        """Check if portfolio weights sum to approximately 100%."""
        if not self.total_weight:
            self._recalculate_total_weight()
        
        target = Decimal(100)
        return abs(self.total_weight - target) <= tolerance
    
    def get_target_amounts(self, total_investment: Decimal) -> Dict[str, Decimal]:
        """Calculate target amounts for each holding given total investment amount."""
        target_amounts = {}
        
        for holding in self.holdings:
            identifier = holding.get_instrument_identifier()
            target_amount = total_investment * holding.get_normalized_weight()
            target_amounts[identifier] = target_amount
        
        return target_amounts


class ModelPortfolioManager(BaseModel):
    """Manager for multiple model portfolios."""
    
    portfolios: Dict[str, ModelPortfolio] = Field(default_factory=dict)
    last_updated: Optional[datetime] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True  # Updated for Pydantic v2
        use_enum_values = True
    
    def add_portfolio(self, portfolio: ModelPortfolio) -> None:
        """Add a model portfolio."""
        self.portfolios[portfolio.portfolio_id] = portfolio
        self.last_updated = datetime.now()
    
    def get_portfolio(self, portfolio_id: str) -> Optional[ModelPortfolio]:
        """Get a model portfolio by ID."""
        return self.portfolios.get(portfolio_id)
    
    def list_portfolio_ids(self) -> List[str]:
        """Get list of all portfolio IDs."""
        return list(self.portfolios.keys())
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of all portfolios."""
        return {
            'total_portfolios': len(self.portfolios),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'portfolios': {
                pid: portfolio.get_holdings_summary()
                for pid, portfolio in self.portfolios.items()
            }
        }
    
    @classmethod
    def load_from_csv(cls, csv_path: str) -> 'ModelPortfolioManager':
        """Load model portfolios from CSV file.
        
        Args:
            csv_path: Path to MP_Master.csv file
            
        Returns:
            ModelPortfolioManager instance with loaded portfolios
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['Portfolio ID', 'Bucket Name', 'Weight', 'Effective Date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Create manager instance
            manager = cls()
            
            # Group by Portfolio ID
            for portfolio_id, group in df.groupby('Portfolio ID'):
                # Get portfolio-level information from first row
                first_row = group.iloc[0]
                
                # Create model portfolio
                portfolio = ModelPortfolio(
                    portfolio_id=portfolio_id,
                    bucket_name=first_row['Bucket Name'],
                    effective_date=first_row['Effective Date']
                )
                
                # Add holdings
                for _, row in group.iterrows():
                    holding = ModelPortfolioHolding(
                        portfolio_id=portfolio_id,
                        bucket_name=row['Bucket Name'],
                        isin=row.get('ISIN') if pd.notna(row.get('ISIN')) else None,
                        ticker=row.get('Ticker') if pd.notna(row.get('Ticker')) else None,
                        weight=Decimal(str(row['Weight'])),
                        effective_date=row['Effective Date']
                    )
                    portfolio.add_holding(holding)
                
                # Add portfolio to manager
                manager.add_portfolio(portfolio)
            
            return manager
            
        except Exception as e:
            raise ValueError(f"Failed to load model portfolios from CSV: {e}")
    
    def save_to_csv(self, csv_path: str) -> None:
        """Save model portfolios to CSV file.
        
        Args:
            csv_path: Path where to save MP_Master.csv file
        """
        try:
            # Prepare data for CSV
            rows = []
            for portfolio in self.portfolios.values():
                for holding in portfolio.holdings:
                    rows.append({
                        'Portfolio ID': holding.portfolio_id,
                        'Bucket Name': holding.bucket_name,
                        'ISIN': holding.isin or '',
                        'Ticker': holding.ticker or '',
                        'Weight': float(holding.weight),
                        'Effective Date': holding.effective_date
                    })
            
            # Create DataFrame and save
            df = pd.DataFrame(rows)
            df.to_csv(csv_path, index=False)
            
        except Exception as e:
            raise ValueError(f"Failed to save model portfolios to CSV: {e}")


# Utility functions for working with model portfolios

def get_gtaa_portfolio(manager: ModelPortfolioManager) -> Optional[ModelPortfolio]:
    """Get the GTAA portfolio (B301) from manager."""
    return manager.get_portfolio('B301')


def calculate_rebalancing_orders(
    model_portfolio: ModelPortfolio,
    current_positions: Dict[str, Decimal],  # instrument_id -> current_market_value
    target_amount: Decimal,
    min_trade_amount: Decimal = Decimal('100')
) -> Dict[str, Decimal]:
    """Calculate rebalancing orders needed to match model portfolio.
    
    Args:
        model_portfolio: Target model portfolio
        current_positions: Current positions {instrument_id: market_value}
        target_amount: Total target investment amount
        min_trade_amount: Minimum trade amount to execute
        
    Returns:
        Dictionary of {instrument_id: trade_amount} where positive = buy, negative = sell
    """
    # Calculate target amounts for each instrument
    target_amounts = model_portfolio.get_target_amounts(target_amount)
    
    # Calculate required trades
    trades = {}
    
    for instrument_id, target_value in target_amounts.items():
        current_value = current_positions.get(instrument_id, Decimal(0))
        trade_amount = target_value - current_value
        
        # Only include trades above minimum threshold
        if abs(trade_amount) >= min_trade_amount:
            trades[instrument_id] = trade_amount
    
    # Handle positions not in model portfolio (should be sold)
    for instrument_id, current_value in current_positions.items():
        if instrument_id not in target_amounts and current_value != 0:
            trades[instrument_id] = -current_value  # Sell entire position
    
    return trades