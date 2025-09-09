#!/usr/bin/env python
"""Update arki_macro_mini strategy with symbol/currency corrections."""

import pandas as pd
from pathlib import Path
import shutil

def get_corrections():
    """Return corrections for arki_macro_mini strategy."""
    return {
        'MCH': {
            'symbol': 'MCH.HK',
            'exchange': 'HKFE',
            'currency': 'HKD'
        },
        'FMEN': {
            'symbol': 'M1EF',
            'exchange': 'EUREX',
            'currency': 'USD'  # EUR에서 USD로 변경 (핵심!)
        }
    }

def update_futures_universe():
    """Update futures_universe.xlsx with corrections."""
    
    universe_path = Path('data/raw/strategies/arki_macro_mini/v1.0/latest/futures_universe.xlsx')
    
    if not universe_path.exists():
        print(f"❌ Universe file not found: {universe_path}")
        return False
    
    # Create backup
    backup_path = universe_path.with_suffix('.backup.xlsx')
    shutil.copy2(universe_path, backup_path)
    print(f"✓ Backup created: {backup_path.name}")
    
    # Load and update
    df = pd.read_excel(universe_path)
    corrections = get_corrections()
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
    universe_path = Path('data/raw/strategies/arki_macro_mini/v1.0/latest/futures_universe.xlsx')
    df = pd.read_excel(universe_path)
    
    expected_updates = [
        ('MCH.HK', 'HKFE', 'HKD'),
        ('M1EF', 'EUREX', 'USD')  # USD 통화 확인
    ]
    
    print(f"\n🔍 Verification:")
    
    for symbol, exchange, currency in expected_updates:
        matches = df[df['IBSymbol'] == symbol]
        if len(matches) > 0:
            row = matches.iloc[0]
            actual_exchange = str(row['Exchange']).strip()
            actual_currency = str(row['Currency']).strip()
            
            if actual_exchange == exchange and actual_currency == currency:
                print(f"  ✓ {symbol}: {exchange}, {currency}")
            else:
                print(f"  ⚠️ {symbol}: Expected {exchange}/{currency}, Got {actual_exchange}/{actual_currency}")
        else:
            print(f"  ❌ {symbol}: Not found")

if __name__ == "__main__":
    print("=== Arki Macro Mini Strategy Update ===\n")
    
    if update_futures_universe():
        verify_corrections()
        print(f"\n🎯 Next Steps:")
        print(f"1. Run: market-data list-strategies")
        print(f"2. Run: market-data download arki_macro_mini --types futures --ib-client-id 2")
    
    print(f"\n✅ Update completed!")
