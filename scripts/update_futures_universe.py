#!/usr/bin/env python
"""Update futures_universe.xlsx with correct IBKR mappings."""

import pandas as pd
from pathlib import Path
import shutil

def get_ibkr_corrections():
    """Return known corrections based on IBKR official mappings."""
    return {
        # Symbols that need correction
        'MCH': {
            'symbol': 'MCH.HK',  # Hong Kong requires .HK suffix
            'exchange': 'HKFE',
            'currency': 'HKD'
        },
        'FMEN': {
            'symbol': 'M1EF',    # IBKR uses M1EF for MSCI EM
            'exchange': 'EUREX',
            'currency': 'USD'
        }
    }

def update_universe_file():
    """Update futures_universe.xlsx with corrections."""
    
    universe_path = Path('data/raw/strategies/arki_global_multi_asset/v1.0/latest/futures_universe.xlsx')
    
    if not universe_path.exists():
        print(f"❌ Universe file not found: {universe_path}")
        return False
    
    # Create backup
    backup_path = universe_path.with_suffix('.backup.xlsx')
    shutil.copy2(universe_path, backup_path)
    print(f"✓ Backup created: {backup_path.name}")
    
    # Load and update
    df = pd.read_excel(universe_path)
    corrections = get_ibkr_corrections()
    updates_made = []
    
    for idx, row in df.iterrows():
        original_symbol = str(row['IBSymbol']).strip()
        
        if original_symbol in corrections:
            correction = corrections[original_symbol]
            changes = []
            
            # Apply symbol correction
            if correction['symbol'] != original_symbol:
                df.at[idx, 'IBSymbol'] = correction['symbol']
                changes.append(f"Symbol: {original_symbol} → {correction['symbol']}")
            
            # Apply exchange correction
            if str(row['Exchange']).strip() != correction['exchange']:
                df.at[idx, 'Exchange'] = correction['exchange']
                changes.append(f"Exchange: {row['Exchange']} → {correction['exchange']}")
            
            # Apply currency correction
            if str(row['Currency']).strip() != correction['currency']:
                df.at[idx, 'Currency'] = correction['currency']
                changes.append(f"Currency: {row['Currency']} → {correction['currency']}")
            
            if changes:
                updates_made.append(f"{original_symbol}: {', '.join(changes)}")
    
    # Save if updates were made
    if updates_made:
        df.to_excel(universe_path, index=False)
        print(f"✓ Applied {len(updates_made)} corrections:")
        for update in updates_made:
            print(f"  • {update}")
        return True
    else:
        print("✓ No corrections needed - file is already up to date")
        return False

def verify_corrections():
    """Verify the corrections were applied."""
    universe_path = Path('data/raw/strategies/arki_global_multi_asset/v1.0/latest/futures_universe.xlsx')
    df = pd.read_excel(universe_path)
    
    expected_symbols = ['MCH.HK', 'M1EF']
    print(f"\n🔍 Verification:")
    
    for symbol in expected_symbols:
        matches = df[df['IBSymbol'] == symbol]
        if len(matches) > 0:
            row = matches.iloc[0]
            print(f"  ✓ {symbol}: {row['Exchange']}, {row['Currency']}")
        else:
            print(f"  ❌ {symbol}: Not found")

if __name__ == "__main__":
    print("=== Futures Universe Update Tool ===\n")
    
    if update_universe_file():
        verify_corrections()
        print(f"\n🎯 Next Steps:")
        print(f"Run: market-data download arki_global_multi_asset --types futures --ib-client-id 2")
    
    print(f"\n✅ Update completed!")
