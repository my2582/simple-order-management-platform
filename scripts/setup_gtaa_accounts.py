#!/usr/bin/env python3
"""Setup script to assign accounts to GTAA model portfolio."""

import sys
import yaml
from pathlib import Path

def setup_gtaa_accounts(account_ids):
    """Add account IDs to GTAA model portfolio configuration."""
    
    # Path to config file
    config_path = Path(__file__).parent.parent / "src" / "simple_order_management_platform" / "config" / "model_portfolios.yaml"
    
    # Load existing config
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        return False
    
    # Update account mappings
    if 'account_mappings' not in config:
        config['account_mappings'] = {}
    
    for account_id in account_ids:
        config['account_mappings'][account_id] = 'GTAA'
        print(f"✅ Assigned account {account_id} to GTAA model portfolio")
    
    # Save updated config
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"\n🎉 Successfully updated configuration: {config_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_gtaa_accounts.py ACCOUNT_ID1 [ACCOUNT_ID2 ...]")
        print("Example: python setup_gtaa_accounts.py DU123456 DU789012")
        sys.exit(1)
    
    account_ids = sys.argv[1:]
    print(f"🔧 Setting up GTAA model portfolio for {len(account_ids)} accounts...")
    
    if setup_gtaa_accounts(account_ids):
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run: ./simple-order list-model-portfolios")
        print("2. Run: ./simple-order calculate-rebalancing")
        print("3. Run: ./simple-order generate-orders orders.csv")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)