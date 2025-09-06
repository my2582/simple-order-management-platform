#!/usr/bin/env python3
"""
Scheduler Daemon Management Script

This script provides daemon management capabilities for the Portfolio Management Scheduler.
It supports starting the scheduler as a background service with proper logging and process management.
"""

import os
import sys
import signal
import subprocess
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
import psutil


class SchedulerDaemon:
    """Daemon manager for the Portfolio Management Scheduler."""
    
    def __init__(self, project_root: Path = None):
        """
        Initialize the scheduler daemon manager.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.pid_file = self.project_root / "scheduler.pid"
        self.log_file = self.project_root / "logs" / "scheduler_daemon.log"
        self.error_log = self.project_root / "logs" / "scheduler_daemon_error.log"
        
        # Ensure logs directory exists
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
    
    def start(self, detach: bool = True) -> bool:
        """
        Start the scheduler daemon.
        
        Args:
            detach: Whether to run as detached daemon process
            
        Returns:
            True if started successfully, False otherwise
        """
        # Check if already running
        if self.is_running():
            self.logger.warning("Scheduler daemon is already running")
            return False
        
        try:
            if detach:
                # Start as detached daemon process
                self._start_daemon()
            else:
                # Start in foreground (for debugging)
                self._start_foreground()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler daemon: {e}")
            return False
    
    def stop(self, timeout: int = 30) -> bool:
        """
        Stop the scheduler daemon gracefully.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            self.logger.info("Scheduler daemon is not running")
            return True
        
        try:
            pid = self._get_pid()
            if not pid:
                return True
            
            self.logger.info(f"Stopping scheduler daemon (PID: {pid})")
            
            # Try graceful shutdown with SIGTERM
            try:
                process = psutil.Process(pid)
                process.terminate()
                
                # Wait for graceful shutdown
                for _ in range(timeout):
                    if not process.is_running():
                        self.logger.info("Scheduler daemon stopped gracefully")
                        self._remove_pid_file()
                        return True
                    time.sleep(1)
                
                # Force kill if still running
                self.logger.warning("Graceful shutdown timeout, forcing kill...")
                process.kill()
                self._remove_pid_file()
                return True
                
            except psutil.NoSuchProcess:
                # Process already dead
                self._remove_pid_file()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to stop scheduler daemon: {e}")
            return False
    
    def restart(self, timeout: int = 30) -> bool:
        """
        Restart the scheduler daemon.
        
        Args:
            timeout: Maximum time to wait for shutdown
            
        Returns:
            True if restarted successfully, False otherwise
        """
        self.logger.info("Restarting scheduler daemon...")
        
        if not self.stop(timeout):
            return False
        
        # Wait a moment before starting
        time.sleep(2)
        
        return self.start()
    
    def status(self) -> dict:
        """
        Get the current status of the scheduler daemon.
        
        Returns:
            Dictionary with status information
        """
        pid = self._get_pid()
        
        status = {
            'running': False,
            'pid': None,
            'uptime': None,
            'memory_usage': None,
            'cpu_percent': None,
            'log_file': str(self.log_file),
            'error_log': str(self.error_log),
            'pid_file': str(self.pid_file)
        }
        
        if pid:
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    status.update({
                        'running': True,
                        'pid': pid,
                        'uptime': time.time() - process.create_time(),
                        'memory_usage': process.memory_info().rss / 1024 / 1024,  # MB
                        'cpu_percent': process.cpu_percent()
                    })
                else:
                    # Stale PID file
                    self._remove_pid_file()
            except psutil.NoSuchProcess:
                # Stale PID file
                self._remove_pid_file()
        
        return status
    
    def is_running(self) -> bool:
        """
        Check if the scheduler daemon is currently running.
        
        Returns:
            True if running, False otherwise
        """
        pid = self._get_pid()
        if not pid:
            return False
        
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            # Clean up stale PID file
            self._remove_pid_file()
            return False
    
    def _start_daemon(self):
        """Start the scheduler as a detached daemon process."""
        # Change to project directory
        os.chdir(self.project_root)
        
        # Create the command to run
        cmd = [
            sys.executable, "-m", "simple_order_management_platform.cli",
            "start-scheduler"
        ]
        
        # Start as daemon process
        with open(self.log_file, 'a') as log_f, open(self.error_log, 'a') as err_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=err_f,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent
                cwd=self.project_root
            )
            
            # Save PID
            self._save_pid(process.pid)
            
            self.logger.info(f"Scheduler daemon started with PID: {process.pid}")
            
            # Give it a moment to start
            time.sleep(2)
            
            # Verify it's still running
            if not self.is_running():
                raise RuntimeError("Scheduler daemon failed to start (process died)")
    
    def _start_foreground(self):
        """Start the scheduler in foreground mode (for debugging)."""
        os.chdir(self.project_root)
        
        # Import and run directly
        try:
            from simple_order_management_platform.cli import app
            import asyncio
            from simple_order_management_platform.services.scheduler_service import SchedulerService
            from simple_order_management_platform.config import Config
            
            config = Config()
            scheduler_service = SchedulerService(config)
            
            # Save PID for foreground process too
            self._save_pid(os.getpid())
            
            self.logger.info("Starting scheduler in foreground mode...")
            asyncio.run(scheduler_service.run_forever())
            
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        finally:
            self._remove_pid_file()
    
    def _get_pid(self) -> int:
        """
        Get the PID from the PID file.
        
        Returns:
            PID if file exists and valid, None otherwise
        """
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None
    
    def _save_pid(self, pid: int):
        """
        Save PID to the PID file.
        
        Args:
            pid: Process ID to save
        """
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
    
    def _remove_pid_file(self):
        """Remove the PID file if it exists."""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def show_logs(self, lines: int = 50, follow: bool = False):
        """
        Show recent log entries.
        
        Args:
            lines: Number of lines to show
            follow: Whether to follow the log (tail -f mode)
        """
        if not self.log_file.exists():
            print("Log file does not exist yet.")
            return
        
        if follow:
            print(f"Following log file: {self.log_file} (Ctrl+C to stop)")
            try:
                # Use subprocess to tail the file
                subprocess.run(['tail', '-f', '-n', str(lines), str(self.log_file)])
            except KeyboardInterrupt:
                print("\nStopped following log.")
        else:
            try:
                with open(self.log_file, 'r') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    
                    print(f"Recent {len(recent_lines)} lines from {self.log_file}:")
                    print("-" * 80)
                    for line in recent_lines:
                        print(line.rstrip())
            except IOError as e:
                print(f"Error reading log file: {e}")


def main():
    """Main entry point for the daemon management script."""
    parser = argparse.ArgumentParser(
        description="Portfolio Management Scheduler Daemon Manager"
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'restart', 'status', 'logs'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--foreground', '-f',
        action='store_true',
        help='Run in foreground mode (for debugging)'
    )
    
    parser.add_argument(
        '--lines', '-n',
        type=int,
        default=50,
        help='Number of log lines to show (default: 50)'
    )
    
    parser.add_argument(
        '--follow',
        action='store_true',
        help='Follow log file (tail -f mode)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Timeout for stop/restart operations (default: 30s)'
    )
    
    args = parser.parse_args()
    
    # Create daemon manager
    daemon = SchedulerDaemon()
    
    if args.action == 'start':
        print("Starting Portfolio Management Scheduler daemon...")
        
        if daemon.start(detach=not args.foreground):
            if args.foreground:
                print("Scheduler started in foreground mode.")
            else:
                status = daemon.status()
                print(f"✅ Scheduler daemon started successfully (PID: {status['pid']})")
                print(f"Log file: {status['log_file']}")
        else:
            print("❌ Failed to start scheduler daemon")
            sys.exit(1)
    
    elif args.action == 'stop':
        print("Stopping Portfolio Management Scheduler daemon...")
        
        if daemon.stop(timeout=args.timeout):
            print("✅ Scheduler daemon stopped successfully")
        else:
            print("❌ Failed to stop scheduler daemon")
            sys.exit(1)
    
    elif args.action == 'restart':
        print("Restarting Portfolio Management Scheduler daemon...")
        
        if daemon.restart(timeout=args.timeout):
            status = daemon.status()
            print(f"✅ Scheduler daemon restarted successfully (PID: {status['pid']})")
        else:
            print("❌ Failed to restart scheduler daemon")
            sys.exit(1)
    
    elif args.action == 'status':
        status = daemon.status()
        
        print("Portfolio Management Scheduler Status:")
        print("-" * 50)
        
        if status['running']:
            uptime_hours = status['uptime'] / 3600 if status['uptime'] else 0
            print(f"Status: 🟢 RUNNING")
            print(f"PID: {status['pid']}")
            print(f"Uptime: {uptime_hours:.1f} hours")
            print(f"Memory Usage: {status['memory_usage']:.1f} MB")
            print(f"CPU Usage: {status['cpu_percent']:.1f}%")
        else:
            print(f"Status: 🔴 NOT RUNNING")
        
        print(f"Log File: {status['log_file']}")
        print(f"Error Log: {status['error_log']}")
        print(f"PID File: {status['pid_file']}")
    
    elif args.action == 'logs':
        daemon.show_logs(lines=args.lines, follow=args.follow)


if __name__ == '__main__':
    main()