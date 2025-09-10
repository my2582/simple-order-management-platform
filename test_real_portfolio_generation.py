#!/usr/bin/env python3
"""
Test script to generate a portfolio report with mock data to verify our changes work correctly.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_mock_multi_portfolio():
    """Create mock portfolio data that simulates real IB data."""
    
    from simple_order_management_platform.models.portfolio import Position, AccountSummary, PortfolioSnapshot, MultiAccountPortfolio
    
    # Create realistic positions for multiple accounts
    account_1_positions = [
        Position(
            account_id="U12803113",
            symbol="VTI",
            contract_id=756733,
            exchange="ARCA", 
            currency="USD",
            sec_type="STK",
            position=Decimal("100"),
            market_price=Decimal("225.30"),
            market_value=Decimal("32259.30"),  # USD converted to SGD
            avg_cost=Decimal("220.50"),
        ),
        Position(
            account_id="U12803113",
            symbol="SPMO",
            contract_id=12345,
            exchange="SGX",
            currency="SGD", 
            sec_type="STK",
            position=Decimal("1000"),
            market_price=Decimal("2.50"),
            market_value=Decimal("2500.00"),  # Already in SGD
            avg_cost=Decimal("2.45"),
        ),
    ]
    
    account_1_summary = AccountSummary(
        account_id="U12803113",
        currency="SGD",
        net_liquidation=Decimal("50000.00"),
        total_cash_value=Decimal("15240.70"),
        gross_position_value=Decimal("34759.30"),
    )
    
    account_2_positions = [
        Position(
            account_id="U13382000",
            symbol="IVV",
            contract_id=123456,
            exchange="ARCA",
            currency="USD", 
            sec_type="STK",
            position=Decimal("50"),
            market_price=Decimal("450.60"),
            market_value=Decimal("32271.60"),  # USD converted to SGD
            avg_cost=Decimal("440.00"),
        ),
    ]
    
    account_2_summary = AccountSummary(
        account_id="U13382000",
        currency="SGD",
        net_liquidation=Decimal("40000.00"),
        total_cash_value=Decimal("7728.40"),
        gross_position_value=Decimal("32271.60"),
    )
    
    # Create snapshots
    snapshots = [
        PortfolioSnapshot(
            account_id="U12803113",
            positions=account_1_positions,
            account_summary=account_1_summary
        ),
        PortfolioSnapshot(
            account_id="U13382000", 
            positions=account_2_positions,
            account_summary=account_2_summary
        ),
    ]
    
    return MultiAccountPortfolio(snapshots=snapshots)

def test_portfolio_generation():
    """Test portfolio report generation with mock data."""
    
    print("🧪 Testing Portfolio Report Generation with Mock Data")
    
    # Create mock portfolio
    multi_portfolio = create_mock_multi_portfolio()
    
    print(f"Created portfolio with {len(multi_portfolio.snapshots)} accounts")
    
    # Test each snapshot
    for snapshot in multi_portfolio.snapshots:
        print(f"\\nAccount {snapshot.account_id}:")
        print(f"  Total value: {snapshot.get_total_portfolio_value()}")
        print(f"  Positions: {len(snapshot.positions)}")
        
        weights = snapshot.get_position_weights()
        print(f"  Weights: {weights}")
        
        positions_summary = snapshot.get_positions_summary()
        print(f"  Summary positions: {len(positions_summary['positions'])}")
        
        for pos in positions_summary['positions']:
            print(f"    {pos['Symbol']}: {pos['Weight_Pct']:.2f}% (mv={pos['Market_Value']})")
    
    # Test Matrix generation
    print("\\n📊 Testing Matrix Sheet Generation")
    
    from simple_order_management_platform.utils.ibkr_exporters import IBKRStandardExporter
    
    exporter = IBKRStandardExporter()
    
    try:
        matrix_df = exporter._create_matrix_sheet(multi_portfolio)
        print(f"✅ Matrix sheet created: {matrix_df.shape}")
        
        # Check for weight data in the matrix
        print("\\nMatrix data preview:")
        print(matrix_df.to_string())
        
    except Exception as e:
        print(f"❌ Matrix generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Amt_Matrix generation
    print("\\n💰 Testing Amt_Matrix Sheet Generation")
    
    try:
        amt_matrix_df = exporter._create_amt_matrix_sheet(multi_portfolio)
        print(f"✅ Amt_Matrix sheet created: {amt_matrix_df.shape}")
        
        print("\\nAmt_Matrix data preview:")
        print(amt_matrix_df.to_string())
        
    except Exception as e:
        print(f"❌ Amt_Matrix generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_portfolio_generation()