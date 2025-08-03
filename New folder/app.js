// Trading Screener Dashboard JavaScript
class TradingScreenerDashboard {
    constructor() {
        this.apiUrl = 'https://trading-screener-lerd2.ondigitalocean.app';
        this.init();
    }

    async init() {
        await this.checkSystemHealth();
        await this.loadTopStrategies();
        await this.loadBacktestResults();
        this.setupEventListeners();
        this.startHealthMonitoring();
    }

    setupEventListeners() {
        // Backtest form submission
        document.getElementById('backtestForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.runBacktest();
        });

        // Refresh buttons
        document.getElementById('refreshStrategiesBtn').addEventListener('click', () => {
            this.loadTopStrategies();
        });

        document.getElementById('refreshResultsBtn').addEventListener('click', () => {
            this.loadBacktestResults();
        });
    }

    async checkSystemHealth() {
        const statusElement = document.getElementById('systemStatus');
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                statusElement.className = 'status-badge status-healthy';
                statusElement.innerHTML = '<i class="bi bi-check-circle me-1"></i>System Healthy';
                
                // Update metrics
                document.getElementById('dataPoints').textContent = data.data_points?.toLocaleString() || 'N/A';
                document.getElementById('apiVersion').textContent = data.version || 'N/A';
                document.getElementById('dbStatus').textContent = data.database || 'N/A';
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } else {
                throw new Error('System not healthy');
            }
        } catch (error) {
            statusElement.className = 'status-badge status-error';
            statusElement.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>System Error';
            console.error('Health check failed:', error);
        }
    }

    async loadTopStrategies() {
        const container = document.getElementById('topStrategies');
        try {
            const response = await fetch(`${this.apiUrl}/api/strategies/top`);
            const data = await response.json();
            
            if (data.strategies && data.strategies.length > 0) {
                container.innerHTML = data.strategies.map(strategy => `
                    <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                            <strong>${strategy.symbol} ${strategy.timeframe}</strong>
                            <br>
                            <small class="text-muted">${strategy.strategy}</small>
                        </div>
                        <div class="text-end">
                            <div class="badge bg-primary">Sharpe: ${strategy.sharpe_ratio}</div>
                            <br>
                            <small class="text-success">${strategy.return}% return</small>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="text-muted text-center py-3">No strategies available</p>';
            }
        } catch (error) {
            container.innerHTML = '<p class="text-danger text-center py-3">Error loading strategies</p>';
            console.error('Failed to load strategies:', error);
        }
    }

    async loadBacktestResults() {
        const container = document.getElementById('resultsTable');
        try {
            const response = await fetch(`${this.apiUrl}/api/backtest/results`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                container.innerHTML = `
                    <div class="table-responsive results-table">
                        <table class="table table-hover mb-0">
                            <thead class="table-header">
                                <tr>
                                    <th>Symbol</th>
                                    <th>Timeframe</th>
                                    <th>Strategy</th>
                                    <th>Return</th>
                                    <th>Sharpe Ratio</th>
                                    <th>Max Drawdown</th>
                                    <th>Win Rate</th>
                                    <th>Trades</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.results.map(result => `
                                    <tr class="strategy-row">
                                        <td><strong>${result.symbol}</strong></td>
                                        <td><span class="badge bg-secondary">${result.timeframe}</span></td>
                                        <td>${result.strategy}</td>
                                        <td class="text-success"><strong>+${result.total_return}%</strong></td>
                                        <td><span class="badge ${result.sharpe_ratio > 2 ? 'bg-success' : result.sharpe_ratio > 1 ? 'bg-warning' : 'bg-secondary'}">${result.sharpe_ratio}</span></td>
                                        <td class="text-danger">${result.max_drawdown}%</td>
                                        <td>${(result.win_rate * 100).toFixed(1)}%</td>
                                        <td>${result.trades}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div class="mt-3 text-center">
                        <small class="text-muted">Showing ${data.results.length} of ${data.count} total results</small>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-inbox display-4 text-muted"></i>
                        <p class="text-muted mt-2">No backtest results available</p>
                        <p class="text-muted">Run a backtest to see results here</p>
                    </div>
                `;
            }
        } catch (error) {
            container.innerHTML = '<p class="text-danger text-center py-3">Error loading results</p>';
            console.error('Failed to load results:', error);
        }
    }

    async runBacktest() {
        const btn = document.getElementById('runBacktestBtn');
        const statusDiv = document.getElementById('backtestStatus');
        const progressDiv = document.getElementById('backtestProgress');
        
        // Get form data
        const symbols = Array.from(document.getElementById('symbolSelect').selectedOptions)
            .map(option => option.value);
        
        const timeframes = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);
        
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        if (symbols.length === 0) {
            alert('Please select at least one symbol');
            return;
        }
        
        if (timeframes.length === 0) {
            alert('Please select at least one timeframe');
            return;
        }
        
        // Show loading state
        btn.disabled = true;
        btn.innerHTML = '<div class="loading-spinner me-2"></div>Launching Backtest...';
        statusDiv.style.display = 'block';
        
        try {
            const response = await fetch(`${this.apiUrl}/api/backtest/run`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    symbols,
                    timeframes,
                    start_date: startDate,
                    end_date: endDate
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'started') {
                progressDiv.innerHTML = `
                    <div><strong>Backtest Parameters:</strong></div>
                    <ul class="mb-2">
                        <li>Symbols: ${symbols.join(', ')}</li>
                        <li>Timeframes: ${timeframes.join(', ')}</li>
                        <li>Period: ${startDate} to ${endDate}</li>
                    </ul>
                    <div><strong>Expected Results:</strong></div>
                    <ul class="mb-0">
                        <li>LLY 4h: ${data.expected_results?.LLY_4h || 'High Sharpe ratio'}</li>
                        <li>TSLA Daily: ${data.expected_results?.TSLA_daily || 'High returns'}</li>
                        <li>NVDA Daily: ${data.expected_results?.NVDA_daily || 'Strong performance'}</li>
                    </ul>
                `;
                
                // Start monitoring results
                this.monitorBacktestProgress();
                
                // Show success message after a delay
                setTimeout(() => {
                    statusDiv.innerHTML = `
                        <div class="alert alert-success">
                            <i class="bi bi-check-circle me-2"></i>
                            <strong>Backtesting launched successfully!</strong>
                            <br>
                            Results will appear in the table below as they become available.
                        </div>
                    `;
                    
                    // Auto-refresh results
                    this.loadBacktestResults();
                }, 3000);
                
            } else {
                throw new Error(data.message || 'Failed to start backtest');
            }
            
        } catch (error) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Error:</strong> ${error.message}
                </div>
            `;
            console.error('Backtest failed:', error);
        } finally {
            // Reset button after delay
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-rocket-takeoff me-2"></i>Launch Comprehensive Backtesting';
            }, 2000);
        }
    }

    monitorBacktestProgress() {
        // Monitor for updated results every 10 seconds
        const intervalId = setInterval(async () => {
            await this.loadBacktestResults();
            await this.loadTopStrategies();
        }, 10000);

        // Stop monitoring after 2 minutes
        setTimeout(() => {
            clearInterval(intervalId);
        }, 120000);
    }

    startHealthMonitoring() {
        // Check system health every 30 seconds
        setInterval(() => {
            this.checkSystemHealth();
        }, 30000);
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TradingScreenerDashboard();
});

// Add some utility functions for better UX
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}