"""Data export utilities for multi-asset results."""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
import logging

from ..config.loader import config_loader
from ..utils.exceptions import SimpleOrderManagementPlatformError

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
        raise SimpleOrderManagementPlatformError("No results to export")
    
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


def export_portfolio_snapshots(
    multi_portfolio: 'MultiAccountPortfolio',
    output_filename: Optional[str] = None,
    include_summary: bool = True
) -> Path:
    """
    Export portfolio snapshots to Excel file with unified position matrix.
    
    Args:
        multi_portfolio: MultiAccountPortfolio object with snapshots
        output_filename: Custom output filename (optional)
        include_summary: Whether to include summary sheet
        
    Returns:
        Path to the exported Excel file
    """
    from ..models.portfolio import MultiAccountPortfolio
    
    if not multi_portfolio.snapshots:
        raise SimpleOrderManagementPlatformError("No portfolio snapshots to export")
    
    # Generate output filename if not provided
    if output_filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"portfolio_positions_{timestamp}.xlsx"
    
    # Ensure .xlsx extension
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    
    # Get output directory
    app_config = config_loader.load_app_config()
    output_dir = Path(app_config.app.get("directories", {}).get("output_dir", "./data/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / output_filename
    
    logger.info(f"Exporting portfolio snapshots to: {output_path}")
    
    # Create Excel file with unified position matrix
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Create unified position matrix sheet
        position_matrix_df = _create_unified_position_matrix(multi_portfolio)
        position_matrix_df.to_excel(writer, sheet_name='Portfolio_Matrix', index=False)
        
        # Create summary sheet if requested
        if include_summary:
            summary_df = _create_portfolio_summary_sheet_v2(multi_portfolio)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    # Log export summary
    total_accounts = len(multi_portfolio.snapshots)
    total_positions = sum(len([p for p in s.positions if p.position != 0]) for s in multi_portfolio.snapshots)
    
    logger.info(f"Portfolio export completed: {total_accounts} accounts, "
               f"{total_positions} total positions exported to {output_path.name}")
    
    return output_path


def _create_unified_position_matrix(multi_portfolio: 'MultiAccountPortfolio') -> pd.DataFrame:
    """Create unified position matrix with all accounts and positions."""
    
    # Collect all unique symbols across all accounts
    all_symbols = set()
    account_data = {}
    
    for snapshot in multi_portfolio.snapshots:
        account_summary = snapshot.get_positions_summary()
        account_data[snapshot.account_id] = {
            'positions': {pos['Symbol']: pos for pos in account_summary['positions']},
            'net_liquidation': float(account_summary['total_value']),
            'cash_percentage': account_summary['cash_percentage'],
            'account_summary': snapshot.account_summary
        }
        
        # Add symbols to the set
        for pos in account_summary['positions']:
            all_symbols.add(pos['Symbol'])
    
    # Sort symbols for consistent ordering
    all_symbols = sorted(all_symbols)
    
    # Create the matrix data
    matrix_data = []
    
    for account_id, data in account_data.items():
        row = {'Account_ID': account_id}
        
        # Add account summary columns first
        net_liq = data['net_liquidation']
        row['Net_Liquidation_Value'] = net_liq
        
        # Calculate cash information from account summary
        cash_base = 0
        cash_local = 0
        if data['account_summary']:
            cash_base = float(data['account_summary'].total_cash_value or 0)
            # For now, assume cash_local same as cash_base (can be enhanced later)
            cash_local = cash_base
        
        row['Cash_Base_Currency'] = cash_base
        row['Cash_Local_Currency'] = cash_local
        
        # Calculate risk asset percentage
        total_position_value = sum(
            abs(pos.get('Market_Value', 0)) for pos in data['positions'].values()
        )
        
        if net_liq != 0:
            cash_pct = (cash_base / net_liq) * 100
            risk_asset_pct = (total_position_value / net_liq) * 100
        else:
            cash_pct = 0
            risk_asset_pct = 0
        
        row['Risk_Asset_Pct'] = risk_asset_pct
        row['Cash_Pct'] = cash_pct
        
        # Add position weights for each symbol
        for symbol in all_symbols:
            if symbol in data['positions']:
                pos_data = data['positions'][symbol]
                weight_pct = pos_data['Weight_Pct']
                # Get the company name if available
                company_name = pos_data.get('Description', symbol)
            else:
                weight_pct = 0.0
                company_name = symbol
            
            # Use safe column names for Excel (symbol + company name)
            safe_symbol = symbol.replace('/', '_').replace(' ', '_')
            safe_name = company_name.replace('/', '_').replace(' ', '_')
            # Create column header with both symbol and name
            col_header = f'{safe_symbol}_{safe_name}_Weight' if safe_name != safe_symbol else f'{safe_symbol}_Weight'
            # Limit column name length to avoid Excel issues
            if len(col_header) > 50:
                col_header = f'{safe_symbol}_Weight'
            
            row[col_header] = weight_pct
        
        matrix_data.append(row)
    
    df = pd.DataFrame(matrix_data)
    
    # Reorder columns to match requirements
    base_cols = [
        'Account_ID', 
        'Net_Liquidation_Value',
        'Risk_Asset_Pct', 
        'Cash_Pct',
        'Cash_Base_Currency', 
        'Cash_Local_Currency'
    ]
    
    symbol_cols = [col for col in df.columns if col.endswith('_Weight')]
    
    # Reorder columns
    ordered_cols = base_cols + symbol_cols
    df = df[ordered_cols]
    
    return df


def _create_portfolio_summary_sheet_v2(multi_portfolio: 'MultiAccountPortfolio') -> pd.DataFrame:
    """Create improved summary sheet with IBKR standard terminology."""
    
    summary_data = []
    
    # Add header information
    combined_summary = multi_portfolio.get_combined_summary()
    
    summary_data.extend([
        ['Portfolio Summary', '', '', '', '', '', ''],
        ['Export Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '', '', '', '', ''],
        ['Total Accounts', combined_summary['total_accounts'], '', '', '', '', ''],
        ['Total Net Liquidation Value', f"${combined_summary['total_portfolio_value']:,.2f}", '', '', '', '', ''],
        ['', '', '', '', '', '', ''],
        ['Account Details', '', '', '', '', '', ''],
        ['Account ID', 'Net Liquidation Value', 'Risk Asset %', 'Cash %', 'Cash Base Currency', 'Cash Local Currency', 'Active Positions']
    ])
    
    # Add account-by-account details
    for snapshot in multi_portfolio.snapshots:
        account_summary = snapshot.get_positions_summary()
        
        net_liq = account_summary['total_value']
        
        # Calculate cash information
        cash_base = 0
        cash_local = 0
        if snapshot.account_summary:
            cash_base = float(snapshot.account_summary.total_cash_value or 0)
            cash_local = cash_base  # Simplified for now
        
        # Calculate risk asset percentage
        total_position_value = sum(
            abs(pos.get('Market_Value', 0)) for pos in account_summary['positions']
        )
        
        if net_liq != 0:
            cash_pct = (cash_base / net_liq) * 100
            risk_asset_pct = (total_position_value / net_liq) * 100
        else:
            cash_pct = 0
            risk_asset_pct = 0
        
        # Count active positions (non-zero)
        active_positions = len([p for p in account_summary['positions'] if p.get('Position', 0) != 0])
        
        summary_data.append([
            snapshot.account_id,
            f"${net_liq:,.2f}",
            f"{risk_asset_pct:.1f}%",
            f"{cash_pct:.1f}%",
            f"${cash_base:,.2f}",
            f"${cash_local:,.2f}",
            active_positions
        ])
    
    return pd.DataFrame(summary_data)
