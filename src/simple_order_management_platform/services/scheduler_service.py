"""
Scheduler Service for automated daily portfolio and market data updates.

This service manages the Singapore timezone scheduling for:
- Market data updates at 6:00 AM SGT daily
- Portfolio position updates at 6:30 AM SGT daily
"""

import logging
import asyncio
import signal
import sys
from datetime import datetime, time
from typing import Optional, Dict, Any
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore

from ..config import Config
from ..integrations.email import EmailIntegration
from .automation_service import AutomatedPortfolioService
from .market_data_service import MarketDataService
from ..auth.permissions import UserRole


class SchedulerService:
    """Singapore timezone scheduler for automated daily portfolio updates."""
    
    def __init__(self, config: Config):
        """
        Initialize the scheduler service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.SchedulerService")
        
        # Initialize services
        self.automation_service = AutomatedPortfolioService()
        self.market_data_service = MarketDataService()
        # Initialize email service with proper configuration
        email_config = config.app.get('email', {})
        self.email_service = EmailIntegration(
            smtp_server=email_config.get('smtp_server', 'smtp.office365.com'),
            smtp_port=email_config.get('smtp_port', 587),
            sender_email=email_config.get('sender', 'minsu.yeom@arkifinance.com'),
            use_tls=email_config.get('use_tls', True)
        )
        
        # Setup scheduler with Singapore timezone
        self.singapore_tz = pytz.timezone('Asia/Singapore')
        
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes grace period
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.singapore_tz
        )
        
        self._running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def start(self) -> None:
        """Start the scheduler daemon."""
        if self._running:
            self.logger.warning("Scheduler is already running")
            return
        
        try:
            self.logger.info("Starting Portfolio Management Scheduler...")
            self.logger.info(f"Timezone: {self.singapore_tz}")
            
            # Add scheduled jobs
            await self._add_scheduled_jobs()
            
            # Start the scheduler
            self.scheduler.start()
            self._running = True
            
            # Log current Singapore time and next job runs
            current_time = datetime.now(self.singapore_tz)
            self.logger.info(f"Scheduler started at {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Log scheduled jobs
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                if next_run:
                    self.logger.info(f"Job '{job.id}' scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Send startup notification
            await self._send_startup_notification()
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the scheduler daemon gracefully."""
        if not self._running:
            self.logger.warning("Scheduler is not running")
            return
        
        try:
            self.logger.info("Stopping Portfolio Management Scheduler...")
            
            # Stop the scheduler
            self.scheduler.shutdown(wait=True)
            self._running = False
            
            self.logger.info("Scheduler stopped successfully")
            
            # Send shutdown notification
            await self._send_shutdown_notification()
            
        except Exception as e:
            self.logger.error(f"Error during scheduler shutdown: {e}", exc_info=True)
            raise
    
    async def _add_scheduled_jobs(self) -> None:
        """Add scheduled jobs for market data and portfolio updates."""
        # Parse schedule times from config
        market_data_time = self._parse_time_config(self.config.app['scheduling']['market_data_update'])
        portfolio_time = self._parse_time_config(self.config.app['scheduling']['portfolio_update'])
        
        # Schedule market data update (6:00 AM SGT daily)
        self.scheduler.add_job(
            self._run_market_data_update,
            CronTrigger(
                hour=market_data_time.hour,
                minute=market_data_time.minute,
                timezone=self.singapore_tz
            ),
            id='market_data_update',
            name='Daily Market Data Update',
            replace_existing=True
        )
        
        # Schedule portfolio update (6:30 AM SGT daily)
        self.scheduler.add_job(
            self._run_portfolio_update,
            CronTrigger(
                hour=portfolio_time.hour,
                minute=portfolio_time.minute,
                timezone=self.singapore_tz
            ),
            id='portfolio_update',
            name='Daily Portfolio Update',
            replace_existing=True
        )
        
        self.logger.info(f"Market data update scheduled for: {market_data_time} SGT daily")
        self.logger.info(f"Portfolio update scheduled for: {portfolio_time} SGT daily")
    
    def _parse_time_config(self, time_str: str) -> time:
        """
        Parse time configuration string to time object.
        
        Args:
            time_str: Time in HH:MM format
            
        Returns:
            time object
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour=hour, minute=minute)
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Invalid time format '{time_str}': {e}")
            raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM format.")
    
    async def _run_market_data_update(self) -> None:
        """Execute scheduled market data update."""
        job_name = "Market Data Update"
        start_time = datetime.now(self.singapore_tz)
        
        self.logger.info(f"Starting scheduled {job_name} at {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        try:
            # Update market data cache using Trade Assistant role
            await self._safe_execute(
                self.market_data_service.update_universe_prices,
                force_update=False,
                max_age_hours=24.0
            )
            
            # Export market data report
            output_file = await self._safe_execute(
                self.market_data_service.export_market_data_report
            )
            
            end_time = datetime.now(self.singapore_tz)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Completed scheduled {job_name} in {duration:.1f} seconds")
            
            # Send success notification
            await self._send_job_success_notification(
                job_name=job_name,
                duration=duration,
                output_file=output_file,
                start_time=start_time
            )
            
        except Exception as e:
            end_time = datetime.now(self.singapore_tz)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Scheduled {job_name} failed after {duration:.1f} seconds: {e}", exc_info=True)
            
            # Send failure notification
            await self._send_job_failure_notification(
                job_name=job_name,
                error=str(e),
                duration=duration,
                start_time=start_time
            )
    
    async def _run_portfolio_update(self) -> None:
        """Execute scheduled portfolio update."""
        job_name = "Portfolio Update"
        start_time = datetime.now(self.singapore_tz)
        
        self.logger.info(f"Starting scheduled {job_name} at {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        try:
            # Run full portfolio update workflow
            results = await self._safe_execute(
                self.automation_service.run_daily_portfolio_update,
                use_cached_prices=True
            )
            
            end_time = datetime.now(self.singapore_tz)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Completed scheduled {job_name} in {duration:.1f} seconds")
            
            # Send success notification with results
            await self._send_portfolio_success_notification(
                job_name=job_name,
                duration=duration,
                results=results,
                start_time=start_time
            )
            
        except Exception as e:
            end_time = datetime.now(self.singapore_tz)
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Scheduled {job_name} failed after {duration:.1f} seconds: {e}", exc_info=True)
            
            # Send failure notification
            await self._send_job_failure_notification(
                job_name=job_name,
                error=str(e),
                duration=duration,
                start_time=start_time
            )
    
    async def _safe_execute(self, func, *args, **kwargs):
        """
        Safely execute an async function with error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Re-raises any exception from the function
        """
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error executing {func.__name__}: {e}", exc_info=True)
            raise
    
    async def _send_startup_notification(self) -> None:
        """Send scheduler startup notification email."""
        try:
            current_time = datetime.now(self.singapore_tz)
            
            subject = "Portfolio Management Scheduler Started"
            
            html_content = f"""
            <html>
            <body>
                <h2>Portfolio Management Scheduler Started</h2>
                <p><strong>Status:</strong> Successfully started</p>
                <p><strong>Time:</strong> {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                
                <h3>Scheduled Tasks:</h3>
                <ul>
                    <li>Market Data Update: {self.config.app['scheduling']['market_data_update']} SGT daily</li>
                    <li>Portfolio Update: {self.config.app['scheduling']['portfolio_update']} SGT daily</li>
                </ul>
                
                <h3>Next Scheduled Runs:</h3>
                <ul>
            """
            
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                if next_run:
                    html_content += f"<li>{job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}</li>"
            
            html_content += """
                </ul>
                
                <p>The scheduler is now running and will execute tasks automatically according to the schedule.</p>
            </body>
            </html>
            """
            
            await self.email_service.send_notification(
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send startup notification: {e}")
    
    async def _send_shutdown_notification(self) -> None:
        """Send scheduler shutdown notification email."""
        try:
            current_time = datetime.now(self.singapore_tz)
            
            subject = "Portfolio Management Scheduler Stopped"
            
            html_content = f"""
            <html>
            <body>
                <h2>Portfolio Management Scheduler Stopped</h2>
                <p><strong>Status:</strong> Gracefully stopped</p>
                <p><strong>Time:</strong> {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                
                <p>All scheduled tasks have been stopped. Manual intervention may be required to restart the scheduler.</p>
            </body>
            </html>
            """
            
            await self.email_service.send_notification(
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send shutdown notification: {e}")
    
    async def _send_job_success_notification(
        self,
        job_name: str,
        duration: float,
        output_file: Optional[Path],
        start_time: datetime
    ) -> None:
        """Send job success notification email."""
        try:
            subject = f"✅ Scheduled {job_name} Completed Successfully"
            
            html_content = f"""
            <html>
            <body>
                <h2>✅ Scheduled {job_name} Completed</h2>
                <p><strong>Status:</strong> Success</p>
                <p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                <p><strong>Duration:</strong> {duration:.1f} seconds</p>
                
                {f'<p><strong>Output File:</strong> {output_file.name if output_file else "N/A"}</p>' if output_file else ''}
                
                <p>The scheduled task completed successfully with no errors.</p>
            </body>
            </html>
            """
            
            await self.email_service.send_notification(
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send job success notification: {e}")
    
    async def _send_portfolio_success_notification(
        self,
        job_name: str,
        duration: float,
        results: Dict[str, Any],
        start_time: datetime
    ) -> None:
        """Send portfolio update success notification with detailed results."""
        try:
            subject = f"✅ Scheduled {job_name} Completed Successfully"
            
            html_content = f"""
            <html>
            <body>
                <h2>✅ Scheduled {job_name} Completed</h2>
                <p><strong>Status:</strong> Success</p>
                <p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                <p><strong>Duration:</strong> {duration:.1f} seconds</p>
                
                <h3>Results:</h3>
                <ul>
            """
            
            for key, value in results.items():
                if isinstance(value, Path):
                    html_content += f"<li><strong>{key}:</strong> {value.name}</li>"
                else:
                    html_content += f"<li><strong>{key}:</strong> {value}</li>"
            
            html_content += """
                </ul>
                
                <p>The portfolio update has been completed successfully and files have been processed.</p>
            </body>
            </html>
            """
            
            await self.email_service.send_notification(
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send portfolio success notification: {e}")
    
    async def _send_job_failure_notification(
        self,
        job_name: str,
        error: str,
        duration: float,
        start_time: datetime
    ) -> None:
        """Send job failure notification email."""
        try:
            subject = f"❌ Scheduled {job_name} Failed"
            
            html_content = f"""
            <html>
            <body>
                <h2>❌ Scheduled {job_name} Failed</h2>
                <p><strong>Status:</strong> Failed</p>
                <p><strong>Start Time:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                <p><strong>Duration:</strong> {duration:.1f} seconds</p>
                
                <h3>Error Details:</h3>
                <pre>{error}</pre>
                
                <p><strong>Action Required:</strong> Please check the system logs and resolve the issue.</p>
                <p>The scheduler will continue running and attempt the next scheduled execution.</p>
            </body>
            </html>
            """
            
            await self.email_service.send_notification(
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send job failure notification: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status information.
        
        Returns:
            Dictionary with scheduler status details
        """
        current_time = datetime.now(self.singapore_tz)
        
        status = {
            'running': self._running,
            'current_time_sgt': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'timezone': str(self.singapore_tz),
            'jobs': []
        }
        
        if self._running:
            for job in self.scheduler.get_jobs():
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                status['jobs'].append(job_info)
        
        return status
    
    async def run_forever(self) -> None:
        """Run the scheduler daemon forever."""
        await self.start()
        
        try:
            # Keep the scheduler running
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            await self.stop()


# Async context manager for scheduler
class SchedulerContext:
    """Async context manager for scheduler service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler_service = None
    
    async def __aenter__(self):
        self.scheduler_service = SchedulerService(self.config)
        await self.scheduler_service.start()
        return self.scheduler_service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.scheduler_service:
            await self.scheduler_service.stop()