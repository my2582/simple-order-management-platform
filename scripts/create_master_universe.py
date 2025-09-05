#!/usr/bin/env python
"""Create master universe from current arki_macro_mini data."""

import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime

def create_master_universes():
    """Create master universe files from current strategy data."""
    
    # 디렉토리 구조 생성
    master_dir = Path('config/universes')
    master_dir.mkdir(parents=True, exist_ok=True)
    
    data_master_dir = Path('data/master')
    data_master_dir.mkdir(parents=True, exist_ok=True)
    
    # 현재 futures_universe를 마스터로 복사
    source = Path('data/raw/strategies/arki_macro_mini/v1.0/latest/futures_universe.xlsx')
    target = master_dir / 'futures_master_universe.xlsx'
    
    if source.exists():
        # 메타데이터 추가
        df = pd.read_excel(source)
        df['created_from'] = 'arki_macro_mini'
        df['created_date'] = datetime.now().strftime('%Y-%m-%d')
        df['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        df['used_by_strategies'] = 'arki_macro_mini'  # 추후 확장
        df['data_status'] = 'verified'
        
        df.to_excel(target, index=False)
        print(f"✓ Master futures universe created: {target}")
        print(f"  Total symbols: {len(df)}")
        
        # 자산군별 요약
        if 'Asset class' in df.columns:
            summary = df['Asset class'].value_counts()
            for asset_class, count in summary.items():
                print(f"  {asset_class}: {count} symbols")
        
        return target
    else:
        print(f"❌ Source file not found: {source}")
        return None

def create_master_config():
    """Create master configuration file."""
    
    config_content = """
# Master Universe Configuration
master_universes:
  futures:
    file_path: "./config/universes/futures_master_universe.xlsx"
    update_frequency: "daily"
    last_updated: null
    
  stocks:
    file_path: "./config/universes/stocks_master_universe.xlsx" 
    update_frequency: "daily"
    last_updated: null
    
  etfs:
    file_path: "./config/universes/etfs_master_universe.xlsx"
    update_frequency: "daily" 
    last_updated: null

# Centralized data storage
raw_data_storage:
  base_path: "./data/master"
  file_format: "parquet"  # parquet, excel, csv
  compression: "snappy"
  retention_days: 730
  
# Strategy data views  
strategy_views:
  base_path: "./data/strategies"
  export_formats: ["parquet", "excel"]
  auto_sync: true
"""
    
    config_path = Path('config/master_config.yaml')
    with open(config_path, 'w') as f:
        f.write(config_content.strip())
    
    print(f"✓ Master configuration created: {config_path}")
    return config_path

if __name__ == "__main__":
    print("=== Master Universe Creation ===\n")
    
    master_file = create_master_universes()
    config_file = create_master_config()
    
    if master_file:
        print(f"\n🎯 Next Steps:")
        print(f"1. Review master universe: {master_file}")
        print(f"2. Run: market-data update-master --types futures")
        print(f"3. Run: market-data build-strategy arki_macro_mini")
    
    print(f"\n✅ Master universe setup completed!")
