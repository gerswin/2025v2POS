/**
 * Enhanced Charts for Reports Module
 * Venezuelan POS System
 */

class ReportsCharts {
    constructor() {
        this.charts = {};
        this.defaultColors = [
            '#007bff', '#28a745', '#ffc107', '#dc3545', 
            '#6f42c1', '#fd7e14', '#20c997', '#6c757d',
            '#e83e8c', '#17a2b8'
        ];
        
        // Set global Chart.js defaults
        this.setGlobalDefaults();
    }

    setGlobalDefaults() {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#6c757d';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        Chart.defaults.plugins.tooltip.titleColor = '#fff';
        Chart.defaults.plugins.tooltip.bodyColor = '#fff';
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
    }

    /**
     * Create a sales trend line chart
     */
    createSalesTrendChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: options.label || 'Ventas',
                    data: data.values,
                    borderColor: options.color || this.defaultColors[0],
                    backgroundColor: options.color ? options.color + '20' : this.defaultColors[0] + '20',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return options.formatValue ? options.formatValue(value) : value;
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: options.showLegend !== false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = options.formatValue ? 
                                    options.formatValue(context.parsed.y) : 
                                    context.parsed.y;
                                return label + ': ' + value;
                            }
                        }
                    }
                },
                ...options.chartOptions
            }
        };

        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create a multi-dataset comparison chart
     */
    createComparisonChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const datasets = data.datasets.map((dataset, index) => ({
            label: dataset.label,
            data: dataset.data,
            borderColor: this.defaultColors[index % this.defaultColors.length],
            backgroundColor: this.defaultColors[index % this.defaultColors.length] + '20',
            tension: 0.4,
            fill: false,
            pointRadius: 3,
            pointHoverRadius: 5
        }));

        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return options.formatValue ? options.formatValue(value) : value;
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = options.formatValue ? 
                                    options.formatValue(context.parsed.y) : 
                                    context.parsed.y;
                                return label + ': ' + value;
                            }
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create a doughnut chart for distribution data
     */
    createDoughnutChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: options.colors || this.defaultColors.slice(0, data.labels.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: options.legendPosition || 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                const value = options.formatValue ? 
                                    options.formatValue(context.parsed) : 
                                    context.parsed;
                                return context.label + ': ' + value + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create a bar chart for categorical data
     */
    createBarChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const config = {
            type: options.horizontal ? 'bar' : 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: options.label || 'Datos',
                    data: data.values,
                    backgroundColor: options.colors || this.defaultColors[0] + '80',
                    borderColor: options.colors || this.defaultColors[0],
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: options.horizontal ? 'y' : 'x',
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            display: !options.horizontal
                        },
                        ticks: options.horizontal ? {
                            callback: function(value) {
                                return options.formatValue ? options.formatValue(value) : value;
                            }
                        } : undefined
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            display: options.horizontal
                        },
                        ticks: !options.horizontal ? {
                            callback: function(value) {
                                return options.formatValue ? options.formatValue(value) : value;
                            }
                        } : undefined
                    }
                },
                plugins: {
                    legend: {
                        display: options.showLegend !== false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = options.formatValue ? 
                                    options.formatValue(context.parsed.y || context.parsed.x) : 
                                    (context.parsed.y || context.parsed.x);
                                return label + ': ' + value;
                            }
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Create a heat map using Chart.js matrix
     */
    createHeatMap(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        // This would require Chart.js matrix plugin
        // For now, we'll create a custom implementation
        this.createCustomHeatMap(canvasId, data, options);
    }

    /**
     * Create a custom heat map visualization
     */
    createCustomHeatMap(canvasId, data, options = {}) {
        const container = document.getElementById(canvasId);
        if (!container) return null;

        // Clear existing content
        container.innerHTML = '';
        
        // Create heat map grid
        const grid = document.createElement('div');
        grid.className = 'heat-map-grid';
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = `repeat(${data.columns}, 1fr)`;
        grid.style.gap = '2px';
        grid.style.padding = '10px';

        data.values.forEach((value, index) => {
            const cell = document.createElement('div');
            cell.className = 'heat-map-cell';
            cell.style.aspectRatio = '1';
            cell.style.borderRadius = '4px';
            cell.style.display = 'flex';
            cell.style.alignItems = 'center';
            cell.style.justifyContent = 'center';
            cell.style.fontSize = '12px';
            cell.style.fontWeight = 'bold';
            cell.style.cursor = 'pointer';
            cell.style.transition = 'all 0.3s ease';

            // Calculate color intensity based on value
            const maxValue = Math.max(...data.values);
            const intensity = value / maxValue;
            const color = this.getHeatMapColor(intensity, options.colorScheme);
            
            cell.style.backgroundColor = color.bg;
            cell.style.color = color.text;
            cell.textContent = options.showValues ? value : '';
            
            // Add tooltip
            cell.title = `${data.labels[index]}: ${value}`;
            
            // Add hover effect
            cell.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.1)';
                this.style.zIndex = '10';
            });
            
            cell.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
                this.style.zIndex = '1';
            });

            grid.appendChild(cell);
        });

        container.appendChild(grid);
        return grid;
    }

    /**
     * Get color for heat map based on intensity
     */
    getHeatMapColor(intensity, scheme = 'heat') {
        const schemes = {
            heat: {
                low: { bg: '#4caf50', text: '#fff' },
                medium: { bg: '#ffeb3b', text: '#333' },
                high: { bg: '#f44336', text: '#fff' }
            },
            blue: {
                low: { bg: '#e3f2fd', text: '#333' },
                medium: { bg: '#2196f3', text: '#fff' },
                high: { bg: '#0d47a1', text: '#fff' }
            },
            grayscale: {
                low: { bg: '#f5f5f5', text: '#333' },
                medium: { bg: '#9e9e9e', text: '#fff' },
                high: { bg: '#212121', text: '#fff' }
            }
        };

        const colors = schemes[scheme] || schemes.heat;
        
        if (intensity < 0.33) return colors.low;
        if (intensity < 0.66) return colors.medium;
        return colors.high;
    }

    /**
     * Create a gauge chart for KPIs
     */
    createGaugeChart(canvasId, value, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const maxValue = options.max || 100;
        const percentage = (value / maxValue) * 100;
        
        const config = {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [percentage, 100 - percentage],
                    backgroundColor: [
                        this.getGaugeColor(percentage),
                        '#e9ecef'
                    ],
                    borderWidth: 0,
                    cutout: '80%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                rotation: -90,
                circumference: 180,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            },
            plugins: [{
                id: 'gaugeText',
                beforeDraw: function(chart) {
                    const ctx = chart.ctx;
                    const centerX = chart.chartArea.left + (chart.chartArea.right - chart.chartArea.left) / 2;
                    const centerY = chart.chartArea.top + (chart.chartArea.bottom - chart.chartArea.top) / 2;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = 'bold 24px Inter';
                    ctx.fillStyle = '#333';
                    ctx.fillText(value + (options.suffix || ''), centerX, centerY);
                    
                    if (options.label) {
                        ctx.font = '14px Inter';
                        ctx.fillStyle = '#666';
                        ctx.fillText(options.label, centerX, centerY + 30);
                    }
                    ctx.restore();
                }
            }]
        };

        const chart = new Chart(ctx, config);
        this.charts[canvasId] = chart;
        return chart;
    }

    /**
     * Get color for gauge based on percentage
     */
    getGaugeColor(percentage) {
        if (percentage >= 80) return '#28a745';
        if (percentage >= 60) return '#ffc107';
        if (percentage >= 40) return '#fd7e14';
        return '#dc3545';
    }

    /**
     * Update chart data
     */
    updateChart(canvasId, newData) {
        const chart = this.charts[canvasId];
        if (!chart) return;

        if (newData.labels) {
            chart.data.labels = newData.labels;
        }
        
        if (newData.datasets) {
            chart.data.datasets = newData.datasets;
        } else if (newData.values) {
            chart.data.datasets[0].data = newData.values;
        }

        chart.update('active');
    }

    /**
     * Destroy chart
     */
    destroyChart(canvasId) {
        const chart = this.charts[canvasId];
        if (chart) {
            chart.destroy();
            delete this.charts[canvasId];
        }
    }

    /**
     * Destroy all charts
     */
    destroyAllCharts() {
        Object.keys(this.charts).forEach(canvasId => {
            this.destroyChart(canvasId);
        });
    }

    /**
     * Export chart as image
     */
    exportChart(canvasId, filename = 'chart') {
        const chart = this.charts[canvasId];
        if (!chart) return;

        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename + '.png';
        link.href = url;
        link.click();
    }

    /**
     * Resize all charts
     */
    resizeCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }
}

// Global instance
window.ReportsCharts = new ReportsCharts();

// Auto-resize charts on window resize
window.addEventListener('resize', () => {
    window.ReportsCharts.resizeCharts();
});

// Utility functions for common chart operations
window.ChartUtils = {
    formatCurrency: (value) => {
        return new Intl.NumberFormat('es-VE', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    },
    
    formatNumber: (value) => {
        return new Intl.NumberFormat('es-VE').format(value);
    },
    
    formatPercentage: (value) => {
        return new Intl.NumberFormat('es-VE', {
            style: 'percent',
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }).format(value / 100);
    },
    
    generateColors: (count) => {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 360 / count) % 360;
            colors.push(`hsl(${hue}, 70%, 50%)`);
        }
        return colors;
    }
};