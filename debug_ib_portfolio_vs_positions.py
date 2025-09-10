#!/usr/bin/env python3
"""
Debug script to understand the difference between ib.portfolio() and ib.positions() methods
and fix the conversion logic.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def simulate_ib_position_vs_portfolio():
    """Simulate the differences between Position and PortfolioItem objects."""
    
    print("=== IB Position vs PortfolioItem Simulation ===")
    
    # This is what ib.positions() would return (Position object attributes)
    class MockIBPosition:
        def __init__(self):
            self.contract = MockContract()
            self.account = "U12803113"
            self.position = 100.0  # Shares
            self.avgCost = 220.50  # Average cost in local currency
            # Position objects don't have marketPrice or marketValue directly!
            
    # This is what ib.portfolio() would return (PortfolioItem object attributes)  
    class MockIBPortfolioItem:
        def __init__(self):
            self.contract = MockContract()
            self.account = "U12803113" 
            self.position = 100.0  # Shares
            self.averageCost = 220.50  # Average cost
            self.marketPrice = 225.30  # Current market price in base currency (SGD)
            self.marketValue = 32259.30  # Current market value in base currency (SGD)
            self.unrealizedPNL = 480.0
            self.realizedPNL = 0.0
            
    class MockContract:
        def __init__(self):
            self.symbol = "VTI"
            self.conId = 756733
            self.exchange = "ARCA"
            self.currency = "USD"
            self.secType = "STK"
            self.localSymbol = "VTI"
            self.multiplier = ""
            
    print("Position object (from ib.positions()):")
    pos = MockIBPosition()
    print(f"  position: {pos.position}")
    print(f"  avgCost: {pos.avgCost}")
    print(f"  marketPrice: {getattr(pos, 'marketPrice', 'NOT AVAILABLE')}")
    print(f"  marketValue: {getattr(pos, 'marketValue', 'NOT AVAILABLE')}")
    
    print("\nPortfolioItem object (from ib.portfolio()):")
    portfolio_item = MockIBPortfolioItem()
    print(f"  position: {portfolio_item.position}")
    print(f"  averageCost: {portfolio_item.averageCost}")
    print(f"  marketPrice: {portfolio_item.marketPrice}")
    print(f"  marketValue: {portfolio_item.marketValue}")
    
    # Now test our conversion functions
    print("\n=== Testing Conversion Functions ===")
    
    from simple_order_management_platform.services.portfolio_service import PortfolioService
    from simple_order_management_platform.providers.ib import IBProvider
    
    # We can't instantiate without real IB connection, so let's test the logic directly
    print("Conversion logic needs to be tested with actual PortfolioItem data...")
    
def analyze_conversion_issue():
    """Analyze why the conversion from PortfolioItem to Position might be failing."""
    
    print("\n=== Analyzing Conversion Issue ===")
    
    # The issue is likely in _convert_ib_portfolio_item_to_position method
    # Let's check what could cause market_value to be None or position to be 0
    
    print("Potential issues:")
    print("1. PortfolioItem.marketValue is None or 0")
    print("2. PortfolioItem.position is 0 (filtered out)")
    print("3. Currency conversion is not working")
    print("4. The attribute names are different (marketValue vs market_value)")
    
    # Let's check the actual PortfolioItem attributes from ib_insync
    try:
        from ib_insync import PortfolioItem
        
        print(f"\nPortfolioItem fields: {PortfolioItem._fields}")
        
        # Check if we're using the right attribute names
        print("Expected attributes:")
        print("  - contract")
        print("  - position") 
        print("  - marketPrice")
        print("  - marketValue")
        print("  - averageCost")
        print("  - unrealizedPNL")
        print("  - realizedPNL")
        print("  - account")
        
    except Exception as e:
        print(f"Could not import PortfolioItem: {e}")

def test_position_filtering():
    """Test if positions are being incorrectly filtered."""
    
    print("\n=== Testing Position Filtering Logic ===")
    
    from simple_order_management_platform.models.portfolio import Position, PortfolioSnapshot, AccountSummary
    
    # Create positions with various scenarios
    positions = [
        Position(
            account_id="TEST123",
            symbol="VTI", 
            contract_id=756733,
            exchange="ARCA",
            currency="USD",
            sec_type="STK",
            position=Decimal("100"),  # Non-zero position
            market_price=Decimal("225.30"),
            market_value=Decimal("32259.30"), # Should result in weight
            avg_cost=Decimal("220.50"),
        ),
        Position(
            account_id="TEST123",
            symbol="CASH",
            contract_id=0,
            exchange="",
            currency="SGD", 
            sec_type="CASH",
            position=Decimal("0"),  # Zero position - should be filtered
            market_price=None,
            market_value=None,
            avg_cost=None,
        ),
        Position(
            account_id="TEST123",
            symbol="SPMO",
            contract_id=12345,
            exchange="SGX",
            currency="SGD",
            sec_type="STK", 
            position=Decimal("1000"),  # Non-zero position
            market_price=Decimal("2.50"),
            market_value=None,  # None market value - should cause weight = 0
            avg_cost=Decimal("2.45"),
        ),
    ]
    
    account_summary = AccountSummary(
        account_id="TEST123",
        currency="SGD",
        net_liquidation=Decimal("50000.00"),
        total_cash_value=Decimal("17740.70"), 
        gross_position_value=Decimal("32259.30"),
    )
    
    snapshot = PortfolioSnapshot(
        account_id="TEST123",
        positions=positions,
        account_summary=account_summary
    )
    
    print(f"Total positions: {len(positions)}")
    print(f"Total portfolio value: {snapshot.get_total_portfolio_value()}")
    
    weights = snapshot.get_position_weights()
    print(f"Calculated weights: {weights}")
    
    positions_summary = snapshot.get_positions_summary()
    print(f"Positions in summary: {len(positions_summary['positions'])}")
    
    for pos in positions_summary['positions']:
        print(f"  {pos['Symbol']}: pos={pos['Position']}, mv={pos['Market_Value']}, weight={pos['Weight_Pct']}%")

if __name__ == "__main__":
    print("🔍 Debugging IB Portfolio vs Positions Conversion Issues\n")
    
    simulate_ib_position_vs_portfolio()
    analyze_conversion_issue() 
    test_position_filtering()