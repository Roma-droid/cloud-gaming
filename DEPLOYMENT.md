# 🚀 Руководство по развёртыванию CloudGaming Frontend

## 📋 Оглавление
1. [Локальное развёртывание](#локальное)
2. [Docker контейнеризация](#docker)
3. [Production развёртывание](#production)
4. [Cloud платформы](#cloud)
5. [CI/CD пайпелайн](#cicd)

---

## 🏠 Локальное развёртывание {#локальное}

### Вариант 1: Python HTTP Server
```bash
cd /workspaces/cloud-gaming/frontend
python3 -m http.server 8080
```
Откройте: `http://localhost:8080`

### Вариант 2: Node.js HTTP Server
```bash
npm install -g http-server
cd /workspaces/cloud-gaming/frontend
http-server -p 8080 -c-1  # -c-1 отключает кеширование
```

### Вариант 3: VS Code Live Server
1. Установите расширение "Live Server"
2. Кликните правой кнопкой на `index.html`
3. Выберите "Open with Live Server"

### Вариант 4: Nginx (локально)
```bash
# Установка
sudo apt-get install nginx

# Конфигурация
sudo cat > /etc/nginx/sites-available/cloudgaming << 'NGINX'
server {
    listen 80;
    server_name localhost;
    
    root /workspaces/cloud-gaming/frontend;
    index index.html;
    
    location / {
        try_files $uri /index.html;
    }
}
NGINX

# Запуск
sudo systemctl start nginx
```
Откройте: `http://localhost`

---

## 🐳 Docker контейнеризация {#docker}

### Dockerfile для фронтенда

Создайте файл `docker/web.Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY frontend/ .

# Скопировать файлы в финальный образ
FROM nginx:alpine
COPY --from=builder /app /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx конфигурация (`docker/nginx.conf`)

```nginx
server {
    listen 80;
    server_name _;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Кеширование статических файлов
    location ~* \.(js|css|png|gif|ico|jpg|jpeg|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # HTML не кешировать
    location ~* \.html$ {
        expires 0;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    
    # SPA routing
    location / {
        try_files $uri /index.html;
    }
    
    # Gzip сжатие
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

### Build и Run

```bash
# Build образа
docker build -f docker/web.Dockerfile -t cloudgaming-web:latest .

# Run контейнера
docker run -d \
  --name cloudgaming-web \
  -p 80:80 \
  --restart unless-stopped \
  cloudgaming-web:latest

# Посмотреть логи
docker logs -f cloudgaming-web

# Остановить контейнер
docker stop cloudgaming-web
docker rm cloudgaming-web
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: docker/web.Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - cloudgaming
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/cloudgaming
    depends_on:
      - db
    networks:
      - cloudgaming

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cloudgaming
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - cloudgaming

networks:
  cloudgaming:
    driver: bridge

volumes:
  postgres_data:
```

Запуск всего проекта:
```bash
docker-compose up -d
```

---

## 🌐 Production развёртывание {#production}

### Подготовка

#### 1. Оптимизация кода
```bash
# Минификация
npm install -g minify
minify frontend/src/components/app.js > app.min.js
minify frontend/src/styles/main.css > main.min.css

# Или использовать онлайн минификаторы
```

#### 2. Обновить пути в index.html
```html
<!-- Продакшен -->
<script src="https://cdn.cloudgaming.com/app.min.js"></script>
<link rel="stylesheet" href="https://cdn.cloudgaming.com/main.min.css">

<!-- Или локально -->
<script src="/js/app.min.js"></script>
<link rel="stylesheet" href="/css/main.min.css">
```

#### 3. Настройки безопасности
```javascript
// В api.js
const API_BASE_URL = 'https://api.cloudgaming.com';  // HTTPS!
const WS_URL = 'wss://stream.cloudgaming.com';       // WSS!
```

### Nginx Production конфигурация

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 443 ssl http2;
    server_name cloudgaming.com www.cloudgaming.com;
    
    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/cloudgaming.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cloudgaming.com/privkey.pem;
    
    # SSL оптимизация
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";
    
    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;
    
    # Frontend
    root /usr/share/nginx/html;
    index index.html;
    
    # Статические файлы
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # HTML
    location ~* \.html$ {
        expires 0;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts для WebRTC
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
    
    # SPA routing
    location / {
        try_files $uri /index.html;
    }
}

# Редирект с HTTP на HTTPS
server {
    listen 80;
    server_name cloudgaming.com www.cloudgaming.com;
    return 301 https://$server_name$request_uri;
}
```

### Самоподписанный SSL для разработки
```bash
# Генерировать самоподписанный сертификат
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Использовать с Nginx
ssl_certificate cert.pem;
ssl_certificate_key key.pem;
```

---

## ☁️ Cloud платформы {#cloud}

### AWS (S3 + CloudFront)

```bash
# 1. Создать S3 bucket
aws s3 mb s3://cloudgaming-frontend

# 2. Загрузить файлы
aws s3 sync frontend/ s3://cloudgaming-frontend/

# 3. Включить Static Website Hosting
aws s3api put-bucket-website \
  --bucket cloudgaming-frontend \
  --website-configuration '{"IndexDocument": {"Suffix": "index.html"}}'

# 4. Создать CloudFront дистрибьютор
aws cloudfront create-distribution \
  --origin-domain-name cloudgaming-frontend.s3.amazonaws.com \
  --enabled
```

### Google Cloud (Storage + CDN)

```bash
# 1. Создать bucket
gsutil mb gs://cloudgaming-frontend

# 2. Загрузить файлы
gsutil -m cp -r frontend/* gs://cloudgaming-frontend/

# 3. Сделать публичным
gsutil acl ch -u AllUsers:R gs://cloudgaming-frontend

# 4. Включить Static Website Hosting
gsutil web set -m index.html -e index.html gs://cloudgaming-frontend
```

### Azure (Blob Storage + CDN)

```bash
# 1. Создать storage account
az storage account create --name cloudgaming --resource-group mygroup --location eastus

# 2. Создать контейнер
az storage container create --name web --account-name cloudgaming

# 3. Загрузить файлы
az storage blob upload-batch -d web -s frontend --account-name cloudgaming

# 4. Включить static website
az storage blob service-properties update \
  --account-name cloudgaming \
  --static-website \
  --404-document index.html \
  --index-document index.html
```

### Vercel

```bash
# 1. Установить CLI
npm install -g vercel

# 2. Deploy
cd /workspaces/cloud-gaming/frontend
vercel --prod

# 3. Конфигурация (vercel.json)
{
  "buildCommand": "echo 'No build needed'",
  "outputDirectory": ".",
  "env": {
    "API_BASE_URL": "https://api.cloudgaming.com"
  }
}
```

### Netlify

```bash
# 1. Установить CLI
npm install -g netlify-cli

# 2. Deploy
cd /workspaces/cloud-gaming/frontend
netlify deploy --prod --dir .

# 3. Конфигурация (netlify.toml)
[build]
  command = "echo 'No build needed'"
  publish = "."

[context.production.environment]
  API_BASE_URL = "https://api.cloudgaming.com"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## 🔄 CI/CD пайпелайн {#cicd}

### GitHub Actions

Создайте `.github/workflows/deploy.yml`:

```yaml
name: Deploy CloudGaming Frontend

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate HTML/CSS/JS
        run: |
          npm install -g w3c-html-validator
          html-validator --file frontend/public/index.html
      
      - name: Build Docker image
        run: docker build -f docker/web.Dockerfile -t cloudgaming-web:${{ github.sha }} .
      
      - name: Push to Docker Hub
        run: |
          docker login -u ${{ secrets.DOCKER_USERNAME }} -p ${{ secrets.DOCKER_PASSWORD }}
          docker tag cloudgaming-web:${{ github.sha }} cloudgaming-web:latest
          docker push cloudgaming-web:latest
      
      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: |
          ssh -i ${{ secrets.DEPLOY_KEY }} user@cloudgaming.com \
            "docker pull cloudgaming-web:latest && \
             docker stop cloudgaming-web && \
             docker rm cloudgaming-web && \
             docker run -d -p 80:80 cloudgaming-web:latest"
```

### GitLab CI

Создайте `.gitlab-ci.yml`:

```yaml
stages:
  - validate
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"

validate:
  stage: validate
  script:
    - npm install -g html-validator
    - html-validator --file frontend/public/index.html

build:
  stage: build
  script:
    - docker build -f docker/web.Dockerfile -t cloudgaming-web:$CI_COMMIT_SHA .
    - docker push cloudgaming-web:$CI_COMMIT_SHA

deploy_production:
  stage: deploy
  only:
    - main
  script:
    - docker pull cloudgaming-web:$CI_COMMIT_SHA
    - docker stop cloudgaming-web || true
    - docker run -d --name cloudgaming-web -p 80:80 cloudgaming-web:$CI_COMMIT_SHA
```

---

## 📊 Мониторинг после развёртывания

### Проверить что всё работает

```bash
# 1. Проверить загрузку страницы
curl -I https://cloudgaming.com/

# 2. Проверить содержимое
curl https://cloudgaming.com/ | grep "<title>"

# 3. Проверить API доступность
curl https://cloudgaming.com/api/games

# 4. Проверить WebRTC доступность
curl https://cloudgaming.com/api/stream

# 5. Проверить SSL сертификат
openssl s_client -connect cloudgaming.com:443
```

### Логирование

```bash
# Nginx логи
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Docker логи
docker logs -f cloudgaming-web

# Application логи в браузере
# F12 → Console → посмотреть ошибки
```

---

## 🔒 Безопасность перед продакшеном

### Checklist

- [ ] HTTPS включен (SSL/TLS)
- [ ] HSTS заголовок добавлен
- [ ] CSP (Content-Security-Policy) настроен
- [ ] CORS только для известных доменов
- [ ] Скрыть версию Nginx/Server
- [ ] Отключить directory listing
- [ ] Включить WAF (Web Application Firewall)
- [ ] Regular security updates
- [ ] Backups настроены

### CSP заголовок

```nginx
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.cloudgaming.com wss://stream.cloudgaming.com;
  frame-ancestors 'none';
";
```

---

## 🆘 Troubleshooting

### Frontend не загружается
```bash
# Проверить Nginx логи
tail /var/log/nginx/error.log

# Проверить статус контейнера
docker inspect cloudgaming-web
```

### API ошибок
```bash
# Проверить backend готов
curl http://localhost:8000/api/health

# Проверить CORS настройки
curl -H "Origin: https://cloudgaming.com" http://localhost:8000 -v
```

### WebRTC не работает
```bash
# Проверить WSS порт открыт
telnet localhost 8001

# Проверить сертификаты
openssl s_client -connect stream.cloudgaming.com:8001
```

---

**Версия:** 1.0.0  
**Дата:** 2026-02-28
