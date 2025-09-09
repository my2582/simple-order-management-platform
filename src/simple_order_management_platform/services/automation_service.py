"""Automated portfolio update and notification service."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import logging
import traceback

from ..auth.permissions import UserRole, get_role_ibkr_params
from ..core.connector import IBConnector
from ..providers.ib import IBProvider
from ..services.portfolio_service import PortfolioService
from ..utils.ibkr_exporters import export_ibkr_portfolio_report
from ..integrations.sharepoint import create_sharepoint_integration
from ..integrations.email import create_email_integration
from ..config.loader import config_loader

logger = logging.getLogger(__name__)


class AutomatedPortfolioService:
    """Service for automated portfolio updates with SharePoint and email integration."""
    
    def __init__(self):
        """Initialize the automated portfolio service."""
        self.sharepoint = create_sharepoint_integration()
        self.email = create_email_integration()
        
        # Load configuration
        app_config = config_loader.load_app_config()
        self.email_recipient = app_config.app.get('email', {}).get('recipient', 'minsu.yeom@arkifinance.com')
    
    def run_daily_portfolio_update(
        self,
        account_ids: Optional[List[str]] = None,
        send_email: bool = True,
        upload_to_sharepoint: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete daily portfolio update process.
        
        Args:
            account_ids: Specific account IDs to process (None for all)
            send_email: Whether to send email notification
            upload_to_sharepoint: Whether to upload to SharePoint
            
        Returns:
            Dictionary with operation results and summary
        """
        start_time = datetime.now()
        operation_log = []
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'operation_log': operation_log,
            'files_created': [],
            'errors': []
        }
        
        try:
            operation_log.append(f"🚀 Starting daily portfolio update at {start_time.strftime('%Y-%m-%d %H:%M:%S SGT')}")
            
            # Step 1: Download portfolio data
            operation_log.append("📊 Downloading portfolio positions from IBKR...")
            portfolio_data = self._download_portfolio_data(account_ids)
            
            if not portfolio_data['success']:
                result['errors'].extend(portfolio_data['errors'])
                return result
            
            multi_portfolio = portfolio_data['multi_portfolio']
            operation_log.append(f"✅ Successfully downloaded {len(multi_portfolio.snapshots)} accounts")
            
            # Step 2: Generate Excel report
            operation_log.append("📄 Generating IBKR standard Excel report...")
            excel_result = self._generate_excel_report(multi_portfolio)
            
            if not excel_result['success']:
                result['errors'].extend(excel_result['errors'])
                return result
            
            excel_path = excel_result['file_path']
            result['files_created'].append(str(excel_path))
            operation_log.append(f"✅ Excel report generated: {excel_path.name}")
            
            # Step 3: Upload to SharePoint
            sharepoint_path = None
            if upload_to_sharepoint and self.sharepoint.is_available():
                operation_log.append("☁️ Uploading to SharePoint...")
                sharepoint_result = self._upload_to_sharepoint(excel_path)
                
                if sharepoint_result['success']:
                    sharepoint_path = sharepoint_result['sharepoint_path']
                    operation_log.append(f"✅ Uploaded to SharePoint: {sharepoint_path}")
                else:
                    operation_log.append(f"⚠️ SharePoint upload failed: {sharepoint_result['error']}")
            elif not self.sharepoint.is_available():
                operation_log.append("⚠️ SharePoint not available - skipping upload")
            
            # Step 4: Send email notification
            if send_email:
                operation_log.append("📧 Sending email notification...")
                email_result = self._send_email_notification(excel_path, multi_portfolio, sharepoint_path)
                
                if email_result['success']:
                    operation_log.append(f"✅ Email sent to {self.email_recipient}")
                else:
                    operation_log.append(f"⚠️ Email sending failed: {email_result['error']}")
            
            # Success!
            end_time = datetime.now()
            duration = end_time - start_time
            
            result.update({
                'success': True,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'accounts_processed': len(multi_portfolio.snapshots),
                'total_portfolio_value': sum(
                    s.get_positions_summary()['total_value'] 
                    for s in multi_portfolio.snapshots
                ),
                'sharepoint_uploaded': sharepoint_path is not None,
                'email_sent': send_email
            })
            
            operation_log.append(f"🎉 Daily portfolio update completed successfully in {duration.total_seconds():.1f} seconds")
            
        except Exception as e:
            error_msg = f"Unexpected error in daily portfolio update: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            result['errors'].append(error_msg)
            operation_log.append(f"❌ {error_msg}")
            
            # Send error notification
            try:
                self._send_error_notification("Daily Portfolio Update", error_msg, {
                    'operation_log': operation_log,
                    'account_ids': account_ids
                })
            except Exception as email_error:
                logger.error(f"Failed to send error notification: {email_error}")
        
        return result
    
    def _download_portfolio_data(self, account_ids: Optional[List[str]]) -> Dict[str, Any]:
        """Download portfolio data from IBKR."""
        try:
            # Get IBKR connection parameters for portfolio manager role
            ibkr_params = get_role_ibkr_params(UserRole.PORTFOLIO_MANAGER)
            
            # Connect to IBKR and download portfolio data
            with IBConnector(**ibkr_params) as connector:
                provider = IBProvider(connector)
                portfolio_service = PortfolioService(provider)
                
                multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_ids)
            
            if not multi_portfolio.snapshots:
                return {
                    'success': False,
                    'errors': ['No portfolio data downloaded - no accounts found or accessible']
                }
            
            return {
                'success': True,
                'multi_portfolio': multi_portfolio
            }
            
        except Exception as e:
            error_msg = f"Failed to download portfolio data: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'errors': [error_msg]
            }
    
    def _generate_excel_report(self, multi_portfolio) -> Dict[str, Any]:
        """Generate IBKR standard Excel report."""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"daily_portfolio_positions_{timestamp}.xlsx"
            
            # Export to Excel
            excel_path = export_ibkr_portfolio_report(
                multi_portfolio=multi_portfolio,
                output_filename=filename,
                include_metadata=True
            )
            
            return {
                'success': True,
                'file_path': excel_path
            }
            
        except Exception as e:
            error_msg = f"Failed to generate Excel report: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'errors': [error_msg]
            }
    
    def _upload_to_sharepoint(self, excel_path: Path) -> Dict[str, Any]:
        """Upload Excel report to SharePoint."""
        try:
            # Generate SharePoint-friendly filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sharepoint_filename = f"portfolio_positions_{timestamp}.xlsx"
            
            sharepoint_path = self.sharepoint.upload_portfolio_report(
                local_file_path=excel_path,
                create_dated_folder=True,
                custom_name=sharepoint_filename
            )
            
            if sharepoint_path:
                return {
                    'success': True,
                    'sharepoint_path': sharepoint_path
                }
            else:
                return {
                    'success': False,
                    'error': 'SharePoint upload returned None - check logs for details'
                }
                
        except Exception as e:
            error_msg = f"Failed to upload to SharePoint: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _send_email_notification(
        self, 
        excel_path: Path, 
        multi_portfolio, 
        sharepoint_path: Optional[Path]
    ) -> Dict[str, Any]:
        """Send email notification with portfolio report."""
        try:
            # Prepare account summary for email
            combined_summary = multi_portfolio.get_combined_summary()
            
            # Add per-account details
            accounts_detail = []
            for snapshot in multi_portfolio.snapshots:
                account_summary = snapshot.get_positions_summary()
                accounts_detail.append({
                    'account_id': snapshot.account_id,
                    'total_value': account_summary['total_value'],
                    'position_count': len([p for p in account_summary['positions'] if p.get('Position', 0) != 0]),
                    'cash_percentage': account_summary['cash_percentage']
                })
            
            email_summary = {
                **combined_summary,
                'accounts': accounts_detail,
                'sharepoint_path': str(sharepoint_path) if sharepoint_path else None
            }
            
            # Send email
            success = self.email.send_portfolio_report(
                recipient_email=self.email_recipient,
                report_file_path=excel_path,
                account_summary=email_summary
            )
            
            if success:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Email sending failed - check logs for details'}
                
        except Exception as e:
            error_msg = f"Failed to send email notification: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _send_error_notification(
        self, 
        error_type: str, 
        error_message: str, 
        context: Dict[str, Any]
    ) -> None:
        """Send error notification email."""
        try:
            self.email.send_error_notification(
                recipient_email=self.email_recipient,
                error_type=error_type,
                error_message=error_message,
                context=context
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def test_integrations(self) -> Dict[str, Any]:
        """Test all integrations (SharePoint, Email, IBKR)."""
        results = {
            'sharepoint': {'available': False, 'error': None},
            'email': {'available': False, 'error': None},
            'ibkr': {'available': False, 'error': None}
        }
        
        # Test SharePoint
        try:
            results['sharepoint']['available'] = self.sharepoint.is_available()
            if results['sharepoint']['available']:
                storage_info = self.sharepoint.get_storage_info()
                results['sharepoint']['info'] = storage_info
        except Exception as e:
            results['sharepoint']['error'] = str(e)
        
        # Test Email
        try:
            results['email']['available'] = self.email.test_connection()
        except Exception as e:
            results['email']['error'] = str(e)
        
        # Test IBKR
        try:
            ibkr_params = get_role_ibkr_params(UserRole.PORTFOLIO_MANAGER)
            with IBConnector(**ibkr_params) as connector:
                results['ibkr']['available'] = connector.is_connected()
        except Exception as e:
            results['ibkr']['error'] = str(e)
        
        return results


# Global instance for easy access
automated_portfolio_service = AutomatedPortfolioService()