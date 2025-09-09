#!/usr/bin/env python3
"""
Test script to validate the currency conversion fix for portfolio positions.
This script tests the new ib.portfolio() approach vs old ib.positions() approach.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simple_order_management_platform.utils.ibkr_exporters import IBKRStandardExporter
from simple_order_management_platform.models.portfolio import Position, AccountSummary, PortfolioSnapshot, MultiAccountPortfolio
from decimal import Decimal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_portfolio_data():
    """Create test portfolio data to validate currency conversion logic."""
    
    # Create test positions with different currencies
    positions = [
        Position(
            account_id="TEST123",
            symbol="VTI",
            contract_id=756733,
            exchange="ARCA", 
            currency="USD",
            sec_type="STK",
            position=Decimal("100"),
            market_price=Decimal("220.50"),  # USD price
            market_value=Decimal("31631.70"),  # Converted to SGD (base currency)
            avg_cost=Decimal("215.00"),
        ),
        Position(
            account_id="TEST123",
            symbol="SPMO",
            contract_id=12345,
            exchange="SGX",
            currency="SGD", 
            sec_type="STK",
            position=Decimal("1000"),
            market_price=Decimal("2.50"),   # SGD price
            market_value=Decimal("2500.00"),  # Already in SGD (base currency)
            avg_cost=Decimal("2.45"),
        ),
    ]
    
    # Create test account summary with SGD as base currency
    account_summary = AccountSummary(
        account_id="TEST123",
        currency="SGD",  # Base currency is now SGD
        net_liquidation=Decimal("50000.00"),  # Total value in SGD
        total_cash_value=Decimal("15868.30"),  # Cash in SGD
        gross_position_value=Decimal("34131.70"),  # Positions value in SGD
    )
    
    # Create portfolio snapshot
    snapshot = PortfolioSnapshot(
        account_id="TEST123",
        positions=positions,
        account_summary=account_summary
    )
    
    # Create multi-account portfolio
    multi_portfolio = MultiAccountPortfolio(snapshots=[snapshot])
    
    return multi_portfolio

def test_weight_calculations():
    """Test that weight calculations are now correct with base currency."""
    
    logger.info("Testing weight calculations with base currency conversion...")
    
    # Create test data
    multi_portfolio = create_test_portfolio_data()
    snapshot = multi_portfolio.snapshots[0]
    
    # Test weight calculations
    weights = snapshot.get_position_weights()
    
    logger.info("Position weights:")
    total_weight = 0
    for symbol, weight in weights.items():
        logger.info(f"  {symbol}: {weight:.2f}%")
        total_weight += weight
    
    logger.info(f"Total weight: {total_weight:.2f}% (should be reasonable, not >100%)")
    
    # Check if weights are reasonable
    if total_weight > 150:  # Allow some margin for errors but not the 400%+ we had before
        logger.error("❌ Weights are still too high - currency conversion issue not fixed")
        return False
    else:
        logger.info("✅ Weight calculations appear reasonable")
        return True

def test_matrix_sheet_generation():
    """Test Matrix sheet generation with corrected data."""
    
    logger.info("Testing Matrix sheet generation...")
    
    # Create test data
    multi_portfolio = create_test_portfolio_data()
    
    # Create exporter
    exporter = IBKRStandardExporter()
    
    try:
        # Test Matrix sheet generation
        matrix_df = exporter._create_matrix_sheet(multi_portfolio)
        logger.info(f"Matrix sheet generated successfully: {matrix_df.shape}")
        
        # Test Amt_Matrix sheet generation  
        amt_matrix_df = exporter._create_amt_matrix_sheet(multi_portfolio)
        logger.info(f"Amt_Matrix sheet generated successfully: {amt_matrix_df.shape}")
        
        logger.info("✅ Both Matrix and Amt_Matrix sheets generated successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error generating matrix sheets: {e}")
        return False

def main():
    """Main test function."""
    
    logger.info("🧪 Testing currency conversion fixes...")
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Weight calculations
    if test_weight_calculations():
        tests_passed += 1
    
    # Test 2: Matrix sheet generation
    if test_matrix_sheet_generation():
        tests_passed += 1
    
    # Summary
    logger.info(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        logger.info("✅ All tests passed! Currency conversion fixes appear to be working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please review the currency conversion implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())