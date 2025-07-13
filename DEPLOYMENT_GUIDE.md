# 🚀 Deployment Guide

This guide covers the deployment of the Flask application with all security improvements implemented.

## 📋 Prerequisites

### Required Services
- **Redis** (for sessions and message queue)
- **Firebase** (authentication and storage)
- **Celery** (background task processing)

### System Requirements
- Python 3.9+
- 2GB+ RAM
- 10GB+ disk space
- Network access to external APIs

## 🔧 Environment Setup

### 1. Create Environment File
Copy the example environment file and configure it for your environment:

```bash
cp ENVIRONMENT_VARIABLES.md .env
```

### 2. Configure Environment Variables
Edit `.env` file with your specific values:

```bash
# Security Configuration
FLASK_SECRET_KEY=your_very_long_random_secret_key_here_32_chars_minimum
APP_ENV=production
FLASK_DEBUG=False

# Firebase Configuration
FIREBASE_API_KEY=AIzaSyC...
FIREBASE_PROJECT_ID=your-project-id
# ... (all other Firebase variables)

# Redis Configuration
REDIS_URL=redis://your-redis-server:6379/0
REDIS_PASSWORD=your_redis_password

# Celery Configuration
CELERY_BROKER_URL=redis://your-redis-server:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-server:6379/0

# CORS Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Monitoring Configuration
ENABLE_MONITORING=true
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

## 🐳 Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p generated_data/temp_uploads generated_data/stock_reports logs

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=app/main_portal_app.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start command
CMD ["python", "app/main_portal_app.py"]
```

### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --requirepass ${REDIS_PASSWORD}
    restart: unless-stopped

  celery-worker:
    build: .
    command: celery -A app.celery_config worker --loglevel=info --concurrency=4
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
      - ./generated_data:/app/generated_data
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A app.celery_config beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
      - celery-worker
    volumes:
      - ./logs:/app/logs
      - ./generated_data:/app/generated_data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  redis_data:
```

### 3. Create nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream flask_app {
        server web:5000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # File upload size limit
        client_max_body_size 5M;

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://flask_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /upload-ticker-file {
            limit_req zone=upload burst=5 nodelay;
            proxy_pass http://flask_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            access_log off;
            proxy_pass http://flask_app;
        }

        location /metrics {
            allow 127.0.0.1;
            deny all;
            proxy_pass http://flask_app;
        }
    }
}
```

## ☁️ Cloud Deployment

### AWS Deployment

#### 1. ECS/Fargate Setup
```yaml
# task-definition.json
{
  "family": "tempautomate",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "your-ecr-repo/tempautomate:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "APP_ENV", "value": "production"},
        {"name": "REDIS_URL", "value": "redis://your-elasticache-endpoint:6379/0"}
      ],
      "secrets": [
        {"name": "FLASK_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:region:account:secret:flask-secret-key"},
        {"name": "FIREBASE_PRIVATE_KEY", "valueFrom": "arn:aws:secretsmanager:region:account:secret:firebase-private-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tempautomate",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "web"
        }
      }
    }
  ]
}
```

#### 2. ElastiCache Redis
```bash
# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id tempautomate-redis \
  --replication-group-description "Redis for TempAutomate" \
  --node-group-id tempautomate-redis-001 \
  --node-group-availability-zones us-east-1a \
  --num-node-groups 1 \
  --replicas-per-node-group 1 \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --port 6379 \
  --parameter-group-name default.redis7
```

### Google Cloud Deployment

#### 1. Cloud Run Setup
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/tempautomate', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/tempautomate']
  
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'tempautomate'
      - '--image'
      - 'gcr.io/$PROJECT_ID/tempautomate'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '1Gi'
      - '--cpu'
      - '1'
      - '--set-env-vars'
      - 'APP_ENV=production,REDIS_URL=redis://your-memorystore-ip:6379/0'
```

#### 2. Memorystore Redis
```bash
# Create Redis instance
gcloud redis instances create tempautomate-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

## 🔒 Security Hardening

### 1. Network Security
```bash
# Firewall rules (example for GCP)
gcloud compute firewall-rules create tempautomate-allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0 \
  --target-tags tempautomate

gcloud compute firewall-rules create tempautomate-allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags tempautomate

# Block direct access to Redis
gcloud compute firewall-rules create tempautomate-block-redis \
  --deny tcp:6379 \
  --source-ranges 0.0.0.0/0 \
  --target-tags tempautomate
```

### 2. Secrets Management
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name flask-secret-key \
  --description "Flask secret key for TempAutomate" \
  --secret-string "your-very-long-random-secret-key-here"

# Google Secret Manager
echo -n "your-very-long-random-secret-key-here" | \
gcloud secrets create flask-secret-key --data-file=-
```

### 3. SSL/TLS Configuration
```bash
# Let's Encrypt with Certbot
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'tempautomate'
    static_configs:
      - targets: ['yourdomain.com:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s
```

### 2. Grafana Dashboard
```json
{
  "dashboard": {
    "title": "TempAutomate Dashboard",
    "panels": [
      {
        "title": "HTTP Requests",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "File Uploads",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(file_uploads_total[5m])",
            "legendFormat": "{{file_type}} {{status}}"
          }
        ]
      },
      {
        "title": "Celery Tasks",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(celery_tasks_total[5m])",
            "legendFormat": "{{task_name}} {{status}}"
          }
        ]
      }
    ]
  }
}
```

### 3. Alerting Rules
```yaml
# alerting.yml
groups:
  - name: tempautomate
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis instance is not responding"

      - alert: CeleryWorkersDown
        expr: celery_workers_active == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "No Celery workers active"
          description: "All Celery workers are down"
```

## 🚀 Deployment Commands

### Docker Compose
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Scale services
docker-compose up -d --scale celery-worker=3

# Update application
docker-compose pull web
docker-compose up -d web
```

### Kubernetes
```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/celery.yaml
kubectl apply -f k8s/web.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n tempautomate
kubectl logs -f deployment/web -n tempautomate

# Scale deployment
kubectl scale deployment web --replicas=3 -n tempautomate
```

## 🔍 Health Checks

### Application Health
```bash
# Basic health check
curl http://yourdomain.com/health

# Detailed health check
curl http://yourdomain.com/health/detailed

# Kubernetes readiness probe
curl http://yourdomain.com/health/ready

# Kubernetes liveness probe
curl http://yourdomain.com/health/live
```

### Service Health
```bash
# Redis health
redis-cli -h your-redis-host ping

# Celery health
celery -A app.celery_config inspect active

# Prometheus metrics
curl http://yourdomain.com:5000/metrics
```

## 📝 Post-Deployment Checklist

- [ ] Environment variables configured correctly
- [ ] SSL/TLS certificates installed and working
- [ ] Redis connection established
- [ ] Celery workers running
- [ ] Firebase authentication working
- [ ] File uploads functioning
- [ ] Rate limiting active
- [ ] CORS configured for production
- [ ] Monitoring endpoints accessible
- [ ] Health checks passing
- [ ] Security headers present
- [ ] Error logging configured
- [ ] Backup strategy implemented
- [ ] Alerting configured
- [ ] Performance monitoring active

## 🛠️ Troubleshooting

### Common Issues

#### 1. Redis Connection Issues
```bash
# Check Redis connectivity
redis-cli -h your-redis-host ping

# Check Redis logs
docker-compose logs redis

# Verify Redis configuration
echo "CONFIG GET requirepass" | redis-cli -h your-redis-host
```

#### 2. Celery Worker Issues
```bash
# Check Celery worker status
celery -A app.celery_config inspect active

# Restart Celery workers
docker-compose restart celery-worker

# Check Celery logs
docker-compose logs celery-worker
```

#### 3. File Upload Issues
```bash
# Check file permissions
ls -la generated_data/temp_uploads/

# Check disk space
df -h

# Verify file validation
curl -X POST -F "file=@test.csv" http://yourdomain.com/upload-ticker-file
```

#### 4. Rate Limiting Issues
```bash
# Check rate limit headers
curl -I http://yourdomain.com/start-analysis

# Monitor rate limiting
docker-compose logs web | grep "rate limit"
```

## 📚 Additional Resources

- [Flask Security Documentation](https://flask-security.readthedocs.io/)
- [Redis Security Guide](https://redis.io/topics/security)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Nginx Security Headers](https://www.nginx.com/resources/wiki/start/topics/examples/security_headers/) 