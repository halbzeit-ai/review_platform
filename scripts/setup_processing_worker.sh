#!/bin/bash

# Setup Processing Worker Service
# This script installs and manages the systemd service for the robust processing queue worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/processing-worker.service"
SYSTEMD_PATH="/etc/systemd/system/processing-worker.service"

echo "=== Processing Worker Service Setup ==="

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install   - Install and enable the processing worker service"
    echo "  start     - Start the processing worker service"
    echo "  stop      - Stop the processing worker service"
    echo "  restart   - Restart the processing worker service"
    echo "  status    - Show service status"
    echo "  logs      - Show service logs"
    echo "  remove    - Remove the service"
    echo ""
}

# Function to install service
install_service() {
    echo "Installing processing worker service..."
    
    # Check if service file exists
    if [[ ! -f "$SERVICE_FILE" ]]; then
        echo "❌ Service file not found: $SERVICE_FILE"
        exit 1
    fi
    
    # Copy service file
    sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"
    echo "✅ Service file installed to $SYSTEMD_PATH"
    
    # Reload systemd
    sudo systemctl daemon-reload
    echo "✅ Systemd daemon reloaded"
    
    # Enable service
    sudo systemctl enable processing-worker.service
    echo "✅ Processing worker service enabled"
    
    echo "🎉 Processing worker service installed successfully!"
    echo "Use 'sudo systemctl start processing-worker' to start the service"
}

# Function to start service
start_service() {
    echo "Starting processing worker service..."
    sudo systemctl start processing-worker.service
    echo "✅ Processing worker service started"
    show_status
}

# Function to stop service
stop_service() {
    echo "Stopping processing worker service..."
    sudo systemctl stop processing-worker.service
    echo "✅ Processing worker service stopped"
}

# Function to restart service
restart_service() {
    echo "Restarting processing worker service..."
    sudo systemctl restart processing-worker.service
    echo "✅ Processing worker service restarted"
    show_status
}

# Function to show status
show_status() {
    echo "Processing worker service status:"
    sudo systemctl status processing-worker.service --no-pager
}

# Function to show logs
show_logs() {
    echo "Processing worker service logs (last 50 lines):"
    sudo journalctl -u processing-worker.service -n 50 --no-pager
    echo ""
    echo "To follow logs in real-time: sudo journalctl -u processing-worker.service -f"
}

# Function to remove service
remove_service() {
    echo "Removing processing worker service..."
    
    # Stop service if running
    sudo systemctl stop processing-worker.service 2>/dev/null || true
    
    # Disable service
    sudo systemctl disable processing-worker.service 2>/dev/null || true
    
    # Remove service file
    sudo rm -f "$SYSTEMD_PATH"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    echo "✅ Processing worker service removed"
}

# Main script logic
case "${1:-}" in
    "install")
        install_service
        ;;
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "remove")
        remove_service
        ;;
    *)
        show_usage
        exit 1
        ;;
esac