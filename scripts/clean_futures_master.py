#!/usr/bin/env python
"""Clean futures master universe to remove non-futures instruments."""

import pandas as pd
from pathlib import Path

def clean_futures_master():
    """Remove non-futures instruments from futures master universe."""
    
    master_path = Path("config/universes/futures_master_universe.xlsx")
    
    if not master_path.exists():
        print(f"❌ Master universe file not found: {master_path}")
        return False
    
    # Load and backup
    df = pd.read_excel(master_path)
    backup_path = master_path.with_suffix('.backup.xlsx')
    df.to_excel(backup_path, index=False)
    print(f"✓ Backup created: {backup_path}")
    
    original_count = len(df)
    print(f"Original universe size: {original_count} instruments")
    
    # Filter to futures only
    if 'Type' in df.columns:
        df_futures = df[df['Type'].astype(str).str.contains('Futures', case=False, na=False)].copy()
    else:
        # If no Type column, filter by known stock/ETF exchanges
        stock_exchanges = ['US', 'ARCA', 'NASDAQ', 'NYSE', 'TSE', 'LSE', 'XETR']
        df_futures = df[~df['Exchange'].astype(str).str.upper().isin(stock_exchanges)].copy()
    
    # Additional cleanup: remove obvious ETF symbols
    etf_symbols = ['IVV', 'IEF', 'IEUR', 'EWG', 'DXJ', 'EWU', 'IAU', 'IBGM', 'IGLT']
    df_futures = df_futures[~df_futures['IBSymbol'].isin(etf_symbols)].copy()
    
    removed_count = original_count - len(df_futures)
    print(f"Removed {removed_count} non-futures instruments")
    print(f"Remaining futures: {len(df_futures)} instruments")
    
    # Show what was removed
    if removed_count > 0:
        removed_symbols = set(df['IBSymbol']) - set(df_futures['IBSymbol'])
        print(f"Removed symbols: {', '.join(list(removed_symbols)[:10])}")
        if len(removed_symbols) > 10:
            print(f"... and {len(removed_symbols) - 10} more")
    
    # Save cleaned version
    df_futures.to_excel(master_path, index=False)
    print(f"✓ Cleaned master universe saved: {master_path}")
    
    return True

if __name__ == "__main__":
    print("=== Futures Master Universe Cleanup ===\n")
    clean_futures_master()
    print("\n✅ Cleanup completed!")
