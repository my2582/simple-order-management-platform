# Portfolio Management Scheduler Guide

## Overview

The Portfolio Management Scheduler provides automated daily updates for portfolio positions and market data using Singapore timezone (SGT) scheduling. This system eliminates the need for manual intervention while ensuring timely and reliable portfolio reports.

## 🎯 Goals Completed

### ✅ Goal 4: Singapore Timezone Scheduling System

The scheduler implements:
- **Market Data Updates**: Daily at 6:00 AM SGT
- **Portfolio Position Updates**: Daily at 6:30 AM SGT  
- **Automated Workflows**: Complete integration with IBKR, SharePoint, and Email
- **Error Handling**: Comprehensive notification system for failures
- **Role-based Access**: Trade Assistant for market data, Portfolio Manager for positions

## 🏗️ System Architecture

### Core Components

1. **SchedulerService** (`scheduler_service.py`)
   - APScheduler-based Singapore timezone scheduling
   - Async job execution with error handling
   - Email notifications for job status

2. **CLI Integration** (`cli.py`)
   - `start-scheduler`: Start daemon process
   - `scheduler-status`: Check scheduler status  
   - `test-scheduler`: Validate scheduler components
   - `run-daily-update`: Manual workflow execution
   - `update-market-data`: Manual market data updates

3. **Daemon Management** (`scheduler_daemon.py`)
   - Process lifecycle management
   - PID file handling
   - Log file management
   - Graceful shutdown handling

4. **Deployment Scripts**
   - `deploy_scheduler.sh`: Production deployment
   - `portfolio-scheduler.service`: Systemd integration
   - Alternative cron-based scheduling

## ⏰ Schedule Configuration

The scheduler runs according to Singapore timezone (Asia/Singapore):

```yaml
# config/app.yaml
scheduling:
  timezone: "Asia/Singapore"
  market_data_update: "06:00"  # Daily at 6:00 AM SGT
  portfolio_update: "06:30"    # Daily at 6:30 AM SGT
```

### Daily Workflow Sequence

1. **6:00 AM SGT**: Market Data Update
   - Uses Trade Assistant role (market data access only)
   - Updates cached prices for all instruments
   - Generates market data report
   - Saves to SharePoint with date-organized folders

2. **6:30 AM SGT**: Portfolio Position Update  
   - Uses Portfolio Manager role (full access)
   - Downloads positions using cached prices (offline operation)
   - Generates IBKR standard format Excel reports
   - Applies asset class mapping from universe data
   - Uploads to SharePoint in daily folders
   - Sends email notification with attachments

## 🚀 Installation & Deployment

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Deployment Script**
   ```bash
   ./scripts/deploy_scheduler.sh
   ```

3. **Start Scheduler**
   ```bash
   # Method 1: CLI daemon
   python3 -m simple_order_management_platform.cli start-scheduler
   
   # Method 2: Daemon script
   ./scripts/scheduler_daemon.py start
   
   # Method 3: Systemd service (if installed)
   sudo systemctl start portfolio-scheduler
   ```

### Production Deployment Options

#### Option 1: Systemd Service (Recommended)

```bash
# Deploy with systemd integration
sudo ./scripts/deploy_scheduler.sh

# Manage service
sudo systemctl start portfolio-scheduler
sudo systemctl stop portfolio-scheduler
sudo systemctl status portfolio-scheduler
sudo systemctl enable portfolio-scheduler  # Auto-start on boot

# View logs
sudo journalctl -u portfolio-scheduler -f
```

#### Option 2: Manual Daemon Management

```bash
# Start daemon
./scripts/scheduler_daemon.py start

# Check status
./scripts/scheduler_daemon.py status

# View logs
./scripts/scheduler_daemon.py logs --follow

# Stop daemon
./scripts/scheduler_daemon.py stop
```

#### Option 3: Cron-based Alternative

```bash
# Set up cron alternative
./scripts/deploy_scheduler.sh
# Choose option 3 or 4

# Add to crontab manually
crontab -e
# Add these lines:
0 6 * * * /path/to/project/scripts/run_daily_updates.sh
30 6 * * * /path/to/project/scripts/run_daily_updates.sh
```

## 🛠️ CLI Commands

### Scheduler Management

```bash
# Start the scheduler daemon
python3 -m simple_order_management_platform.cli start-scheduler

# Check scheduler status and next run times
python3 -m simple_order_management_platform.cli scheduler-status

# Test scheduler components
python3 -m simple_order_management_platform.cli test-scheduler

# Test all system integrations
python3 -m simple_order_management_platform.cli test-integrations
```

### Manual Operations

```bash
# Run complete daily update workflow manually
python3 -m simple_order_management_platform.cli run-daily-update

# Update market data cache only
python3 -m simple_order_management_platform.cli update-market-data

# Check market data cache status
python3 -m simple_order_management_platform.cli market-data-status

# Download positions using cached prices (offline)
python3 -m simple_order_management_platform.cli download-positions-cached

# Download positions with live prices (online)
python3 -m simple_order_management_platform.cli download-positions-ibkr
```

## 📊 Monitoring & Logging

### Log Files

- **Scheduler Daemon**: `logs/scheduler_daemon.log`
- **Scheduler Errors**: `logs/scheduler_daemon_error.log`
- **Application Logs**: Console output and service-specific logs
- **Systemd Logs**: `journalctl -u portfolio-scheduler`

### Status Monitoring

```bash
# Check daemon status
./scripts/scheduler_daemon.py status
# Output:
# Status: 🟢 RUNNING
# PID: 12345
# Uptime: 24.5 hours
# Memory Usage: 156.3 MB
# CPU Usage: 0.2%

# Check schedule status
python3 -m simple_order_management_platform.cli scheduler-status
# Shows current SGT time, next scheduled runs, and job configuration
```

### Email Notifications

The scheduler automatically sends email notifications for:

- **Startup/Shutdown**: Scheduler daemon lifecycle events
- **Job Success**: Successful completion with execution details
- **Job Failure**: Error notifications with detailed error messages
- **Daily Reports**: Portfolio and market data reports as attachments

Email configuration in `config/app.yaml`:
```yaml
email:
  sender: "minsu.yeom@arkifinance.com"
  recipient: "minsu.yeom@arkifinance.com"
  smtp_server: "smtp.office365.com"
  smtp_port: 587
  use_tls: true
```

## 🔧 Configuration

### Environment Requirements

- **Python**: 3.8+ with required packages
- **IBKR TWS/Gateway**: Running and accessible
- **SharePoint**: OneDrive sync configured
- **Email**: Office 365 SMTP access configured

### Key Configuration Files

1. **config/app.yaml**: Main application configuration
2. **config/universes/**: Asset class mapping files
3. **data/model_portfolios/**: Portfolio definition files
4. **requirements.txt**: Python dependencies

### Role-based Configuration

```yaml
ibkr_profiles:
  trade_assistant:
    description: "Trade Assistant - Market data access only"
    permissions:
      - "market_data"
      - "price_download"
      
  portfolio_manager:
    description: "Portfolio Manager - Full trading access"  
    permissions:
      - "portfolio_download"
      - "account_summary"
```

## 🚨 Troubleshooting

### Common Issues

#### Scheduler Not Starting
```bash
# Check configuration
python3 -m simple_order_management_platform.cli test-scheduler

# Check logs
./scripts/scheduler_daemon.py logs

# Verify dependencies
pip install -r requirements.txt
```

#### IBKR Connection Issues
```bash
# Test IBKR connectivity
python3 -m simple_order_management_platform.cli test-integrations

# Check TWS/Gateway status
# Ensure correct host/port in config/app.yaml
```

#### SharePoint Upload Failures
```bash
# Check SharePoint directory configuration
ls -la "/Users/msyeom/Library/CloudStorage/OneDrive-SharedLibraries-OPTIMALVEST.AIPTE.LTD/Arki Investment - Trading"

# Verify OneDrive sync status
# Check directory permissions
```

#### Email Notification Issues
```bash
# Test email configuration
python3 -c "
from simple_order_management_platform.config import Config
from simple_order_management_platform.integrations.email import EmailService
config = Config()
email_service = EmailService(config)
# Test email sending
"
```

### Performance Tuning

- **Memory Usage**: Monitor with `scheduler_daemon.py status`
- **Execution Time**: Check log timestamps for slow operations
- **Cache Optimization**: Use cached prices for faster portfolio operations
- **Resource Limits**: Configure in systemd service file

### Backup & Recovery

- **Configuration Backup**: Version control config files
- **Data Backup**: Regular backup of data/ directory
- **Log Rotation**: Implement log rotation for long-term operation
- **Disaster Recovery**: Document restore procedures

## 📈 Integration with Overall System

The scheduler completes the comprehensive portfolio management platform:

1. **Goal 1 ✅**: Daily automated portfolio updates → **COMPLETED**
2. **Goal 2 ✅**: Order generation system → **COMPLETED** 
3. **Goal 3 ✅**: Market data platform separation → **COMPLETED**
4. **Goal 4 ✅**: Singapore timezone scheduling → **COMPLETED**

### Key Features Delivered

- ✅ IBKR standard Excel format exports
- ✅ Automated SharePoint integration
- ✅ Email notifications with attachments  
- ✅ Role-based access control
- ✅ Cached pricing system for offline operations
- ✅ Asset class mapping and classification
- ✅ Singapore timezone automation
- ✅ Comprehensive error handling and notifications
- ✅ Production-ready deployment scripts
- ✅ Multiple deployment options (systemd, daemon, cron)

## 🔗 Related Documentation

- [README.md](../README.md): Project overview and setup
- [Architecture Guide](./ARCHITECTURE.md): System architecture details
- [API Documentation](./API.md): Service interfaces and models
- [Configuration Guide](./CONFIGURATION.md): Detailed configuration options

---

## Support

For issues or questions about the scheduler system:
1. Check this guide and troubleshooting section
2. Review application logs
3. Test individual components using CLI commands
4. Contact system administrator

The Portfolio Management Scheduler provides robust, automated daily operations for professional portfolio management with minimal manual intervention required.