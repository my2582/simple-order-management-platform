#!/usr/bin/env python3
"""
Debug script to understand why portfolio weights are all showing as 0.00%.
"""

import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def analyze_excel_data():
    """Analyze the generated Excel file to understand the issue."""
    
    try:
        # Find the latest portfolio positions file
        output_dir = Path("data/output")
        excel_files = list(output_dir.glob("portfolio_positions_*.xlsx"))
        
        if not excel_files:
            print("❌ No portfolio positions Excel files found")
            return
        
        # Get the latest file
        latest_file = max(excel_files, key=lambda x: x.stat().st_mtime)
        print(f"📁 Analyzing file: {latest_file}")
        
        # Check Portfolio_Matrix sheet data
        print("\n=== Portfolio_Matrix Sheet Analysis ===")
        
        try:
            df = pd.read_excel(latest_file, sheet_name='Portfolio_Matrix')
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            
            # Look for weight columns
            weight_cols = [col for col in df.columns if 'Weight' in col]
            print(f"Weight columns found: {weight_cols}")
            
            if weight_cols:
                print("\n--- Weight Column Values ---")
                for col in weight_cols:
                    values = df[col].dropna()
                    print(f"{col}: {values.tolist()}")
                    
            # Check raw data in the last few rows (actual account data)
            print("\n--- Last few rows (account data) ---")
            print(df.tail(10).to_string())
                    
        except Exception as e:
            print(f"Error reading Portfolio_Matrix: {e}")
            
        # Try Matrix sheet as well
        print("\n=== Matrix Sheet Analysis ===")
        
        try:
            df_matrix = pd.read_excel(latest_file, sheet_name='Matrix')
            print(f"Matrix shape: {df_matrix.shape}")
            print("Matrix data:")
            print(df_matrix.to_string())
            
        except Exception as e:
            print(f"Matrix sheet not found or error: {e}")
            
    except Exception as e:
        print(f"❌ Error analyzing Excel data: {e}")

def debug_portfolio_model():
    """Debug the portfolio model weight calculation logic."""
    
    print("\n=== Portfolio Model Debug ===")
    
    from simple_order_management_platform.models.portfolio import Position, AccountSummary, PortfolioSnapshot
    from decimal import Decimal
    
    # Create test position data
    positions = [
        Position(
            account_id="TEST123",
            symbol="VTI",
            contract_id=756733,
            exchange="ARCA", 
            currency="USD",
            sec_type="STK",
            position=Decimal("100"),  # Non-zero position
            market_price=Decimal("220.50"),
            market_value=Decimal("22050.00"),  # USD converted to SGD would be higher
            avg_cost=Decimal("215.00"),
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
            market_value=Decimal("2500.00"),
            avg_cost=Decimal("2.45"),
        ),
    ]
    
    # Create test account summary
    account_summary = AccountSummary(
        account_id="TEST123",
        currency="SGD",
        net_liquidation=Decimal("50000.00"),
        total_cash_value=Decimal("25450.00"),
        gross_position_value=Decimal("24550.00"),
    )
    
    # Create portfolio snapshot
    snapshot = PortfolioSnapshot(
        account_id="TEST123",
        positions=positions,
        account_summary=account_summary
    )
    
    print(f"Total portfolio value: {snapshot.get_total_portfolio_value()}")
    print(f"Position weights: {snapshot.get_position_weights()}")
    
    # Check positions summary
    positions_summary = snapshot.get_positions_summary()
    print(f"Positions in summary: {len(positions_summary['positions'])}")
    
    for pos in positions_summary['positions']:
        print(f"Position {pos['Symbol']}: Weight = {pos['Weight_Pct']}%, Position = {pos['Position']}, Market Value = {pos['Market_Value']}")

if __name__ == "__main__":
    print("🔍 Debugging Portfolio Weight Calculation Issues")
    
    # First analyze the Excel output
    analyze_excel_data()
    
    # Then debug the model logic
    debug_portfolio_model()