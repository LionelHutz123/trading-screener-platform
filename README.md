# 🚀 Trading Screener Platform

**High-Performance Trading Analysis & Backtesting Platform**

Deployed on Digital Ocean App Platform with automatic GitHub integration.

[![Deploy](https://img.shields.io/badge/Deploy-Digital%20Ocean-0080FF)](https://cloud.digitalocean.com/apps)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-00a3c4)](https://fastapi.tiangolo.com)

## ✨ Features

### 📊 **Advanced Technical Analysis**
- **RSI Divergence Detection** - Regular & hidden divergences
- **Flag Pattern Recognition** - Bull/bear flags with volume confirmation
- **Order Block Analysis** - Institutional order flow patterns
- **Fair Value Gap Detection** - Price inefficiency identification
- **Multi-timeframe Analysis** - 1h, 4h, 1d comprehensive screening

### 🎯 **Proven Trading Strategies**
Based on backtesting results, our top performers include:
- **LLY 4h/15-period**: 5.42 Sharpe ratio ⭐⭐⭐
- **TSLA Daily**: 99.21% return, 1.73 Sharpe ratio
- **NVDA Daily**: 92.22% return, 1.45 Sharpe ratio

### ⚡ **High-Performance Infrastructure**
- **Digital Ocean App Platform** - Serverless scaling
- **DuckDB** - Lightning-fast analytics database
- **Redis** - Real-time data caching
- **PostgreSQL** - Managed database for results
- **Automatic deployments** from GitHub

## 🚀 **Quick Start**

### 1. **API Endpoints**

**Health Check:**
```bash
GET /health
```

**Run Backtesting:**
```bash
POST /api/backtest/run
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "timeframes": ["1h", "4h"],
  "start_date": "2023-01-01",
  "end_date": "2024-01-01"
}
```

**Get Results:**
```bash
GET /api/backtest/results
GET /api/strategies/top
```

### 2. **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app_platform_api.py

# Run backtesting
python main.py --mode backtesting --symbols AAPL MSFT --timeframes 1h 4h
```

## 📈 **Trading Results**

### 🏆 **Top Performing Strategies**

| Strategy | Symbol | Timeframe | Return | Sharpe | Max DD |
|----------|--------|-----------|---------|--------|--------|
| RSI Divergence | LLY | 4h | 13.03% | **5.42** | -4.15% |
| Flag Pattern | TSLA | 1d | **99.21%** | 1.73 | -21.97% |
| Confluence | NVDA | 1d | **92.22%** | 1.45 | -21.13% |
| Order Block | GOOGL | 4h | 8.95% | **2.86** | -4.75% |

### 📊 **Key Insights**
- **4-hour timeframes** excel at risk-adjusted returns
- **Daily strategies** provide higher absolute returns
- **15-20 period lookbacks** are optimal across symbols
- **Healthcare & Tech** show consistently strong performance

## 🏗️ **Architecture**

```
┌─────────────────────┐    ┌─────────────────────┐
│   GitHub Repository │────│  Digital Ocean      │
│   Auto-Deploy      │    │  App Platform       │
└─────────────────────┘    └─────────────────────┘
                                      │
┌─────────────────────┐    ┌─────────────────────┐
│   FastAPI Service  │    │   Background Jobs   │
│   trading-api      │────│   backtest-runner   │
└─────────────────────┘    └─────────────────────┘
          │                          │
┌─────────────────────┐    ┌─────────────────────┐
│   PostgreSQL DB    │    │      Redis Cache    │
│   Results Storage  │    │   Real-time Data    │
└─────────────────────┘    └─────────────────────┘
```

## 🔧 **Configuration**

### Environment Variables

```bash
# Trading API
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Application
ENV=production
PORT=8080
```

## 📊 **Monitoring & Observability**

- **Health Checks**: Automatic service monitoring
- **Performance Metrics**: API response times, success rates
- **Trading Analytics**: Win rates, Sharpe ratios, drawdowns
- **Resource Monitoring**: CPU, memory, database performance

## 🔄 **Deployment**

### Automatic Deployment
- **Push to `main` branch** → Automatic deployment
- **Zero-downtime deployments** with health checks
- **Rollback capability** if deployment fails

### Manual Deployment
```bash
# Using deployment script
.\deploy_github.ps1 -Action create

# Check status
.\deploy_github.ps1 -Action status
```

## 📁 **Project Structure**

```
trading-screener-platform/
├── 📊 Core Trading Engine
│   ├── core/ta_engine/           # Technical analysis
│   ├── core/backtesting/         # Backtesting engine
│   ├── core/data_engine/         # Data management
│   └── core/multiprocessing/     # Parallel processing
├── 🚀 API & Services
│   ├── app_platform_api.py       # Main API service
│   ├── services/                 # Background services
│   └── web/api/                  # Additional endpoints
├── 🔧 Infrastructure
│   ├── .do/app.yaml              # App Platform config
│   ├── Dockerfile                # Container config
│   └── requirements.txt          # Dependencies
└── 📈 Data & Results
    ├── data/                     # Historical data
    ├── logs/                     # Application logs
    └── backups/                  # Data backups
```

## 🧪 **Testing**

```bash
# Run comprehensive tests
python test_comprehensive_system.py

# Test specific strategies
python -m pytest tests/

# Performance testing
python -m pytest tests/test_performance.py
```

## 📈 **Usage Examples**

### Start Backtesting Job
```python
import requests

response = requests.post('/api/backtest/run', json={
    "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA"],
    "timeframes": ["1h", "4h", "1d"],
    "start_date": "2022-01-01",
    "end_date": "2024-01-01"
})
```

### Get Top Strategies
```python
response = requests.get('/api/strategies/top?limit=10')
top_strategies = response.json()['strategies']
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-strategy`
3. Commit changes: `git commit -m 'Add amazing trading strategy'`
4. Push to branch: `git push origin feature/amazing-strategy`
5. Submit a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Documentation**: Check the `/docs` endpoint
- **Issues**: [GitHub Issues](https://github.com/LionelHutz123/trading-screener-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/LionelHutz123/trading-screener-platform/discussions)

## 🎯 **Roadmap**

- [ ] **Real-time alerts** via WebSocket
- [ ] **Mobile app** for iOS/Android
- [ ] **Machine learning** signal enhancement
- [ ] **Social trading** features
- [ ] **Multi-broker** support

---

**🎉 Ready to revolutionize your trading with data-driven strategies!**

Deploy to Digital Ocean: [![Deploy](https://img.shields.io/badge/Deploy%20Now-0080FF?style=for-the-badge)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/LionelHutz123/trading-screener-platform)