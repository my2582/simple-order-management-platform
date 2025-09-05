#!/usr/bin/env python
"""Basic test script to verify installation."""

def test_imports():
    """Test if all modules can be imported."""
    try:
        print("Testing basic imports...")
        
        import pandas as pd
        import yaml
        from pathlib import Path
        print("✓ Basic packages imported")
        
        import ib_insync
        print("✓ ib_insync imported")
        
        from market_data_platform.utils.exceptions import MarketDataPlatformError
        print("✓ Custom exceptions imported")
        
        from market_data_platform.models.base import BaseInstrument, InstrumentType
        print("✓ Base models imported")
        
        from market_data_platform.models.futures import FuturesContract
        print("✓ Futures models imported")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_files():
    """Test configuration files."""
    try:
        print("\nTesting configuration files...")
        
        import yaml
        from pathlib import Path
        
        # Test app config
        app_config_path = Path('config/app.yaml')
        with open(app_config_path, 'r') as f:
            app_config = yaml.safe_load(f)
        print("✓ app.yaml loaded")
        
        # Test strategies config  
        strategies_config_path = Path('config/strategies.yaml')
        with open(strategies_config_path, 'r') as f:
            strategies_config = yaml.safe_load(f)
        print("✓ strategies.yaml loaded")
        
        print("✓ All config files loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Config loading error: {e}")
        return False

def test_universe_file():
    """Test universe file."""
    try:
        print("\nTesting universe file...")
        
        import pandas as pd
        from pathlib import Path
        
        universe_path = Path('data/raw/strategies/arki_global_multi_asset/v1.0/latest/futures_universe.xlsx')
        
        if not universe_path.exists():
            print(f"❌ Universe file not found: {universe_path}")
            return False
        
        df = pd.read_excel(universe_path)
        print(f"✓ Universe file loaded: {len(df)} instruments")
        print(f"  Symbols: {list(df['IBSymbol'][:5])}{'...' if len(df) > 5 else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ Universe file error: {e}")
        return False

if __name__ == "__main__":
    print("=== Market Data Platform Basic Test ===\n")
    
    success = True
    success &= test_imports()
    success &= test_config_files() 
    success &= test_universe_file()
    
    if success:
        print("\n🎉 All basic tests passed!")
        print("\nNext steps:")
        print("1. Start IB TWS or Gateway")
        print("2. Run: market-data test-connection")
        print("3. Try: market-data download arki_global_multi_asset --types futures --test")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
