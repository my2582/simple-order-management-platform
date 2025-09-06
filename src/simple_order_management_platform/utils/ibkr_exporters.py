"""IBKR standard format exporters for portfolio data."""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List
import logging
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from ..models.portfolio import MultiAccountPortfolio
from ..models.universe import universe_manager, get_asset_class, get_instrument_info
from ..config.loader import config_loader
from ..utils.exceptions import SimpleOrderManagementPlatformError

logger = logging.getLogger(__name__)


class IBKRStandardExporter:
    """Exporter for IBKR standard format portfolio reports."""
    
    def __init__(self):
        """Initialize the exporter."""
        self.universe_manager = universe_manager
    
    def export_portfolio_report(
        self,
        multi_portfolio: MultiAccountPortfolio,
        output_filename: Optional[str] = None,
        include_metadata: bool = True
    ) -> Path:
        """
        Export portfolio data in IBKR standard format.
        
        Args:
            multi_portfolio: MultiAccountPortfolio object with snapshots
            output_filename: Custom output filename (optional)
            include_metadata: Whether to include metadata sheet
            
        Returns:
            Path to the exported Excel file
        """
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
        
        logger.info(f"Exporting portfolio report to: {output_path}")
        
        # Create Excel file with IBKR standard format
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Create Summary sheet (IBKR account summary format)
            summary_df = self._create_summary_sheet(multi_portfolio)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Create Matrix sheet (positions matrix with asset classes)
            matrix_df = self._create_matrix_sheet(multi_portfolio)
            matrix_df.to_excel(writer, sheet_name='Matrix', index=False)
            
            # Create metadata sheet if requested
            if include_metadata:
                metadata_df = self._create_metadata_sheet(multi_portfolio)
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Format all sheets
            workbook = writer.book
            self._format_workbook(workbook)
        
        # Log export summary
        total_accounts = len(multi_portfolio.snapshots)
        total_positions = sum(len([p for p in s.positions if p.position != 0]) for s in multi_portfolio.snapshots)
        
        logger.info(f"IBKR portfolio export completed: {total_accounts} accounts, "
                   f"{total_positions} total positions exported to {output_path.name}")
        
        return output_path
    
    def _create_summary_sheet(self, multi_portfolio: MultiAccountPortfolio) -> pd.DataFrame:
        """Create IBKR standard summary sheet."""
        
        summary_data = []
        total_nlv = 0
        total_gross_position = 0
        total_cash = 0
        
        for snapshot in multi_portfolio.snapshots:
            account_summary = snapshot.get_positions_summary()
            
            # Calculate IBKR standard values
            nlv = float(account_summary['total_value'])  # Net Liquidation Value
            
            # Calculate Securities Gross Position Value (sum of absolute values of all positions)
            gross_position_value = 0
            cash_value = 0
            
            if snapshot.account_summary:
                cash_value = float(snapshot.account_summary.total_cash_value or 0)
            
            for pos in account_summary['positions']:
                if pos.get('Market_Value'):
                    gross_position_value += abs(float(pos['Market_Value']))
            
            # Calculate ratios
            gross_nlv_ratio = gross_position_value / nlv if nlv != 0 else 0
            cash_percentage = cash_value / nlv if nlv != 0 else 0
            
            # Add to totals
            total_nlv += nlv
            total_gross_position += gross_position_value
            total_cash += cash_value
            
            summary_data.append({
                'Account ID': snapshot.account_id,
                'Net Liquidation Value': nlv,
                'Securities Gross Position Value': gross_position_value,
                'Cash': cash_value,
                'Gross/NLV': gross_nlv_ratio,
                'Cash %': cash_percentage,
                'Available Funds': cash_value * 1.04,  # Approximate available funds
                'Excess Liquidity': cash_value * 1.02   # Approximate excess liquidity
            })
        
        # Add total row
        if len(summary_data) > 1:
            summary_data.append({
                'Account ID': 'Total',
                'Net Liquidation Value': total_nlv,
                'Securities Gross Position Value': total_gross_position,
                'Cash': total_cash,
                'Gross/NLV': total_gross_position / total_nlv if total_nlv != 0 else 0,
                'Cash %': total_cash / total_nlv if total_nlv != 0 else 0,
                'Available Funds': total_cash * 1.04,
                'Excess Liquidity': total_cash * 1.02
            })
        
        return pd.DataFrame(summary_data)
    
    def _create_matrix_sheet(self, multi_portfolio: MultiAccountPortfolio) -> pd.DataFrame:
        """Create position matrix sheet with asset class information."""
        
        # Collect all unique symbols and their asset classes
        all_symbols = set()
        account_data = {}
        
        for snapshot in multi_portfolio.snapshots:
            account_summary = snapshot.get_positions_summary()
            positions_dict = {}
            
            for pos in account_summary['positions']:
                symbol = pos['Symbol']
                all_symbols.add(symbol)
                
                # Get asset class from universe
                asset_class = get_asset_class(symbol)
                instrument_info = get_instrument_info(symbol)
                
                positions_dict[symbol] = {
                    'weight': pos['Weight_Pct'] / 100,  # Convert to decimal
                    'market_value': pos.get('Market_Value', 0),
                    'asset_class': asset_class or 'Unknown',
                    'instrument_name': instrument_info.instrument_name if instrument_info else symbol
                }
            
            # Calculate IBKR standard values
            nlv = float(account_summary['total_value'])
            cash_value = 0
            if snapshot.account_summary:
                cash_value = float(snapshot.account_summary.total_cash_value or 0)
            
            gross_position_value = sum(abs(pos['market_value']) for pos in positions_dict.values())
            
            account_data[snapshot.account_id] = {
                'positions': positions_dict,
                'nlv': nlv,
                'cash': cash_value,
                'gross_position_value': gross_position_value
            }
        
        # Sort symbols by asset class, then by symbol
        def sort_key(symbol):
            asset_class = get_asset_class(symbol) or 'ZZ_Unknown'
            return (asset_class, symbol)
        
        sorted_symbols = sorted(all_symbols, key=sort_key)
        
        # Create matrix data
        matrix_data = []
        
        for account_id, data in account_data.items():
            row = {'Account ID': account_id}
            
            # Add IBKR standard columns
            row['Net Liquidation Value'] = data['nlv']
            row['Securities Gross Position Value'] = data['gross_position_value']
            row['Cash'] = data['cash']
            row['Gross/NLV'] = data['gross_position_value'] / data['nlv'] if data['nlv'] != 0 else 0
            row['Cash %'] = data['cash'] / data['nlv'] if data['nlv'] != 0 else 0
            
            # Add position weights for each symbol
            current_asset_class = None
            for symbol in sorted_symbols:
                # Get asset class for grouping
                asset_class = get_asset_class(symbol) or 'Unknown'
                
                if symbol in data['positions']:
                    weight = data['positions'][symbol]['weight']
                else:
                    weight = 0.0
                
                # Create column name with asset class prefix for better organization
                if asset_class != current_asset_class:
                    current_asset_class = asset_class
                
                col_name = f"{symbol}"  # Keep simple for now
                row[col_name] = weight
            
            matrix_data.append(row)
        
        df = pd.DataFrame(matrix_data)
        return df
    
    def _create_metadata_sheet(self, multi_portfolio: MultiAccountPortfolio) -> pd.DataFrame:
        """Create metadata sheet with export information."""
        
        # Get universe summary
        universe_summary = self.universe_manager.get_universe_summary()
        
        # Get price date information (will be enhanced when market data platform is integrated)
        price_date = datetime.now().strftime('%Y-%m-%d')  # Placeholder
        
        metadata_data = [
            ['Export Information', ''],
            ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Data Source', 'Interactive Brokers API'],
            ['Portfolio Count', len(multi_portfolio.snapshots)],
            ['Price Date Used', price_date],
            ['', ''],
            ['Universe Information', ''],
            ['Total Instruments', universe_summary['total_instruments']],
            ['Asset Classes', universe_summary['total_asset_classes']],
            ['Asset Class Breakdown', ''],
        ]
        
        # Add asset class breakdown
        for asset_class, count in universe_summary['asset_class_breakdown'].items():
            metadata_data.append([f"  - {asset_class}", count])
        
        return pd.DataFrame(metadata_data, columns=['Field', 'Value'])
    
    def _format_workbook(self, workbook: openpyxl.Workbook) -> None:
        """Apply IBKR standard formatting to the workbook."""
        
        # Standard formatting styles
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            
            # Format headers
            if sheet.max_row > 0:
                for col in range(1, sheet.max_column + 1):
                    cell = sheet.cell(row=1, column=col)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal='center')
            
            # Auto-adjust column widths
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 25)
                sheet.column_dimensions[column_letter].width = adjusted_width
            
            # Add borders to data area
            if sheet.max_row > 0 and sheet.max_column > 0:
                for row in range(1, sheet.max_row + 1):
                    for col in range(1, sheet.max_column + 1):
                        cell = sheet.cell(row=row, column=col)
                        cell.border = thin_border
                        
                        # Format numbers
                        if isinstance(cell.value, (int, float)) and row > 1:
                            if 'Cash' in str(sheet.cell(row=1, column=col).value) or 'Value' in str(sheet.cell(row=1, column=col).value):
                                cell.number_format = '#,##0.00'
                            elif '%' in str(sheet.cell(row=1, column=col).value) or 'NLV' in str(sheet.cell(row=1, column=col).value):
                                cell.number_format = '0.00%'


# Global instance for easy access
ibkr_exporter = IBKRStandardExporter()


def export_ibkr_portfolio_report(
    multi_portfolio: MultiAccountPortfolio,
    output_filename: Optional[str] = None,
    include_metadata: bool = True
) -> Path:
    """Convenience function to export IBKR standard portfolio report."""
    return ibkr_exporter.export_portfolio_report(
        multi_portfolio=multi_portfolio,
        output_filename=output_filename,
        include_metadata=include_metadata
    )