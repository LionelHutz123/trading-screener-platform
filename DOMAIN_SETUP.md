# 🌐 HutzTrades.com Domain Setup Guide

## 🎯 Overview
Complete setup guide for deploying your Trading Screener to **hutztrades.com**

## 📋 Domain Configuration Options

### **Option 1: Static Site Hosting (Recommended)**
**Best for**: Professional landing page + API backend

**Setup:**
1. **Upload Files to Web Host**
   - `landing.html` → `index.html` (homepage)
   - `index.html` → `dashboard.html` (trading dashboard)
   - `app.js` → JavaScript functionality

2. **DNS Configuration**
   - Point `hutztrades.com` to your web hosting
   - Create `api.hutztrades.com` CNAME to `trading-screener-lerd2.ondigitalocean.app`

3. **File Structure**
   ```
   hutztrades.com/
   ├── index.html (landing page)
   ├── dashboard.html (trading interface)
   ├── app.js (functionality)
   └── assets/ (images, etc.)
   ```

### **Option 2: Digital Ocean App Platform Custom Domain**
**Best for**: Integrated full-stack deployment

**Setup:**
1. **Add Domain to App Platform**
   ```bash
   doctl apps create-domain <app-id> --domain hutztrades.com
   ```

2. **DNS Configuration**
   - Add CNAME record: `hutztrades.com` → `trading-screener-lerd2.ondigitalocean.app`

3. **SSL Certificate**
   - Automatic Let's Encrypt SSL
   - HTTPS enforced

## 🚀 Quick Deploy Instructions

### **Static Hosting Setup**

1. **Choose a Hosting Provider**
   - Netlify (recommended)
   - Vercel
   - GitHub Pages
   - Traditional web hosting

2. **Deploy Files**
   ```bash
   # If using Netlify
   npm install -g netlify-cli
   netlify deploy --prod --dir .
   ```

3. **Configure Custom Domain**
   - Add `hutztrades.com` in hosting dashboard
   - Update DNS settings

### **Netlify Setup (Easiest)**

1. **Create Netlify Account**
   - Go to netlify.com
   - Connect GitHub account

2. **Deploy from GitHub**
   - Connect to `trading-screener-platform` repo
   - Build command: `# none needed`
   - Publish directory: `.`

3. **Add Custom Domain**
   - Site settings → Domain management
   - Add `hutztrades.com`
   - Follow DNS instructions

## 📁 Required Files for Domain

### **Homepage (landing.html → index.html)**
- Professional landing page
- Company branding
- Feature highlights
- Call-to-action buttons

### **Trading Dashboard (index.html → dashboard.html)**
- Full trading interface
- Real-time data
- Backtesting controls
- Results visualization

### **Configuration Updates Needed**

1. **Update API URLs in app.js**
   ```javascript
   // Current
   apiUrl: 'https://trading-screener-lerd2.ondigitalocean.app'
   
   // Option 1: Keep current (works)
   apiUrl: 'https://trading-screener-lerd2.ondigitalocean.app'
   
   // Option 2: Use subdomain
   apiUrl: 'https://api.hutztrades.com'
   ```

2. **Update Navigation Links**
   ```html
   <!-- Landing page links to dashboard -->
   <a href="dashboard.html">Launch Trading Dashboard</a>
   ```

## 🔧 DNS Configuration

### **Required DNS Records**

**Option 1: Static + API Subdomain**
```
Type    Name    Value
A       @       [Your hosting IP]
CNAME   www     hutztrades.com
CNAME   api     trading-screener-lerd2.ondigitalocean.app
```

**Option 2: Full App Platform**
```
Type    Name    Value
CNAME   @       trading-screener-lerd2.ondigitalocean.app
CNAME   www     trading-screener-lerd2.ondigitalocean.app
```

## 🎨 Branding Customization

### **Colors & Theme**
- Primary: `#2563eb` (Blue)
- Secondary: `#059669` (Green)
- Accent: `#dc2626` (Red)

### **Logo Placement**
- Add logo to header
- Update favicon
- Social media meta tags

## 📊 Analytics Setup

### **Google Analytics**
```html
<!-- Add to <head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_TRACKING_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_TRACKING_ID');
</script>
```

## 🔒 Security & Performance

### **SSL Certificate**
- Automatic with most hosting providers
- Force HTTPS redirects

### **Performance Optimization**
- Enable gzip compression
- CDN for static assets
- Image optimization

## 📞 Support

### **What You Need to Provide**
1. **Hosting Choice** (Netlify recommended)
2. **Domain Registrar Access** (for DNS updates)
3. **Any Logo/Branding Assets**

### **What I Can Help With**
- File customization
- API configuration
- Technical setup guidance
- Custom features

## ✅ Next Steps

1. **Choose hosting option** (recommend Netlify)
2. **Provide domain registrar access** (for DNS)
3. **Upload files** or connect GitHub
4. **Test functionality**
5. **Launch HutzTrades.com!**

---

**Your Professional Trading Platform is Ready for hutztrades.com!** 🚀