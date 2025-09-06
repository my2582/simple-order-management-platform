#!/bin/bash

# Portfolio Management Scheduler Deployment Script
# This script sets up the scheduler service for production deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_NAME="simple-order-management-platform"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
SERVICE_NAME="portfolio-scheduler"

# Functions
print_header() {
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}Portfolio Management Scheduler Deployment${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

check_requirements() {
    print_info "Checking system requirements..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_success "Python version: $python_version"
    
    # Check if project virtual environment exists
    if [ ! -d "$PROJECT_ROOT/venv" ] && [ ! -d "$PROJECT_ROOT/.venv" ]; then
        print_warning "Virtual environment not found. Consider creating one."
        print_info "To create: python3 -m venv venv && source venv/bin/activate"
    fi
    
    # Check required Python packages
    if ! python3 -c "import apscheduler, pytz" &> /dev/null; then
        print_error "Required packages not installed. Run: pip install -r requirements.txt"
        exit 1
    fi
    
    print_success "All requirements met"
}

setup_directories() {
    print_info "Setting up directories..."
    
    # Create logs directory
    mkdir -p "$LOGS_DIR"
    print_success "Created logs directory: $LOGS_DIR"
    
    # Create data directories if they don't exist
    mkdir -p "$PROJECT_ROOT/data/output"
    mkdir -p "$PROJECT_ROOT/data/market_data_cache"
    print_success "Created data directories"
    
    # Set proper permissions
    chmod 755 "$LOGS_DIR"
    chmod 755 "$PROJECT_ROOT/data"
    
    print_success "Directory setup complete"
}

install_systemd_service() {
    print_info "Setting up systemd service..."
    
    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        print_warning "Systemd service installation requires root privileges"
        print_info "You can install it manually later with:"
        print_info "sudo cp $SCRIPT_DIR/portfolio-scheduler.service /etc/systemd/system/"
        print_info "sudo systemctl daemon-reload"
        print_info "sudo systemctl enable portfolio-scheduler"
        return 0
    fi
    
    # Get current user info for service file
    REAL_USER=${SUDO_USER:-$USER}
    USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    USER_GROUP=$(id -gn "$REAL_USER")
    
    # Create customized service file
    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Portfolio Management Scheduler
Documentation=https://github.com/your-org/simple-order-management-platform
After=network.target
Wants=network.target

[Service]
Type=simple
User=$REAL_USER
Group=$USER_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 -m simple_order_management_platform.cli start-scheduler
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=append:$LOGS_DIR/scheduler.log
StandardError=append:$LOGS_DIR/scheduler_error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_ROOT $USER_HOME/Library/CloudStorage
ProtectHome=read-only
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
MemoryMax=1G
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    print_success "Systemd service installed and enabled"
    print_info "Service file: $SERVICE_FILE"
    print_info "To start: sudo systemctl start $SERVICE_NAME"
    print_info "To check status: sudo systemctl status $SERVICE_NAME"
    print_info "To view logs: sudo journalctl -u $SERVICE_NAME -f"
}

create_cron_alternative() {
    print_info "Setting up cron-based alternative scheduler..."
    
    # Create a simple cron script
    CRON_SCRIPT="$SCRIPT_DIR/run_daily_updates.sh"
    
    cat > "$CRON_SCRIPT" << 'EOF'
#!/bin/bash

# Daily Portfolio Updates Cron Script
# This script runs the scheduled tasks at specified times

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/cron_scheduler.log"

# Ensure logs directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Change to project directory
cd "$PROJECT_ROOT"

# Determine which task to run based on time
current_hour=$(date '+%H')
current_minute=$(date '+%M')

# Market data update at 06:00 SGT
if [ "$current_hour" = "06" ] && [ "$current_minute" = "00" ]; then
    log_message "Starting market data update"
    python3 -m simple_order_management_platform.cli update-market-data >> "$LOG_FILE" 2>&1
    log_message "Market data update completed"

# Portfolio update at 06:30 SGT
elif [ "$current_hour" = "06" ] && [ "$current_minute" = "30" ]; then
    log_message "Starting daily portfolio update"
    python3 -m simple_order_management_platform.cli run-daily-update >> "$LOG_FILE" 2>&1
    log_message "Daily portfolio update completed"
fi
EOF

    chmod +x "$CRON_SCRIPT"
    
    print_success "Created cron alternative script: $CRON_SCRIPT"
    print_info "To use with cron, add these lines to crontab (crontab -e):"
    print_info "0 6 * * * $CRON_SCRIPT  # Market data update"
    print_info "30 6 * * * $CRON_SCRIPT  # Portfolio update"
    print_info "Note: Adjust timezone as needed for your system"
}

test_installation() {
    print_info "Testing installation..."
    
    # Test configuration loading
    if python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from simple_order_management_platform.config import Config
config = Config()
print('✅ Configuration loaded successfully')
print(f'Market data update: {config.app[\"scheduling\"][\"market_data_update\"]} SGT')
print(f'Portfolio update: {config.app[\"scheduling\"][\"portfolio_update\"]} SGT')
"; then
        print_success "Configuration test passed"
    else
        print_error "Configuration test failed"
        return 1
    fi
    
    # Test CLI commands
    if python3 -m simple_order_management_platform.cli test-scheduler; then
        print_success "Scheduler component test passed"
    else
        print_error "Scheduler component test failed"
        return 1
    fi
    
    print_success "Installation test completed"
}

show_usage_instructions() {
    print_info "Deployment completed! Usage instructions:"
    echo
    echo "🔧 Manual Management (using daemon script):"
    echo "  Start:   $SCRIPT_DIR/scheduler_daemon.py start"
    echo "  Stop:    $SCRIPT_DIR/scheduler_daemon.py stop"
    echo "  Status:  $SCRIPT_DIR/scheduler_daemon.py status"
    echo "  Logs:    $SCRIPT_DIR/scheduler_daemon.py logs"
    echo
    
    if systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
        echo "🔧 Systemd Service Management:"
        echo "  Start:   sudo systemctl start $SERVICE_NAME"
        echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
        echo "  Status:  sudo systemctl status $SERVICE_NAME"
        echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
        echo
    fi
    
    echo "📊 CLI Commands:"
    echo "  Test:           python3 -m simple_order_management_platform.cli test-scheduler"
    echo "  Test integrations: python3 -m simple_order_management_platform.cli test-integrations"
    echo "  Manual update:  python3 -m simple_order_management_platform.cli run-daily-update"
    echo "  Market data:    python3 -m simple_order_management_platform.cli update-market-data"
    echo "  Status check:   python3 -m simple_order_management_platform.cli scheduler-status"
    echo
    
    echo "📁 Important Paths:"
    echo "  Project root:   $PROJECT_ROOT"
    echo "  Logs directory: $LOGS_DIR"
    echo "  Config file:    $PROJECT_ROOT/config/app.yaml"
    echo
    
    print_info "The scheduler will run the following tasks automatically:"
    print_info "• Market data update: 6:00 AM SGT daily"
    print_info "• Portfolio update: 6:30 AM SGT daily"
    print_info "• All outputs saved to SharePoint and emailed automatically"
}

# Main deployment flow
main() {
    print_header
    
    print_info "Project root: $PROJECT_ROOT"
    print_info "Script directory: $SCRIPT_DIR"
    echo
    
    # Run deployment steps
    check_requirements
    echo
    
    setup_directories
    echo
    
    # Ask user about installation method
    echo "Choose installation method:"
    echo "1) Install as systemd service (recommended for production)"
    echo "2) Use manual daemon management only"
    echo "3) Set up cron-based alternative"
    echo "4) All of the above"
    
    read -p "Enter choice (1-4): " choice
    echo
    
    case $choice in
        1)
            install_systemd_service
            ;;
        2)
            print_info "Systemd service installation skipped"
            ;;
        3)
            create_cron_alternative
            ;;
        4)
            install_systemd_service
            echo
            create_cron_alternative
            ;;
        *)
            print_warning "Invalid choice, skipping service installation"
            ;;
    esac
    
    echo
    test_installation
    echo
    
    show_usage_instructions
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"