# 🎮 CloudGaming Frontend - Руководство по запуску

## 📦 Требования

- Веб-браузер с поддержкой:
  - HTML5 Video
  - WebRTC (RTCPeerConnection)
  - Fetch API
  - ES6 Modules

### Рекомендуемые браузеры:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🚀 Быстрый старт

### 1. Запуск фронтенда локально

**Способ 1: Простой HTTP сервер (Python)**
```bash
cd /workspaces/cloud-gaming/frontend
python3 -m http.server 3000
```

Затем откройте в браузере: `http://localhost:3000/public/index.html`

**Способ 2: Live Server (VS Code)**
1. Установите расширение Live Server
2. Кликните правой кнопкой на `index.html`
3. Выберите "Open with Live Server"

**Способ 3: Node.js http-server**
```bash
npm install -g http-server
cd /workspaces/cloud-gaming/frontend
http-server -p 3000
```

### 2. Убедитесь, что бэкенд работает

```bash
# Проверьте, что бэкенд запущен на port 8000
curl http://localhost:8000/api/games
```

## 📝 Конфигурация

### Изменение API URL

В файле `src/services/api.js`, измените строку:
```javascript
const API_BASE_URL = window.location.origin + '/api';
```

Для локального развития с отдельным сервером:
```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

## 🎯 Функциональность

### Основные возможности
✅ **Аутентификация**
- Регистрация новых пользователей
- Вход в аккаунт
- Выход из аккаунта

✅ **Библиотека игр**
- Просмотр доступных игр
- Поиск по названию
- Карточки игр с описанием

✅ **Облачный геймнг**
- Потоковое видео через WebRTC
- Управление клавиатурой и мышью
- Поддержка геймпада
- Чат в реальном времени
- Статистика подключения

✅ **Интерфейс**
- Темная тема
- Адаптивный дизайн
- Плавные анимации
- Уведомления

## 🔧 Разработка

### Структура локальной разработки

```
frontend/
├── public/
│   └── index.html                  # Точка входа
├── src/
│   ├── components/
│   │   └── app.js                  # Главное приложение
│   ├── services/
│   │   ├── api.js                  # API клиент
│   │   ├── webrtc.js               # WebRTC
│   │   ├── input.js                # Input handler
│   │   └── notifications.js        # Notifications
│   └── styles/
│       ├── main.css                # Основные стили
│       └── animations.css          # Анимации
```

### Добавление новой функции

1. **Создайте новый сервер мир** в `src/services/`
```javascript
// src/services/my-feature.js
class MyFeature {
    constructor() {
        // инициализация
    }
    
    doSomething() {
        // реализация
    }
}

export { MyFeature };
```

2. **Импортируйте в app.js**
```javascript
import { MyFeature } from '../services/my-feature.js';
```

3. **Использование в App класс**
```javascript
class App {
    constructor() {
        this.myFeature = new MyFeature();
    }
}
```

### Тестирование

Используйте браузерную консоль для отладки:
```javascript
// Проверьте API соединение
api.getGames().then(games => console.log(games))

// Проверьте аутентификацию
api.isAuthenticated // true/false

// Отправьте тестовое входное событие
api.sendKeyboardInput('test-instance-id', 'ArrowUp', true)
```

## 🐛 Решение проблем

### Проблема: CORS ошибка
**Решение**: Убедитесь, что бэкенд имеет правильно сконфигурированные CORS заголовки

### Проблема: WebRTC видео не загружается
**Решение**: 
1. Проверьте, что бэкенд правильно отправляет SDP offer
2. Убедитесь, что браузер поддерживает WebRTC
3. Проверьте консоль для ошибок подключения

### Проблема: Управление не работает
**Решение**:
1. Убедитесь, что input API эндпоинты работают
2. Проверьте права доступа сессии
3. Включите видео элемент перед отправкой команд

## 📊 Мониторинг производительности

### Важные метрики
- **FPS**: Кадры в секунду видеопотока
- **Bitrate**: Пропускная способность потока
- **Latency**: Время задержки (RTT)
- **Connection State**: Статус WebRTC соединения

### DevTools советы
1. Откройте Chrome DevTools (F12)
2. Перейдите на вкладку "Network"
3. Фильтруйте по типу "fetch" для API запросов
4. Проверьте WebRTC статистику в консоли

## 🚢 Развёртывание

### Развёртывание на nginx
```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        root /var/www/cloud-gaming/frontend/public;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }
}
```

### Docker контейнеризация
```dockerfile
FROM nginx:latest
COPY frontend/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📚 Дополнительные ресурсы

- [WebRTC MDN Документация](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)
- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [ES6 Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте консоль браузера (F12)
2. Убедитесь, что бэкенд работает
3. Перезагрузите страницу (Ctrl+Shift+R für обновления кэша)
4. Откройте issue в репозитории

---

**Версия:** 1.0.0  
**Последнее обновление:** 2026-02-28
