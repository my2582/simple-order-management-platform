"""Email integration for automated notifications and report delivery."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class EmailIntegration:
    """Integration for sending automated email notifications and reports."""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        use_tls: bool = True,
        password: str = None
    ):
        """
        Initialize email integration.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            sender_email: Sender email address
            use_tls: Whether to use TLS encryption
            password: Email password (optional, will try env var if not provided)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.use_tls = use_tls
        
        # Try to get password from: 1) parameter, 2) environment variable
        self.password = password or os.environ.get('EMAIL_PASSWORD')
        if not self.password:
            logger.warning("No email password found in config or EMAIL_PASSWORD environment variable. Email sending may fail.")
    
    def set_password(self, password: str) -> None:
        """Set email password manually."""
        self.password = password
    
    def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            if self.password:
                server.login(self.sender_email, self.password)
            
            server.quit()
            logger.info("Email connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
    
    def send_portfolio_report(
        self,
        recipient_email: str,
        report_file_path: Path,
        account_summary: Dict[str, Any],
        additional_files: Optional[List[Path]] = None
    ) -> bool:
        """
        Send portfolio report via email.
        
        Args:
            recipient_email: Recipient email address
            report_file_path: Path to the portfolio report file
            account_summary: Summary information for email body
            additional_files: Additional files to attach (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Daily Portfolio Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create email body
            body = self._create_portfolio_email_body(account_summary)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach main report
            if report_file_path.exists():
                self._attach_file(msg, report_file_path)
            else:
                logger.error(f"Report file not found: {report_file_path}")
                return False
            
            # Attach additional files
            if additional_files:
                for file_path in additional_files:
                    if file_path.exists():
                        self._attach_file(msg, file_path)
                    else:
                        logger.warning(f"Additional file not found: {file_path}")
            
            # Send email
            return self._send_message(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send portfolio report: {e}")
            return False
    
    def send_market_data_report(
        self,
        recipient_email: str,
        data_file_path: Path,
        data_summary: Dict[str, Any]
    ) -> bool:
        """
        Send market data update report via email.
        
        Args:
            recipient_email: Recipient email address
            data_file_path: Path to the market data file
            data_summary: Summary information for email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Market Data Update - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create email body
            body = self._create_market_data_email_body(data_summary)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach data file
            if data_file_path.exists():
                self._attach_file(msg, data_file_path)
            else:
                logger.error(f"Data file not found: {data_file_path}")
                return False
            
            # Send email
            return self._send_message(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send market data report: {e}")
            return False
    
    def send_error_notification(
        self,
        recipient_email: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send error notification email.
        
        Args:
            recipient_email: Recipient email address
            error_type: Type of error (e.g., 'Portfolio Download', 'Market Data Update')
            error_message: Error message details
            context: Additional context information
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"🚨 System Error Alert - {error_type}"
            
            # Create error email body
            body = self._create_error_email_body(error_type, error_message, context)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            return self._send_message(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False
    
    def _create_portfolio_email_body(self, account_summary: Dict[str, Any]) -> str:
        """Create HTML email body for portfolio report."""
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S SGT')
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .table th, .table td {{ padding: 8px 12px; text-align: left; border: 1px solid #ddd; }}
                .table th {{ background-color: #3498db; color: white; }}
                .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Daily Portfolio Report</h2>
                <p>Generated on: {current_date}</p>
            </div>
            
            <div class="summary">
                <h3>📈 Portfolio Summary</h3>
                <ul>
                    <li><strong>Total Accounts:</strong> {account_summary.get('total_accounts', 'N/A')}</li>
                    <li><strong>Total Portfolio Value:</strong> ${account_summary.get('total_portfolio_value', 0):,.2f}</li>
                    <li><strong>Total Positions:</strong> {account_summary.get('total_positions', 'N/A')}</li>
                    <li><strong>Data Source:</strong> Interactive Brokers API</li>
                </ul>
            </div>
            
            <h3>📋 Account Details</h3>
            <table class="table">
                <thead>
                    <tr>
                        <th>Account ID</th>
                        <th>Portfolio Value</th>
                        <th>Positions</th>
                        <th>Cash %</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add account details if available
        if 'accounts' in account_summary:
            for account in account_summary['accounts']:
                html_body += f"""
                    <tr>
                        <td>{account.get('account_id', 'N/A')}</td>
                        <td>${account.get('total_value', 0):,.2f}</td>
                        <td>{account.get('position_count', 'N/A')}</td>
                        <td>{account.get('cash_percentage', 0):.1f}%</td>
                        <td>✅ Active</td>
                    </tr>
                """
        
        html_body += """
                </tbody>
            </table>
            
            <div class="summary">
                <h3>📎 Attachments</h3>
                <p>Please find the detailed portfolio report attached to this email in Excel format.</p>
                <p>The report includes:</p>
                <ul>
                    <li>Summary sheet with account-level information</li>
                    <li>Position matrix with asset class breakdown</li>
                    <li>Metadata with export details</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>This is an automated report generated by the Simple Order Management Platform.</p>
                <p>For questions or issues, please contact: minsu.yeom@arkifinance.com</p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _create_market_data_email_body(self, data_summary: Dict[str, Any]) -> str:
        """Create HTML email body for market data report."""
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S SGT')
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📈 Market Data Update Report</h2>
                <p>Generated on: {current_date}</p>
            </div>
            
            <div class="summary">
                <h3>🎯 Update Summary</h3>
                <ul>
                    <li><strong>Symbols Updated:</strong> {data_summary.get('symbols_updated', 'N/A')}</li>
                    <li><strong>Price Date:</strong> {data_summary.get('price_date', 'N/A')}</li>
                    <li><strong>Data Source:</strong> Interactive Brokers API</li>
                    <li><strong>Update Status:</strong> ✅ Completed Successfully</li>
                </ul>
            </div>
            
            <div class="summary">
                <h3>📎 Attachments</h3>
                <p>Please find the updated market data file attached to this email.</p>
            </div>
            
            <div class="footer">
                <p>This is an automated report generated by the Market Data Platform.</p>
                <p>For questions or issues, please contact: minsu.yeom@arkifinance.com</p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _create_error_email_body(
        self, 
        error_type: str, 
        error_message: str, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create HTML email body for error notification."""
        
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S SGT')
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; }}
                .error {{ background-color: #fdf2f2; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #e74c3c; }}
                .context {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 System Error Alert</h2>
                <p>Error occurred on: {current_date}</p>
            </div>
            
            <div class="error">
                <h3>❌ Error Type: {error_type}</h3>
                <p><strong>Error Message:</strong></p>
                <pre style="white-space: pre-wrap; font-family: monospace;">{error_message}</pre>
            </div>
        """
        
        if context:
            html_body += """
            <div class="context">
                <h3>📋 Context Information</h3>
                <ul>
            """
            for key, value in context.items():
                html_body += f"<li><strong>{key}:</strong> {value}</li>"
            
            html_body += """
                </ul>
            </div>
            """
        
        html_body += """
            <div class="footer">
                <p>This is an automated error notification from the Simple Order Management Platform.</p>
                <p>Please investigate and resolve the issue as soon as possible.</p>
                <p>For technical support, contact: minsu.yeom@arkifinance.com</p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _attach_file(self, msg: MIMEMultipart, file_path: Path) -> None:
        """Attach file to email message."""
        with open(file_path, 'rb') as attachment:
            part = MIMEApplication(attachment.read(), Name=file_path.name)
            part['Content-Disposition'] = f'attachment; filename="{file_path.name}"'
            msg.attach(part)
    
    def _send_message(self, msg: MIMEMultipart, recipient_email: str) -> bool:
        """Send email message via SMTP."""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            if self.password:
                server.login(self.sender_email, self.password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
    
    def send_notification(
        self,
        subject: str,
        html_content: str,
        recipient_email: Optional[str] = None
    ) -> bool:
        """
        Send a general notification email.
        
        Args:
            subject: Email subject
            html_content: HTML content for email body
            recipient_email: Recipient email address (uses default if not provided)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Use default recipient if not provided
            if not recipient_email:
                recipient_email = "minsu.yeom@arkifinance.com"  # Default recipient
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            return self._send_message(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False


# Factory function for easy initialization
def create_email_integration() -> EmailIntegration:
    """Create email integration instance from configuration."""
    from ..config.loader import config_loader
    
    app_config = config_loader.load_app_config()
    email_config = app_config.app.get('email', {})
    
    return EmailIntegration(
        smtp_server=email_config.get('smtp_server', 'smtp.office365.com'),
        smtp_port=email_config.get('smtp_port', 587),
        sender_email=email_config.get('sender', 'minsu.yeom@arkifinance.com'),
        use_tls=email_config.get('use_tls', True),
        password=email_config.get('password')  # Get password from config
    )


# Global instance for easy access
email_integration = create_email_integration()