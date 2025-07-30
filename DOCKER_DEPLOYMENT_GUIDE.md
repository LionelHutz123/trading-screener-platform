# 🐳 Docker Deployment Guide for DigitalOcean

## 🚀 **Quick Deployment Steps**

### **Step 1: Connect to Your Droplet**
```bash
ssh root@your-droplet-ip
```

### **Step 2: Clone Your Repository**
```bash
mkdir -p /opt/trading-screener
cd /opt/trading-screener
git clone https://github.com/yourusername/trading-screener.git .
```

### **Step 3: Run the Deployment Script**
```bash
chmod +x deploy_docker.sh
./deploy_docker.sh
```

## 📋 **What the Deployment Script Does**

### **✅ Environment Setup**
- Creates `.env.production` with your Alpaca API keys
- Sets up proper directory structure
- Configures permissions

### **🐳 Docker Services**
- **trading-screener**: Main application
- **monitoring**: Grafana dashboard
- **database-backup**: Automated backups

### **🛡️ Security & Monitoring**
- Configures UFW firewall
- Sets up health checks
- Enables automatic restarts
- Configures log rotation

## 🔧 **Manual Deployment (Alternative)**

If you prefer to deploy manually:

### **1. Set Up Environment**
```bash
# Create .env.production
cat > .env.production << 'EOF'
ALPACA_API_KEY=PK463DCZLB0H1M8TG3DN
ALPACA_SECRET_KEY=UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ENVIRONMENT=production
DEBUG=false
EOF
```

### **2. Build and Start**
```bash
# Build the image
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### **3. Configure Firewall**
```bash
ufw allow 22/tcp
ufw allow 8080/tcp
ufw allow 3000/tcp
ufw --force enable
```

## 📊 **Accessing Your Services**

### **Trading Screener**
- **URL**: `http://your-droplet-ip:8080`
- **Health Check**: `http://your-droplet-ip:8080/health`

### **Grafana Monitoring**
- **URL**: `http://your-droplet-ip:3000`
- **Username**: `admin`
- **Password**: `admin`

## 🔍 **Monitoring Commands**

### **Check Service Status**
```bash
# View all containers
docker-compose ps

# Check logs
docker-compose logs -f trading-screener

# Monitor resource usage
docker stats
```

### **Health Checks**
```bash
# Test health endpoint
curl http://localhost:8080/health

# Check container health
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

## 🔄 **Updating Your Application**

### **Method 1: Git Pull + Rebuild**
```bash
cd /opt/trading-screener
git pull
docker-compose up -d --build
```

### **Method 2: Restart Services**
```bash
docker-compose restart
```

### **Method 3: Full Rebuild**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🛠️ **Troubleshooting**

### **Service Won't Start**
```bash
# Check logs
docker-compose logs trading-screener

# Check environment
docker-compose exec trading-screener env | grep ALPACA

# Restart service
docker-compose restart trading-screener
```

### **Port Already in Use**
```bash
# Check what's using the port
netstat -tulpn | grep :8080

# Kill process if needed
sudo kill -9 <PID>
```

### **Disk Space Issues**
```bash
# Clean up Docker
docker system prune -a

# Check disk usage
df -h
```

## 📈 **Production Optimizations**

### **1. SSL/HTTPS Setup**
```bash
# Install Certbot
apt install certbot

# Get SSL certificate
certbot certonly --standalone -d your-domain.com
```

### **2. Database Backup**
```bash
# Manual backup
docker-compose exec trading-screener cp /app/data/trading_data.duckdb /app/backups/

# Check backup schedule
crontab -l
```

### **3. Monitoring Setup**
```bash
# Access Grafana
# Add data sources and dashboards
# Set up alerts
```

## 🔐 **Security Checklist**

- [ ] Change Grafana admin password
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Monitor disk space
- [ ] Set up log rotation
- [ ] Configure alerts

## 📞 **Support Commands**

### **View All Logs**
```bash
docker-compose logs -f
```

### **Restart Everything**
```bash
docker-compose down
docker-compose up -d
```

### **Check Resource Usage**
```bash
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

### **Backup Database**
```bash
docker-compose exec trading-screener cp /app/data/trading_data.duckdb /app/backups/backup_$(date +%Y%m%d_%H%M%S).duckdb
```

## 🎯 **Next Steps After Deployment**

1. **Test the Application**
   - Visit `http://your-droplet-ip:8080`
   - Check health endpoint
   - Test data fetching

2. **Configure Monitoring**
   - Set up Grafana dashboards
   - Configure alerts
   - Monitor performance

3. **Set Up Backups**
   - Verify backup schedule
   - Test restore process
   - Monitor backup storage

4. **Security Hardening**
   - Change default passwords
   - Set up SSL
   - Configure firewall rules

5. **Performance Tuning**
   - Monitor resource usage
   - Optimize Docker settings
   - Scale if needed

## 🚨 **Emergency Commands**

### **Stop All Services**
```bash
docker-compose down
```

### **View Recent Logs**
```bash
docker-compose logs --tail=100 trading-screener
```

### **Restart Specific Service**
```bash
docker-compose restart trading-screener
```

### **Check System Resources**
```bash
top
htop
df -h
free -h
```

Your trading screener is now ready for production! 🎉 