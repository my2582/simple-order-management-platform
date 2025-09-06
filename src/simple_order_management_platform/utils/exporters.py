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
    Export portfolio snapshots to Excel file.
    
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
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Create summary sheet if requested
        if include_summary:
            summary_df = _create_portfolio_summary_sheet(multi_portfolio)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Create individual sheets for each account
        for snapshot in multi_portfolio.snapshots:
            account_summary = snapshot.get_positions_summary()
            
            # Create sheet even if no positions (show account info)
            create_account_sheet = True
            
            # Create sheet name
            sheet_name = f"Account_{snapshot.account_id}"
            if len(sheet_name) > 31:  # Excel sheet name limit
                sheet_name = f"Acc_{snapshot.account_id[:25]}"
            
            try:
                # Create account metadata
                metadata_rows = [
                    ['Account Information', ''],
                    ['Account ID', snapshot.account_id],
                    ['Timestamp', snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')],
                    ['Total Portfolio Value', f"${account_summary['total_value']:,.2f}"],
                    ['Cash Percentage', f"{account_summary['cash_percentage']:.2f}%"],
                    ['Number of Positions', len(account_summary['positions'])],
                    ['', ''],
                ]
                
                # Add account summary information if available
                if snapshot.account_summary:
                    summary = snapshot.account_summary
                    metadata_rows.extend([
                        ['Account Summary Details', ''],
                        ['Net Liquidation', f"${float(summary.net_liquidation or 0):,.2f}"],
                        ['Total Cash Value', f"${float(summary.total_cash_value or 0):,.2f}"],
                        ['Buying Power', f"${float(summary.buying_power or 0):,.2f}"],
                        ['Unrealized PnL', f"${float(summary.unrealized_pnl or 0):,.2f}"],
                        ['', ''],
                    ])
                
                metadata_rows.extend([['', ''], ['Position Details', '']])
                metadata_df = pd.DataFrame(metadata_rows, columns=['Field', 'Value'])
                
                # Write metadata
                metadata_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
                
                # Write positions data if any
                start_row = len(metadata_df) + 1
                if account_summary['positions']:
                    positions_df = pd.DataFrame(account_summary['positions'])
                    positions_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
                else:
                    # Create empty positions template
                    empty_positions = pd.DataFrame([{
                        'Symbol': 'No positions found',
                        'Exchange': '',
                        'Currency': '',
                        'SecType': '',
                        'Position': 0,
                        'Market_Price': 0,
                        'Market_Value': 0,
                        'Weight_Pct': 0,
                        'Avg_Cost': 0,
                        'Unrealized_PnL': 0,
                        'Local_Symbol': ''
                    }])
                    empty_positions.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
                
                logger.debug(f"Exported account {snapshot.account_id} to sheet '{sheet_name}'")
                
            except Exception as e:
                logger.error(f"Failed to export account {snapshot.account_id} to Excel: {e}")
                continue
    
    # Log export summary
    total_accounts = len(multi_portfolio.snapshots)
    total_positions = sum(len(s.positions) for s in multi_portfolio.snapshots if s.positions)
    
    logger.info(f"Portfolio export completed: {total_accounts} accounts, "
               f"{total_positions} total positions exported to {output_path.name}")
    
    return output_path


def _create_portfolio_summary_sheet(multi_portfolio: 'MultiAccountPortfolio') -> pd.DataFrame:
    """Create summary sheet for portfolio snapshots."""
    
    summary_data = []
    
    # Add header information
    combined_summary = multi_portfolio.get_combined_summary()
    
    summary_data.extend([
        ['Portfolio Summary', '', '', '', '', ''],
        ['Export Time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '', '', '', ''],
        ['Total Accounts', combined_summary['total_accounts'], '', '', '', ''],
        ['Total Portfolio Value', f"${combined_summary['total_portfolio_value']:,.2f}", '', '', '', ''],
        ['Total Positions', combined_summary['total_positions'], '', '', '', ''],
        ['', '', '', '', '', ''],
        ['Account Details', '', '', '', '', ''],
        ['Account ID', 'Positions', 'Total Value', 'Cash %', 'Largest Position', 'Top Holdings']
    ])
    
    # Add account-by-account details
    for snapshot in multi_portfolio.snapshots:
        account_summary = snapshot.get_positions_summary()
        
        # Find largest position by value
        largest_position = ""
        top_holdings = ""
        
        if account_summary['positions']:
            positions_sorted = sorted(
                account_summary['positions'], 
                key=lambda x: abs(x.get('Market_Value', 0)), 
                reverse=True
            )
            
            if positions_sorted:
                largest_position = f"{positions_sorted[0]['Symbol']} (${abs(positions_sorted[0].get('Market_Value', 0)):,.0f})"
                
                # Top 3 holdings
                top_3 = positions_sorted[:3]
                top_holdings = ", ".join([
                    f"{pos['Symbol']} ({pos['Weight_Pct']:.1f}%)"
                    for pos in top_3
                ])
        
        summary_data.append([
            snapshot.account_id,
            len(account_summary['positions']),
            f"${account_summary['total_value']:,.2f}",
            f"{account_summary['cash_percentage']:.1f}%",
            largest_position,
            top_holdings[:50] + "..." if len(top_holdings) > 50 else top_holdings
        ])
    
    return pd.DataFrame(summary_data)
