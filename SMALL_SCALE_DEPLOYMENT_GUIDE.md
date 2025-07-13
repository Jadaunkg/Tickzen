# 🚀 Small Scale Deployment Guide
## Optimized for 10-15 Concurrent Users, 100 Total Users/Day

This guide is specifically optimized for small-scale deployment using the **free Redis plan** (30MB RAM, 30 connections).

## 📊 **Resource Requirements Analysis**

### **Memory Usage (30MB Limit):**
- **Sessions**: ~2-3MB (24-hour lifetime, 15 concurrent users)
- **Rate Limiting**: ~1-2MB (reduced limits)
- **Celery Queue**: ~3-5MB (optimized task storage)
- **SocketIO**: ~2-3MB (real-time connections)
- **Task Cache**: ~2-3MB (15-minute expiration)
- **Ticker Cache**: ~2-3MB (minimal caching)
- **System Overhead**: ~5MB
- **Total Estimated**: **17-24MB** ✅ (Within 30MB limit)

### **Connection Usage (30 Limit):**
- **Flask App**: 1 connection
- **Celery Workers**: 2 connections (reduced from 8)
- **SocketIO**: 1 connection
- **Rate Limiting**: 1 connection
- **Monitoring**: 1 connection
- **Azure Functions**: 1 connection
- **Total Connections**: **7 connections** ✅ (Within 30 limit)

## 🔧 **Optimization Summary**

### **1. Session Management**
```python
# Reduced session lifetime from 7 days to 24 hours
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Shorter session key prefix
app.config['SESSION_KEY_PREFIX'] = 's:'  # Instead of 'flask_session:'
```

### **2. Rate Limiting (Conservative)**
```python
RATE_LIMIT_CONFIG = {
    'default': '50 per day;10 per hour;3 per minute',
    'api': '200 per day;30 per hour;8 per minute',
    'auth': '20 per day;5 per hour;2 per minute',
    'upload': '10 per day;3 per hour;1 per minute',
    'analysis': '30 per day;8 per hour;2 per minute',
    'automation': '15 per day;3 per hour;1 per minute'
}
```

### **3. Celery Optimization**
```python
# Reduced worker concurrency
CELERY_WORKER_CONCURRENCY="2"  # Instead of 8

# Shorter task timeouts
CELERY_TASK_TIME_LIMIT="900"  # 15 minutes instead of 30

# Faster result expiration
result_expires=900  # 15 minutes instead of 1 hour
```

### **4. Gunicorn Optimization**
```bash
# Fewer workers for small scale
gunicorn --bind=0.0.0.0 --timeout 300 --workers 2 --worker-class eventlet app.main_portal_app:app
```

## 🚀 **Deployment Steps**

### **1. Redis Cloud Setup**
```bash
# Create free Redis Cloud instance
# - Plan: Free
# - Region: East US (Virginia)
# - Memory: 30MB
# - Connections: 30
# - Database: 1
```

### **2. Environment Variables**
```bash
# .env file for small scale
FLASK_SECRET_KEY=your_32_char_secret_key
APP_ENV=production
FLASK_DEBUG=False

# Redis Configuration
REDIS_URL=redis://username:password@host:port/0
REDIS_PASSWORD=your_redis_password

# Celery Configuration
CELERY_BROKER_URL=redis://username:password@host:port/0
CELERY_RESULT_BACKEND=redis://username:password@host:port/0

# Firebase Configuration (your existing config)
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_PROJECT_ID=your_project_id
# ... (other Firebase variables)

# CORS Configuration
ALLOWED_ORIGINS=https://yourdomain.com

# Monitoring Configuration
ENABLE_MONITORING=true
```

### **3. Azure Deployment**
```bash
# Use the optimized azure-deploy.sh script
./azure-deploy.sh
```

## 📈 **Monitoring & Alerts**

### **1. Redis Memory Monitoring**
```python
# Add to your monitoring
def check_redis_memory():
    redis_client = redis.from_url(REDIS_URL)
    info = redis_client.info('memory')
    used_memory = info['used_memory_human']
    max_memory = '30MB'
    
    if info['used_memory'] > 25 * 1024 * 1024:  # 25MB threshold
        send_alert(f"Redis memory usage high: {used_memory}")
```

### **2. Connection Monitoring**
```python
def check_redis_connections():
    redis_client = redis.from_url(REDIS_URL)
    info = redis_client.info('clients')
    connected_clients = info['connected_clients']
    
    if connected_clients > 25:  # 25 connection threshold
        send_alert(f"Redis connections high: {connected_clients}/30")
```

## 🛡️ **User Limits & Restrictions**

### **Per User Limits:**
- **Daily Analysis**: 30 per user
- **File Uploads**: 10 per user
- **Automation Runs**: 15 per user
- **API Calls**: 200 per user

### **Concurrent Limits:**
- **Max Concurrent Users**: 15
- **Max Concurrent Analysis**: 5
- **Max Concurrent Uploads**: 2
- **Max Concurrent Automation**: 3

## 🔄 **Scaling Strategy**

### **When to Upgrade:**
1. **Memory Usage > 25MB** consistently
2. **Connection Count > 25** consistently
3. **User Count > 15** concurrent users
4. **Daily Users > 100** regularly

### **Upgrade Path:**
```
Free Plan (30MB) → Basic Plan (250MB) → Standard Plan (1GB)
```

## 📊 **Performance Expectations**

### **Response Times:**
- **Web Pages**: < 2 seconds
- **API Calls**: < 1 second
- **Stock Analysis**: 2-5 minutes
- **File Uploads**: < 30 seconds

### **Throughput:**
- **Concurrent Users**: 10-15
- **Daily Requests**: ~500-1000
- **File Uploads**: ~50-100
- **Analysis Jobs**: ~100-200

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **1. Redis Memory Full**
```bash
# Check memory usage
redis-cli -h your-host info memory

# Clear old sessions
redis-cli -h your-host --scan --pattern "s:*" | xargs redis-cli -h your-host del

# Clear old Celery results
redis-cli -h your-host --scan --pattern "celery-task-meta-*" | xargs redis-cli -h your-host del
```

#### **2. Too Many Connections**
```bash
# Check connection count
redis-cli -h your-host info clients

# Restart application to reset connections
# Check for connection leaks in your code
```

#### **3. Rate Limiting Issues**
```bash
# Check rate limit headers
curl -I https://yourdomain.com/start-analysis

# Monitor rate limiting logs
tail -f logs/app.log | grep "rate limit"
```

## ✅ **Success Metrics**

### **Green Zone (All Good):**
- Memory Usage: < 20MB
- Connections: < 20
- Response Time: < 2s
- Error Rate: < 1%

### **Yellow Zone (Monitor):**
- Memory Usage: 20-25MB
- Connections: 20-25
- Response Time: 2-5s
- Error Rate: 1-5%

### **Red Zone (Upgrade Needed):**
- Memory Usage: > 25MB
- Connections: > 25
- Response Time: > 5s
- Error Rate: > 5%

## 💰 **Cost Analysis**

### **Free Tier Costs:**
- **Redis Cloud**: $0/month
- **Azure App Service**: $0/month (F1 tier)
- **Firebase**: $0/month (within free limits)
- **Total**: **$0/month** ✅

### **When to Upgrade:**
- **Redis Basic**: $13.41/month (250MB)
- **Azure B1**: $12.41/month
- **Total**: **~$26/month**

## 🎯 **Conclusion**

This optimized configuration will comfortably handle:
- ✅ **10-15 concurrent users**
- ✅ **100 total users per day**
- ✅ **Within free Redis plan limits**
- ✅ **Good performance and reliability**

The key is **monitoring** and being ready to upgrade when you hit the limits! 