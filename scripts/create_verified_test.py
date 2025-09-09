#!/usr/bin/env python
"""Create test universe with verified IBKR symbols."""

import pandas as pd
from pathlib import Path

def main():
    # 새 전략 경로로 변경
    base_path = Path('data/raw/strategies/arki_macro_mini/v1.0/latest')
    base_path.mkdir(parents=True, exist_ok=True)
    
    verified_symbols = [
        {'Asset class': 'Commodity', 'Region': '', 'Instrument name': 'Crude Oil WTI', 'IBSymbol': 'CL', 'Exchange': 'NYMEX', 'Currency': 'USD', 'Type': 'Futures', 'Multiplier': 1000},
        {'Asset class': 'Commodity', 'Region': '', 'Instrument name': 'Gold', 'IBSymbol': 'GC', 'Exchange': 'COMEX', 'Currency': 'USD', 'Type': 'Futures', 'Multiplier': 100},
        {'Asset class': 'Commodity', 'Region': '', 'Instrument name': 'Natural Gas', 'IBSymbol': 'NG', 'Exchange': 'NYMEX', 'Currency': 'USD', 'Type': 'Futures', 'Multiplier': 10000},
    ]
    
    df = pd.DataFrame(verified_symbols)
    output_path = base_path / 'verified_test_universe.xlsx'
    df.to_excel(output_path, index=False)
    print(f"✓ Updated test universe: {output_path}")

if __name__ == "__main__":
    main()
