"""Data export utilities for multi-asset results."""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

from ..config.loader import config_loader
from ..utils.exceptions import MarketDataPlatformError

logger = logging.getLogger(__name__)


def export_multi_asset_results(
    results_by_type: Dict[str, Dict[str, Tuple[bool, Optional[pd.DataFrame], Optional[str]]]],
    strategy_name: str,
    output_filename: Optional[str] = None,
    include_metadata: bool = True
) -> Path:
    """
    Export multi-asset download results to Excel file.
    
    Args:
        results_by_type: Dictionary mapping instrument_type -> symbol -> (success, dataframe, error)
        strategy_name: Name of the strategy for filename generation
        output_filename: Custom output filename (optional)
        include_metadata: Whether to include metadata sheets
        
    Returns:
        Path to the exported Excel file
    """
    
    if not results_by_type:
        raise MarketDataPlatformError("No results to export")
    
    # Generate output filename if not provided
    if output_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{strategy_name}_{timestamp}.xlsx"
    
    # Ensure .xlsx extension
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    
    # Get output directory
    app_config = config_loader.load_app_config()
    output_dir = Path(app_config.app.get("directories", {}).get("output_dir", "./data/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / output_filename
    
    logger.info(f"Exporting results to: {output_path}")
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Create summary sheet
        summary_df = _create_summary_sheet(results_by_type, strategy_name)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Create sheets for each successful instrument
        for instrument_type, results in results_by_type.items():
            for symbol, (success, df, error) in results.items():
                if success and df is not None:
                    sheet_name = _create_sheet_name(symbol, instrument_type)
                    
                    try:
                        # Add metadata if requested
                        start_row = 0
                        if include_metadata:
                            metadata_df = _create_instrument_metadata(symbol, df, instrument_type)
                            metadata_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
                            start_row = len(metadata_df) + 2
                        
                        # Add the actual data
                        df.to_excel(writer, sheet_name=sheet_name, startrow=start_row)
                        
                        logger.debug(f"Exported {symbol} to sheet '{sheet_name}'")
                        
                    except Exception as e:
                        logger.error(f"Failed to export {symbol} to Excel: {e}")
                        continue
    
    # Log export summary
    total_instruments = sum(len(results) for results in results_by_type.values())
    successful_instruments = sum(
        sum(1 for success, _, _ in results.values() if success)
        for results in results_by_type.values()
    )
    
    logger.info(f"Export completed: {successful_instruments}/{total_instruments} instruments exported to {output_path.name}")
    
    return output_path


def _create_summary_sheet(
    results_by_type: Dict[str, Dict[str, Tuple[bool, Optional[pd.DataFrame], Optional[str]]]],
    strategy_name: str
) -> pd.DataFrame:
    """Create summary sheet with overall statistics."""
    
    summary_data = []
    
    # Add header information
    summary_data.extend([
        ['Export Information', '', '', '', '', '', ''],
        ['Strategy Name', strategy_name, '', '', '', '', ''],
        ['Export Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '', '', '', '', ''],
        ['', '', '', '', '', '', ''],
        ['Detailed Results', '', '', '', '', '', ''],
        ['Instrument Type', 'Symbol', 'Status', 'Data Points', 'Start Date', 'End Date', 'Error Message']
    ])
    
    for instrument_type, results in results_by_type.items():
        for symbol, (success, df, error) in results.items():
            status = 'Success' if success else 'Failed'
            data_points = len(df) if success and df is not None else 0
            start_date = df.index.min().strftime('%Y-%m-%d') if success and df is not None and len(df) > 0 else ''
            end_date = df.index.max().strftime('%Y-%m-%d') if success and df is not None and len(df) > 0 else ''
            error_msg = error if error else ''
            
            summary_data.append([
                instrument_type.title(),
                symbol,
                status,
                data_points,
                start_date,
                end_date,
                error_msg[:100] + '...' if error_msg and len(error_msg) > 100 else error_msg
            ])
    
    return pd.DataFrame(summary_data)


def _create_instrument_metadata(
    symbol: str,
    df: pd.DataFrame,
    instrument_type: str
) -> pd.DataFrame:
    """Create metadata DataFrame for an instrument."""
    
    metadata = [
        ['Instrument Information', ''],
        ['Symbol', symbol],
        ['Instrument Type', instrument_type.title()],
        ['Data Points', len(df)],
        ['Date Range', f"{df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}"],
        ['Latest Close', f"{df['close'].iloc[-1]:.4f}" if 'close' in df.columns else 'N/A'],
        ['Export Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['', ''],
        ['Data Columns', ', '.join(df.columns.tolist())],
        ['', ''],
    ]
    
    return pd.DataFrame(metadata, columns=['Field', 'Value'])


def _create_sheet_name(symbol: str, instrument_type: str) -> str:
    """Create Excel sheet name with proper formatting and length limits."""
    
    # Create base name
    sheet_name = f"{symbol}_{instrument_type}"
    
    # Remove invalid characters for Excel sheet names
    invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
    for char in invalid_chars:
        sheet_name = sheet_name.replace(char, '_')
    
    # Limit to 31 characters (Excel limit)
    if len(sheet_name) > 31:
        # Keep symbol intact, truncate instrument_type if needed
        max_type_length = 31 - len(symbol) - 1  # -1 for underscore
        if max_type_length > 0:
            sheet_name = f"{symbol}_{instrument_type[:max_type_length]}"
        else:
            sheet_name = symbol[:31]
    
    return sheet_name
