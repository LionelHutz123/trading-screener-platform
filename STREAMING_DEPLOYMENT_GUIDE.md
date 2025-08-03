# 🚀 HutzTrades Live Streaming Deployment Guide

Your streaming and pattern recognition system is **ready for deployment** to your existing DigitalOcean app at `trading-screener-lerd2.ondigitalocean.app`.

## 📋 What's Being Deployed

### ✅ New Features Added:
1. **Live Data Streaming**
   - Alpaca paper trading WebSocket connection
   - Real-time 1-minute bar updates
   - Quote and trade data streaming

2. **Pattern Recognition Engine**
   - Flag patterns (bullish/bearish)
   - Order block detection
   - Fair value gaps (FVG)
   - Change of character (CHoCH)
   - Swing high/low detection
   - Real-time confluence signals

3. **New API Endpoints**
   - `GET /api/stream/status` - Check streaming status
   - `POST /api/stream/start` - Start live data feed
   - `GET /api/stream/signals` - Get live trading signals
   - `WebSocket /ws/stream` - Real-time updates
   - `GET /api/stream/market-data/{symbol}` - Latest market data

## 🛠️ Deployment Options

### Option 1: GitHub Push (Recommended)
If your DigitalOcean app is connected to GitHub:

```bash
# Add all changes
git add .

# Commit with descriptive message
git commit -m "Add live streaming and pattern recognition

- Alpaca paper trading integration
- Real-time WebSocket streaming
- Pattern recognition engine (Flag, OB, FVG, CHoCH, Swing)
- Live signal generation
- Streaming API endpoints

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to trigger deployment
git push origin main
```

### Option 2: Manual via DigitalOcean Dashboard
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click on your `hutztrades-secure-api` app
3. Go to Settings → App-Level Environment Variables
4. Add these variables:
   - `ALPACA_API_KEY`: `PK463DCZLB0H1M8TG3DN`
   - `ALPACA_SECRET_KEY`: `UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq`
   - `ENABLE_STREAMING`: `true`
5. Click "Deploy" to trigger a new deployment

### Option 3: Using doctl CLI
```bash
# Install doctl if not already installed
# https://docs.digitalocean.com/reference/doctl/how-to/install/

# Login to DigitalOcean
doctl auth init

# List your apps to get the ID
doctl apps list

# Update environment variables
doctl apps update YOUR_APP_ID \
  --env ALPACA_API_KEY=PK463DCZLB0H1M8TG3DN \
  --env ALPACA_SECRET_KEY=UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq \
  --env ENABLE_STREAMING=true

# Deploy
doctl apps create-deployment YOUR_APP_ID
```

## 🧪 Testing After Deployment

### 1. Health Check
```bash
curl https://trading-screener-lerd2.ondigitalocean.app/health
```

### 2. Stream Status
```bash
curl https://trading-screener-lerd2.ondigitalocean.app/api/stream/status
```

### 3. Start Streaming
```bash
curl -X POST https://trading-screener-lerd2.ondigitalocean.app/api/stream/start
```

### 4. Get Live Signals
```bash
curl https://trading-screener-lerd2.ondigitalocean.app/api/stream/signals
```

### 5. WebSocket Test (JavaScript)
```javascript
const ws = new WebSocket('wss://trading-screener-lerd2.ondigitalocean.app/ws/stream');

ws.onopen = () => {
    console.log('Connected to streaming service');
    ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: ['AAPL', 'TSLA', 'SPY']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 📊 Dashboard Integration

The frontend at `index.html` and `dashboard.html` already has JavaScript (`app.js`) configured to:
- Connect to WebSocket for real-time updates
- Display live signals
- Show rate limit warnings
- Handle streaming status

## 🔍 Monitoring

After deployment, monitor:
1. **DigitalOcean Dashboard**: Check deployment logs
2. **API Endpoints**: Test each endpoint
3. **WebSocket Connection**: Verify real-time data flow
4. **Pattern Detection**: Confirm signals are being generated

## ⚡ Quick Start Commands

```bash
# Test everything is working
curl https://trading-screener-lerd2.ondigitalocean.app/api/stream/status | jq

# Start streaming (if not auto-started)
curl -X POST https://trading-screener-lerd2.ondigitalocean.app/api/stream/start | jq

# Check for live signals
curl https://trading-screener-lerd2.ondigitalocean.app/api/stream/signals | jq
```

## 🎯 Expected Results

Once deployed and streaming is started:
- Real-time market data flows through WebSocket
- Pattern recognition runs on incoming data
- Live signals appear at `/api/stream/signals`
- Dashboard updates in real-time
- Paper trading account shows activity

## 📝 Notes

- Paper trading works during market hours (9:30 AM - 4:00 PM ET)
- Extended hours trading available if configured
- Patterns are detected on 1-minute, 5-minute, and hourly timeframes
- Confluence signals require multiple pattern confirmations

## 🚨 Troubleshooting

If streaming doesn't start:
1. Check Alpaca API credentials are set correctly
2. Verify market is open (or use crypto symbols)
3. Check deployment logs in DigitalOcean
4. Test with a single symbol first

---

**Your live streaming and pattern recognition system is ready to deploy! 🎉**