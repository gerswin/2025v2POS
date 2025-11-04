#!/bin/bash

# Venezuelan POS System Load Testing Script
# This script runs comprehensive load tests using Artillery.js

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TARGET_URL=${TARGET_URL:-"http://localhost:8000"}
RESULTS_DIR="load_testing/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}Venezuelan POS System Load Testing${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Check if Artillery is installed
if ! command -v artillery &> /dev/null; then
    echo -e "${RED}Error: Artillery.js is not installed${NC}"
    echo "Install it with: npm install -g artillery"
    exit 1
fi

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check if target server is running
echo -e "${YELLOW}Checking target server availability...${NC}"
if ! curl -s "$TARGET_URL/health/" > /dev/null; then
    echo -e "${RED}Error: Target server at $TARGET_URL is not responding${NC}"
    echo "Make sure the Venezuelan POS system is running"
    exit 1
fi

echo -e "${GREEN}✓ Target server is responding${NC}"
echo ""

# Function to run a specific test
run_test() {
    local test_name=$1
    local config_file=$2
    local output_file="$RESULTS_DIR/${test_name}_${TIMESTAMP}.json"
    local report_file="$RESULTS_DIR/${test_name}_${TIMESTAMP}.html"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    # Run Artillery test
    artillery run \
        --target "$TARGET_URL" \
        --output "$output_file" \
        "$config_file"
    
    # Generate HTML report
    artillery report \
        --output "$report_file" \
        "$output_file"
    
    echo -e "${GREEN}✓ $test_name completed${NC}"
    echo -e "  Results: $output_file"
    echo -e "  Report:  $report_file"
    echo ""
}

# Function to run quick smoke test
run_smoke_test() {
    echo -e "${YELLOW}Running smoke test...${NC}"
    
    local smoke_config=$(cat << EOF
config:
  target: '$TARGET_URL'
  phases:
    - duration: 30
      arrivalRate: 2
scenarios:
  - name: "Smoke Test"
    flow:
      - get:
          url: "/health/"
      - get:
          url: "/api/health/"
EOF
)
    
    echo "$smoke_config" | artillery run -
    echo -e "${GREEN}✓ Smoke test completed${NC}"
    echo ""
}

# Function to analyze results
analyze_results() {
    echo -e "${YELLOW}Analyzing results...${NC}"
    
    local latest_result=$(ls -t "$RESULTS_DIR"/*.json 2>/dev/null | head -1)
    
    if [ -z "$latest_result" ]; then
        echo -e "${RED}No results found to analyze${NC}"
        return
    fi
    
    echo -e "Latest result file: $latest_result"
    
    # Extract key metrics using jq if available
    if command -v jq &> /dev/null; then
        echo ""
        echo -e "${BLUE}Key Metrics:${NC}"
        
        local total_requests=$(jq '.aggregate.counters["http.requests"] // 0' "$latest_result")
        local total_responses=$(jq '.aggregate.counters["http.responses"] // 0' "$latest_result")
        local errors=$(jq '.aggregate.counters["errors.ECONNREFUSED"] // 0' "$latest_result")
        local p95=$(jq '.aggregate.latency.p95 // 0' "$latest_result")
        local p99=$(jq '.aggregate.latency.p99 // 0' "$latest_result")
        local mean=$(jq '.aggregate.latency.mean // 0' "$latest_result")
        
        echo "  Total Requests: $total_requests"
        echo "  Total Responses: $total_responses"
        echo "  Errors: $errors"
        echo "  Mean Response Time: ${mean}ms"
        echo "  P95 Response Time: ${p95}ms"
        echo "  P99 Response Time: ${p99}ms"
        
        # Performance assessment
        echo ""
        echo -e "${BLUE}Performance Assessment:${NC}"
        
        if (( $(echo "$p95 > 500" | bc -l) )); then
            echo -e "${RED}❌ P95 response time exceeds 500ms threshold${NC}"
        else
            echo -e "${GREEN}✅ P95 response time within acceptable range${NC}"
        fi
        
        if (( $(echo "$p99 > 1000" | bc -l) )); then
            echo -e "${RED}❌ P99 response time exceeds 1000ms threshold${NC}"
        else
            echo -e "${GREEN}✅ P99 response time within acceptable range${NC}"
        fi
        
        local error_rate=$(echo "scale=2; $errors * 100 / $total_requests" | bc -l)
        if (( $(echo "$error_rate > 5" | bc -l) )); then
            echo -e "${RED}❌ Error rate exceeds 5% threshold: ${error_rate}%${NC}"
        else
            echo -e "${GREEN}✅ Error rate within acceptable range: ${error_rate}%${NC}"
        fi
    else
        echo -e "${YELLOW}Install 'jq' for detailed metrics analysis${NC}"
    fi
    
    echo ""
}

# Main execution
echo -e "${YELLOW}Select test type:${NC}"
echo "1. Smoke test (quick validation)"
echo "2. Standard load test"
echo "3. Stress test (high load)"
echo "4. All tests"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        run_smoke_test
        ;;
    2)
        run_test "standard_load" "load_testing/artillery_config.yml"
        analyze_results
        ;;
    3)
        # Create stress test config
        stress_config="load_testing/artillery_stress_config.yml"
        cat > "$stress_config" << EOF
config:
  target: '$TARGET_URL'
  phases:
    - duration: 60
      arrivalRate: 10
      rampTo: 200
    - duration: 180
      arrivalRate: 200
    - duration: 60
      arrivalRate: 200
      rampTo: 10
  ensure:
    p95: 1000
    p99: 2000
    maxErrorRate: 10
scenarios:
  - name: "Stress Test"
    flow:
      - get:
          url: "/health/"
      - get:
          url: "/api/health/"
      - get:
          url: "/api/events/"
EOF
        
        run_test "stress_test" "$stress_config"
        analyze_results
        ;;
    4)
        echo -e "${BLUE}Running all tests...${NC}"
        run_smoke_test
        run_test "standard_load" "load_testing/artillery_config.yml"
        
        # Create and run stress test
        stress_config="load_testing/artillery_stress_config.yml"
        cat > "$stress_config" << EOF
config:
  target: '$TARGET_URL'
  phases:
    - duration: 60
      arrivalRate: 10
      rampTo: 200
    - duration: 180
      arrivalRate: 200
  ensure:
    p95: 1000
    p99: 2000
    maxErrorRate: 10
scenarios:
  - name: "Stress Test"
    flow:
      - get:
          url: "/health/"
      - get:
          url: "/api/health/"
EOF
        
        run_test "stress_test" "$stress_config"
        analyze_results
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Load testing completed!${NC}"
echo -e "Results are available in: $RESULTS_DIR"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review the HTML reports for detailed analysis"
echo "2. Check application logs for any errors during testing"
echo "3. Monitor system resources (CPU, memory, database connections)"
echo "4. Compare results with previous test runs"