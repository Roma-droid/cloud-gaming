# 🔗 Интеграция с Backend API

## 📋 Список API Endpoints

### Аутентификация

#### 🔐 POST /api/auth/register
Регистрация нового пользователя
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securePassword123"
  }'
```

**Ответ (200):**
```json
{
  "user_id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2026-02-28T10:00:00Z"
}
```

#### 🔐 POST /api/auth/login
Вход в аккаунт
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securePassword123"
  }'
```

**Ответ (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### 🔐 POST /api/auth/logout
Выход из аккаунта
```bash
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer {token}"
```

**Ответ (200):**
```json
{
  "message": "Успешный выход"
}
```

---

### Игры

#### 🎮 GET /api/games
Получить список всех доступных игр
```bash
curl -X GET "http://localhost:8000/api/games" \
  -H "Authorization: Bearer {token}"
```

**Ответ (200):**
```json
[
  {
    "id": 1,
    "name": "Minecraft",
    "description": "Sandbox simulation game",
    "genre": "Sandbox",
    "icon": "🎮",
    "max_players": 4
  },
  {
    "id": 2,
    "name": "Portal 2",
    "description": "Puzzle-platformer game",
    "genre": "Puzzle",
    "icon": "🎯",
    "max_players": 2
  }
]
```

#### 🎮 GET /api/games/{game_id}
Получить информацию об одной игре
```bash
curl -X GET "http://localhost:8000/api/games/1" \
  -H "Authorization: Bearer {token}"
```

---

### Игровые сессии

#### 🚀 POST /api/instances
Создать новую игровую сессию
```bash
curl -X POST "http://localhost:8000/api/instances" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": 1,
    "region": "eu-west-1",
    "quality": "high"
  }'
```

**Ответ (201):**
```json
{
  "instance_id": "abc123def456",
  "game_id": 1,
  "status": "starting",
  "server_url": "wss://game-server-1.cloud.example.com:8080",
  "created_at": "2026-02-28T10:05:00Z"
}
```

#### 📊 GET /api/instances/{instance_id}
Получить статус сессии
```bash
curl -X GET "http://localhost:8000/api/instances/abc123def456" \
  -H "Authorization: Bearer {token}"
```

**Ответ (200):**
```json
{
  "instance_id": "abc123def456",
  "game_id": 1,
  "status": "ready",
  "uptime": 120,
  "fps": 60,
  "bitrate": 5000,
  "player_count": 1
}
```

#### 🔴 DELETE /api/instances/{instance_id}
Остановить игровую сессию
```bash
curl -X DELETE "http://localhost:8000/api/instances/abc123def456" \
  -H "Authorization: Bearer {token}"
```

**Ответ (200):**
```json
{
  "instance_id": "abc123def456",
  "status": "stopped",
  "duration": 300
}
```

---

### WebRTC Streaming

#### 📡 POST /api/instances/{instance_id}/streaming/offer
Получить SDP предложение для WebRTC

```bash
curl -X POST "http://localhost:8000/api/instances/abc123def456/streaming/offer" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "ice_candidates": [],
    "rtc_offer": "v=0\r\no=- ..."
  }'
```

**Ответ (200):**
```json
{
  "rtc_answer": "v=0\r\no=- ...",
  "ice_candidates": [
    {
      "candidate": "candidate:...",
      "sdpMLineIndex": 0,
      "sdpMid": "video"
    }
  ]
}
```

#### 📊 GET /api/instances/{instance_id}/stats
Получить статистику потока
```bash
curl -X GET "http://localhost:8000/api/instances/abc123def456/stats" \
  -H "Authorization: Bearer {token}"
```

**Ответ (200):**
```json
{
  "fps": 60,
  "bitrate": 5000,
  "resolution": "1920x1080",
  "latency": 45,
  "codec": "H.264"
}
```

---

### Управление

#### ⌨️ POST /api/instances/{instance_id}/input/keyboard
Отправить нажатие клавиши
```bash
curl -X POST "http://localhost:8000/api/instances/abc123def456/input/keyboard" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "KeyW",
    "pressed": true
  }'
```

**Ответ (200):**
```json
{
  "status": "accepted"
}
```

#### 🖱️ POST /api/instances/{instance_id}/input/mouse
Отправить движение мыши
```bash
curl -X POST "http://localhost:8000/api/instances/abc123def456/input/mouse" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "x": 640,
    "y": 360,
    "button": "left"
  }'
```

#### 🎮 POST /api/instances/{instance_id}/input/gamepad
Отправить ввод геймпада
```bash
curl -X POST "http://localhost:8000/api/instances/abc123def456/input/gamepad" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "button": "a",
    "pressed": true,
    "axis": {
      "left_stick_x": 0.5,
      "left_stick_y": 0.3
    }
  }'
```

---

### Чат

#### 💬 POST /api/instances/{instance_id}/chat
Отправить сообщение в чат сессии
```bash
curl -X POST "http://localhost:8000/api/instances/abc123def456/chat" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello everyone!",
    "timestamp": "2026-02-28T10:05:00Z"
  }'
```

**Ответ (200):**
```json
{
  "message_id": 123,
  "user_id": 1,
  "text": "Hello everyone!",
  "timestamp": "2026-02-28T10:05:00Z"
}
```

---

## 🧪 Тестирование API

### Инструменты
- **Curl** - командная строка
- **Postman** - GUI для тестирования
- **Thunder Client** - VS Code расширение
- **REST Client** - VS Code расширение

### Используемые переменные

Установите эти переменные в Postman или локально:
```
{{BASE_URL}} = http://localhost:8000
{{TOKEN}} = ваш JWT токен
{{INSTANCE_ID}} = ID текущей сессии
{{GAME_ID}} = ID игры
```

### Сценарий тестирования

#### 1️⃣ Регистрация
```bash
POST {{BASE_URL}}/api/auth/register
{
  "username": "test_user",
  "email": "test@example.com",
  "password": "test12345"
}
```

Сохраните полученный `user_id`

#### 2️⃣ Вход
```bash
POST {{BASE_URL}}/api/auth/login
{
  "username": "test_user",
  "password": "test12345"
}
```

Сохраните `access_token` в переменную `{{TOKEN}}`

#### 3️⃣ Получить игры
```bash
GET {{BASE_URL}}/api/games
Authorization: Bearer {{TOKEN}}
```

Выберите один из `game_id` и сохраните как `{{GAME_ID}}`

#### 4️⃣ Создать сессию
```bash
POST {{BASE_URL}}/api/instances
Authorization: Bearer {{TOKEN}}
{
  "game_id": {{GAME_ID}},
  "quality": "high"
}
```

Сохраните `instance_id` как `{{INSTANCE_ID}}`

#### 5️⃣ Проверить статус сессии
```bash
GET {{BASE_URL}}/api/instances/{{INSTANCE_ID}}
Authorization: Bearer {{TOKEN}}
```

Дождитесь `status: "ready"`

#### 6️⃣ Тестировать управление
```bash
POST {{BASE_URL}}/api/instances/{{INSTANCE_ID}}/input/keyboard
Authorization: Bearer {{TOKEN}}
{
  "key": "KeyW",
  "pressed": true
}
```

#### 7️⃣ Получить статистику
```bash
GET {{BASE_URL}}/api/instances/{{INSTANCE_ID}}/stats
Authorization: Bearer {{TOKEN}}
```

#### 8️⃣ Остановить сессию
```bash
DELETE {{BASE_URL}}/api/instances/{{INSTANCE_ID}}
Authorization: Bearer {{TOKEN}}
```

---

## 🔍 Проверка интеграции в браузере

### Откройте консоль разработчика (F12)

#### Тест 1: Проверить загрузку сервисов
```javascript
// В console перейдите в App
console.log('API Loaded:', typeof api !== 'undefined');
console.log('StreamingClient Loaded:', typeof StreamingClient !== 'undefined');
console.log('InputManager Loaded:', typeof InputManager !== 'undefined');
```

#### Тест 2: Проверить сохранение токена
```javascript
// Войдите в приложение, затем проверьте
localStorage.getItem('cloudgaming_token');
```

#### Тест 3: Отправить игровой ввод
```javascript
// Во время игровой сессии
api.sendKeyboardInput('KeyW', true).then(() => console.log('Input sent'));
```

#### Тест 4: Проверить WebRTC подключение
```javascript
// Проверить состояние подключения
console.log('WebRTC state:', streamClient?.peerConnection?.connectionState);
```

---

## 📊 Мониторинг в DevTools

### Network вкладка
- Проверить все запросы API
- Убедиться, что Authorization header присутствует
- Проверить время отклика (должно быть < 500ms)
- Посмотреть логи WebSocket подключения

### Performance вкладка
- Записать игровую сессию 60 секунд
- Проверить FPS графику
- Идеально: 55-60 FPS стабильно
- Предупреждение: если падает ниже 30 FPS

### Application вкладка
- **Storage > LocalStorage** - проверить токен и настройки
- **Storage > Cookies** - если используются куки
- **Cache Storage** - для offline поддержки (будущее)

---

## 🐛 Типичные ошибки и решение

### 401 Unauthorized
```
Проблема: Токен истёк или отсутствует
Решение: Повторно войдите в приложение
Код: api.logout(); showLoginScreen();
```

### 500 Internal Server Error
```
Проблема: Ошибка на сервере
Решение: Проверить логи бэкенда
Код: docker logs backend
```

### WebRTC Connection Failed
```
Проблема: Не удалось подключиться к видеопотоку
Решение: 
1. Проверить firewall
2. Проверить сетевое подключение
3. Убедиться что сессия полностью запущена (status="ready")
```

### Timeout при создании сессии
```
Проблема: Сессия слишком долго запускается
Решение: Увеличить лимит времени или выбрать другой регион
```

---

## 📊 Пример Postman Collection

Создайте файл `CloudGaming.postman_collection.json`:

```json
{
  "info": {
    "name": "CloudGaming API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Register",
          "request": {
            "method": "POST",
            "url": "{{BASE_URL}}/api/auth/register",
            "body": {
              "mode": "raw",
              "raw": "{\"username\":\"{{USERNAME}}\",\"email\":\"{{EMAIL}}\",\"password\":\"{{PASSWORD}}\"}"
            }
          }
        },
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "url": "{{BASE_URL}}/api/auth/login",
            "body": {
              "mode": "raw",
              "raw": "{\"username\":\"{{USERNAME}}\",\"password\":\"{{PASSWORD}}\"}"
            }
          }
        }
      ]
    },
    {
      "name": "Games",
      "item": [
        {
          "name": "Get Games",
          "request": {
            "method": "GET",
            "url": "{{BASE_URL}}/api/games",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{TOKEN}}"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

Импортируйте в Postman: **File → Import**

---

## 🚀 Вывод в production

### Перед развёртыванием проверьте:

- [ ] Все API endpoints возвращают корректные коды ошибок
- [ ] CORS настроен правильно (Access-Control-Allow-Origin)
- [ ] JWT токены подписаны и проверяются
- [ ] WebRTC работает через HTTPS (требование для видео)
- [ ] Геймпады работают во всех браузерах
- [ ] Нет XSS или CSRF уязвимостей
- [ ] Token refresh реализован
- [ ] Обработка сетевых ошибок

---

**Версия:** 1.0.0  
**Дата:** 2026-02-28
