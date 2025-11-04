#!/bin/bash

# Venezuelan POS System Monitoring Setup Script
# This script sets up comprehensive monitoring with Prometheus and Grafana

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Venezuelan POS System Monitoring Setup${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Configuration
MONITORING_DIR="monitoring"
PROMETHEUS_VERSION="2.45.0"
GRAFANA_VERSION="10.0.0"
NODE_EXPORTER_VERSION="1.6.0"

# Create monitoring directory structure
echo -e "${YELLOW}Creating monitoring directory structure...${NC}"
mkdir -p "$MONITORING_DIR"/{prometheus,grafana,exporters,logs}
mkdir -p "$MONITORING_DIR"/grafana/{dashboards,provisioning/{dashboards,datasources}}

# Function to download and setup Prometheus
setup_prometheus() {
    echo -e "${YELLOW}Setting up Prometheus...${NC}"
    
    if [ ! -f "$MONITORING_DIR/prometheus/prometheus" ]; then
        echo "Downloading Prometheus $PROMETHEUS_VERSION..."
        
        # Detect OS and architecture
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        ARCH=$(uname -m)
        
        case $ARCH in
            x86_64) ARCH="amd64" ;;
            arm64|aarch64) ARCH="arm64" ;;
            *) echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
        esac
        
        PROMETHEUS_URL="https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.${OS}-${ARCH}.tar.gz"
        
        curl -L "$PROMETHEUS_URL" | tar -xz -C "$MONITORING_DIR/prometheus" --strip-components=1
        
        echo -e "${GREEN}✓ Prometheus downloaded and extracted${NC}"
    else
        echo -e "${GREEN}✓ Prometheus already installed${NC}"
    fi
    
    # Copy configuration
    cp "$MONITORING_DIR/prometheus.yml" "$MONITORING_DIR/prometheus/"
    cp "$MONITORING_DIR/alert_rules.yml" "$MONITORING_DIR/prometheus/"
    
    echo -e "${GREEN}✓ Prometheus configuration copied${NC}"
}

# Function to setup Grafana
setup_grafana() {
    echo -e "${YELLOW}Setting up Grafana...${NC}"
    
    # Create Grafana configuration
    cat > "$MONITORING_DIR/grafana/grafana.ini" << EOF
[server]
http_port = 3000
domain = localhost

[database]
type = sqlite3
path = grafana.db

[security]
admin_user = admin
admin_password = admin123

[users]
allow_sign_up = false

[auth.anonymous]
enabled = false

[dashboards]
default_home_dashboard_path = /var/lib/grafana/dashboards/venezuelan-pos-dashboard.json
EOF
    
    # Create datasource configuration
    cat > "$MONITORING_DIR/grafana/provisioning/datasources/prometheus.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: true
EOF
    
    # Create dashboard provisioning configuration
    cat > "$MONITORING_DIR/grafana/provisioning/dashboards/dashboards.yml" << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF
    
    # Copy dashboard
    cp "$MONITORING_DIR/grafana_dashboard.json" "$MONITORING_DIR/grafana/dashboards/venezuelan-pos-dashboard.json"
    
    echo -e "${GREEN}✓ Grafana configuration created${NC}"
}

# Function to setup Node Exporter
setup_node_exporter() {
    echo -e "${YELLOW}Setting up Node Exporter...${NC}"
    
    if [ ! -f "$MONITORING_DIR/exporters/node_exporter" ]; then
        echo "Downloading Node Exporter $NODE_EXPORTER_VERSION..."
        
        # Detect OS and architecture
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        ARCH=$(uname -m)
        
        case $ARCH in
            x86_64) ARCH="amd64" ;;
            arm64|aarch64) ARCH="arm64" ;;
            *) echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
        esac
        
        NODE_EXPORTER_URL="https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.${OS}-${ARCH}.tar.gz"
        
        curl -L "$NODE_EXPORTER_URL" | tar -xz -C "$MONITORING_DIR/exporters" --strip-components=1
        
        echo -e "${GREEN}✓ Node Exporter downloaded and extracted${NC}"
    else
        echo -e "${GREEN}✓ Node Exporter already installed${NC}"
    fi
}

# Function to create startup scripts
create_startup_scripts() {
    echo -e "${YELLOW}Creating startup scripts...${NC}"
    
    # Prometheus startup script
    cat > "$MONITORING_DIR/start_prometheus.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/prometheus"
./prometheus \
    --config.file=prometheus.yml \
    --storage.tsdb.path=data \
    --web.console.templates=consoles \
    --web.console.libraries=console_libraries \
    --web.enable-lifecycle \
    --log.level=info
EOF
    
    # Node Exporter startup script
    cat > "$MONITORING_DIR/start_node_exporter.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/exporters"
./node_exporter \
    --web.listen-address=:9100 \
    --log.level=info
EOF
    
    # Grafana startup script (Docker-based)
    cat > "$MONITORING_DIR/start_grafana.sh" << 'EOF'
#!/bin/bash
MONITORING_DIR="$(dirname "$0")"

if command -v docker &> /dev/null; then
    docker run -d \
        --name grafana-venezuelan-pos \
        -p 3000:3000 \
        -v "$PWD/$MONITORING_DIR/grafana/grafana.ini:/etc/grafana/grafana.ini" \
        -v "$PWD/$MONITORING_DIR/grafana/provisioning:/etc/grafana/provisioning" \
        -v "$PWD/$MONITORING_DIR/grafana/dashboards:/var/lib/grafana/dashboards" \
        grafana/grafana:latest
    
    echo "Grafana started on http://localhost:3000"
    echo "Default credentials: admin/admin123"
else
    echo "Docker not found. Please install Docker to run Grafana."
    echo "Alternatively, install Grafana directly: https://grafana.com/docs/grafana/latest/installation/"
fi
EOF
    
    # Master startup script
    cat > "$MONITORING_DIR/start_monitoring.sh" << 'EOF'
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Venezuelan POS System Monitoring${NC}"
echo -e "${BLUE}=========================================${NC}"

# Start Node Exporter
echo -e "${YELLOW}Starting Node Exporter...${NC}"
./start_node_exporter.sh > logs/node_exporter.log 2>&1 &
NODE_EXPORTER_PID=$!
echo "Node Exporter PID: $NODE_EXPORTER_PID"

# Wait a moment
sleep 2

# Start Prometheus
echo -e "${YELLOW}Starting Prometheus...${NC}"
./start_prometheus.sh > logs/prometheus.log 2>&1 &
PROMETHEUS_PID=$!
echo "Prometheus PID: $PROMETHEUS_PID"

# Wait a moment
sleep 5

# Start Grafana
echo -e "${YELLOW}Starting Grafana...${NC}"
./start_grafana.sh

echo ""
echo -e "${GREEN}Monitoring stack started successfully!${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000 (admin/admin123)"
echo "  Node Exporter: http://localhost:9100"
echo ""
echo -e "${BLUE}Log files:${NC}"
echo "  Prometheus: logs/prometheus.log"
echo "  Node Exporter: logs/node_exporter.log"
echo ""
echo "To stop monitoring, run: ./stop_monitoring.sh"

# Save PIDs for cleanup
echo "$NODE_EXPORTER_PID" > logs/node_exporter.pid
echo "$PROMETHEUS_PID" > logs/prometheus.pid
EOF
    
    # Stop script
    cat > "$MONITORING_DIR/stop_monitoring.sh" << 'EOF'
#!/bin/bash

echo "Stopping Venezuelan POS System Monitoring..."

# Stop Grafana (Docker)
if docker ps | grep -q grafana-venezuelan-pos; then
    docker stop grafana-venezuelan-pos
    docker rm grafana-venezuelan-pos
    echo "Grafana stopped"
fi

# Stop Prometheus
if [ -f logs/prometheus.pid ]; then
    PROMETHEUS_PID=$(cat logs/prometheus.pid)
    if kill -0 "$PROMETHEUS_PID" 2>/dev/null; then
        kill "$PROMETHEUS_PID"
        echo "Prometheus stopped (PID: $PROMETHEUS_PID)"
    fi
    rm -f logs/prometheus.pid
fi

# Stop Node Exporter
if [ -f logs/node_exporter.pid ]; then
    NODE_EXPORTER_PID=$(cat logs/node_exporter.pid)
    if kill -0 "$NODE_EXPORTER_PID" 2>/dev/null; then
        kill "$NODE_EXPORTER_PID"
        echo "Node Exporter stopped (PID: $NODE_EXPORTER_PID)"
    fi
    rm -f logs/node_exporter.pid
fi

echo "Monitoring stack stopped"
EOF
    
    # Make scripts executable
    chmod +x "$MONITORING_DIR"/*.sh
    
    echo -e "${GREEN}✓ Startup scripts created${NC}"
}

# Function to create monitoring documentation
create_documentation() {
    echo -e "${YELLOW}Creating monitoring documentation...${NC}"
    
    cat > "$MONITORING_DIR/README.md" << 'EOF'
# Venezuelan POS System Monitoring

This directory contains the complete monitoring setup for the Venezuelan POS System using Prometheus and Grafana.

## Quick Start

1. **Start the monitoring stack:**
   ```bash
   cd monitoring
   ./start_monitoring.sh
   ```

2. **Access the dashboards:**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin123)

3. **Stop the monitoring stack:**
   ```bash
   ./stop_monitoring.sh
   ```

## Components

### Prometheus (Port 9090)
- Metrics collection and storage
- Alerting rules for performance and business metrics
- Scrapes metrics from Django application on port 8001

### Grafana (Port 3000)
- Visualization dashboards
- Pre-configured Venezuelan POS dashboard
- Default credentials: admin/admin123

### Node Exporter (Port 9100)
- System metrics (CPU, memory, disk, network)
- Automatically scraped by Prometheus

## Metrics Available

### Application Metrics
- `venezuelan_pos_ticket_sales_total` - Total tickets sold
- `venezuelan_pos_revenue_total` - Total revenue generated
- `venezuelan_pos_payment_processing_duration_seconds` - Payment processing time
- `venezuelan_pos_stage_transitions_total` - Pricing stage transitions
- `venezuelan_pos_notification_delivery_duration_seconds` - Notification delivery time
- `venezuelan_pos_database_query_duration_seconds` - Database query time
- `venezuelan_pos_cache_operations_total` - Cache operations
- `venezuelan_pos_fiscal_series_generated_total` - Fiscal series generated
- `venezuelan_pos_active_users` - Currently active users

### Django Metrics
- `django_http_requests_total` - HTTP requests
- `django_http_requests_latency_seconds` - Request latency
- `django_db_connections_total` - Database connections

### System Metrics (via Node Exporter)
- CPU usage, memory usage, disk space
- Network I/O, disk I/O
- System load averages

## Alerting

Prometheus includes alerting rules for:
- High response times (>500ms warning, >1s critical)
- High error rates (>5% warning, >10% critical)
- Database performance issues
- Low cache hit rates
- Business metric anomalies
- System resource usage

## Configuration Files

- `prometheus.yml` - Prometheus configuration
- `alert_rules.yml` - Alerting rules
- `grafana_dashboard.json` - Grafana dashboard definition
- `grafana/grafana.ini` - Grafana configuration

## Troubleshooting

### Prometheus not starting
- Check logs: `tail -f logs/prometheus.log`
- Verify configuration: `./prometheus/prometheus --config.file=prometheus.yml --config.check`

### Grafana not accessible
- Check if Docker is running: `docker ps`
- Check container logs: `docker logs grafana-venezuelan-pos`

### No metrics appearing
- Verify Django app is running on port 8000
- Check if metrics endpoint is accessible: `curl http://localhost:8001/metrics`
- Verify Prometheus targets: http://localhost:9090/targets

### Performance Issues
- Increase Prometheus retention if needed
- Adjust scrape intervals in prometheus.yml
- Monitor system resources with Node Exporter metrics

## Customization

### Adding New Metrics
1. Add metric definitions in `venezuelan_pos/core/monitoring.py`
2. Update Prometheus configuration if needed
3. Create new dashboard panels in Grafana

### Custom Alerts
1. Edit `alert_rules.yml`
2. Reload Prometheus configuration: `curl -X POST http://localhost:9090/-/reload`

### Dashboard Modifications
1. Edit dashboards in Grafana UI
2. Export JSON and save to `grafana_dashboard.json`
3. Restart Grafana to apply changes
EOF
    
    echo -e "${GREEN}✓ Documentation created${NC}"
}

# Main execution
echo -e "${YELLOW}This script will set up comprehensive monitoring for the Venezuelan POS System${NC}"
echo -e "${YELLOW}Components: Prometheus, Grafana, Node Exporter${NC}"
echo ""

read -p "Continue with setup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Run setup functions
setup_prometheus
setup_node_exporter
setup_grafana
create_startup_scripts
create_documentation

echo ""
echo -e "${GREEN}✅ Monitoring setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Start the monitoring stack: cd monitoring && ./start_monitoring.sh"
echo "2. Configure your Django app to export metrics on port 8001"
echo "3. Access Grafana at http://localhost:3000 (admin/admin123)"
echo "4. View metrics in Prometheus at http://localhost:9090"
echo ""
echo -e "${YELLOW}Note: Make sure your Venezuelan POS application is configured to export Prometheus metrics${NC}"
echo -e "${YELLOW}The application should be accessible on http://localhost:8000 with metrics on port 8001${NC}"