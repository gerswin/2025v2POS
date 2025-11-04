#!/bin/bash
# Install Tiquemax POS Podman Pod as a systemd service
# This enables automatic startup on system boot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if pod exists
if ! podman pod exists tiquemax-pos; then
    log_error "Pod 'tiquemax-pos' does not exist!"
    log_info "Create it first with: cd ../.. && ./deployment/podman/create-pod.sh"
    exit 1
fi

log_info "Installing Tiquemax POS systemd service..."

# Determine systemd directory
if [ -d "$HOME/.config/systemd/user" ] || [ "$EUID" -ne 0 ]; then
    # User service (rootless)
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    SYSTEMCTL="systemctl --user"
    log_info "Installing as user service (rootless)"

    # Enable linger for user to keep services running after logout
    loginctl enable-linger "$USER" 2>/dev/null || log_warning "Could not enable linger (may require sudo)"
else
    # System service
    SYSTEMD_DIR="/etc/systemd/system"
    SYSTEMCTL="systemctl"
    log_info "Installing as system service"

    if [ "$EUID" -ne 0 ]; then
        log_error "System service installation requires root privileges"
        log_info "Run with: sudo $0"
        exit 1
    fi
fi

# Create systemd directory if it doesn't exist
mkdir -p "$SYSTEMD_DIR"

# Copy service file
log_info "Copying service file..."
cp tiquemax-pod.service "$SYSTEMD_DIR/"

# Reload systemd
log_info "Reloading systemd daemon..."
$SYSTEMCTL daemon-reload

# Enable service
log_info "Enabling service..."
$SYSTEMCTL enable tiquemax-pod.service

log_success "Service installed successfully!"
echo ""
log_info "Service management commands:"
echo "  Start:   $SYSTEMCTL start tiquemax-pod"
echo "  Stop:    $SYSTEMCTL stop tiquemax-pod"
echo "  Restart: $SYSTEMCTL restart tiquemax-pod"
echo "  Status:  $SYSTEMCTL status tiquemax-pod"
echo "  Logs:    journalctl --user -u tiquemax-pod -f"
echo ""
log_info "The service will automatically start on system boot"
echo ""
log_warning "Note: The pod must be created before the service can start"
log_info "Current pod status:"
podman pod ps --filter name=tiquemax-pos
