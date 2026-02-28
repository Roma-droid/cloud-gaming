# 📚 Примеры использования API и сервисов

## 🔐 APIService - Работа с бэкендом

### Инициализация
```javascript
import { api } from './services/api.js';

// API автоматически инициализируется при импорте
// Использует localStorage для хранения токена
```

### Аутентификация

#### Регистрация
```javascript
try {
    const response = await api.register({
        username: 'john_doe',
        email: 'john@example.com',
        password: 'securePassword123'
    });
    
    console.log('Пользователь создан:', response.user_id);
    notificationManager.success('Регистрация успешна!');
} catch (error) {
    console.error('Ошибка регистрации:', error);
    notificationManager.error(`Ошибка: ${error.message}`);
}
```

#### Вход
```javascript
try {
    const response = await api.login({
        username: 'john_doe',
        password: 'securePassword123'
    });
    
    console.log('Токен получен:', response.access_token);
    console.log('Тип токена:', response.token_type); // "bearer"
    
    // Токен автоматически сохраняется в localStorage
    notificationManager.success('Вы вошли в аккаунт');
} catch (error) {
    notificationManager.error('Ошибка входа. Проверьте учётные данные');
}
```

#### Выход
```javascript
api.logout();
notificationManager.info('Вы вышли из аккаунта');
// Токен удалён из localStorage
```

---

### Управление играми

#### Получить список игр
```javascript
async function loadGames() {
    try {
        const games = await api.getGames();
        
        // Результат:
        // [
        //     {
        //         id: 1,
        //         name: "Minecraft",
        //         description: "...",
        //         genre: "Sandbox",
        //         icon: "🎮"
        //     },
        //     ...
        // ]
        
        console.log(`Загружено ${games.length} игр`);
        renderGameLibrary(games);
    } catch (error) {
        notificationManager.error('Не удалось загрузить игры');
    }
}
```

#### Создать игровую сессию
```javascript
async function launchGame(gameId) {
    try {
        const response = await api.createGameInstance({
            game_id: gameId,
            region: 'eu-west-1', // опционально
            quality: 'high'       // опционально
        });
        
        // Результат:
        // {
        //     instance_id: "abc123def456",
        //     game_id: 1,
        //     status: "starting",
        //     server_url: "wss://game-server.com:8080"
        // }
        
        console.log('Экземпляр игры создан:', response.instance_id);
        
        // Сохраняем ID для последующих операций
        currentInstanceId = response.instance_id;
        
        // Подожди, пока сервер готов
        await waitForInstanceReady(response.instance_id);
        
    } catch (error) {
        notificationManager.error('Ошибка при запуске игры');
    }
}

async function waitForInstanceReady(instanceId, maxWait = 30000) {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWait) {
        try {
            const status = await api.getInstanceStatus(instanceId);
            if (status.status === 'ready') {
                return;
            }
        } catch (e) {
            // Продолжаем ждать
        }
        await new Promise(r => setTimeout(r, 1000));
    }
    throw new Error('Сессия не запустилась');
}
```

#### Остановить игровую сессию
```javascript
async function stopGameSession(instanceId) {
    try {
        const response = await api.stopGameInstance(instanceId);
        console.log('Сессия остановлена:', response.status);
        notificationManager.success('Игра остановлена');
    } catch (error) {
        notificationManager.error('Ошибка при остановке игры');
    }
}
```

---

## 🎥 StreamingClient - WebRTC видеопоток

### Инициализация
```javascript
import { StreamingClient } from './services/webrtc.js';
import { api } from './services/api.js';

// Создание клиента
const streamClient = new StreamingClient(api);

// HTML элемент видео
const videoElement = document.getElementById('game-video');
```

### Подключение к потоку
```javascript
async function startStreaming(instanceId) {
    try {
        // Подключаемся к потоку
        await streamClient.connect(instanceId, videoElement);
        
        console.log('Поток открыт');
        notificationManager.success('Видеопоток подключен');
        
        // Видео теперь отображается в videoElement
        
    } catch (error) {
        notificationManager.error('Ошибка подключения к потоку');
    }
}
```

### Мониторинг качества потока
```javascript
// Получить статистику потока
const stats = await streamClient.getStats();
console.log(`
    FPS: ${stats.fps}
    Bitrate: ${stats.bitrate} kbps
    Разрешение: ${stats.resolution}
    Задержка: ${stats.latency} ms
`);

// Отобразить статистику на UI
updateStreamStats({
    fps: stats.fps,
    bitrate: Math.round(stats.bitrate),
    resolution: stats.resolution,
    latency: stats.latency
});
```

### Изменение качества потока
```javascript
async function setStreamQuality(quality) {
    try {
        // Доступные: 'low', 'medium', 'high', 'ultra'
        await streamClient.setQuality(quality);
        notificationManager.success(`Качество установлено: ${quality}`);
    } catch (error) {
        notificationManager.error('Ошибка изменения качества');
    }
}
```

### Переподключение при разрыве
```javascript
async function handleStreamDisconnection(instanceId) {
    try {
        notificationManager.warning('Переподключение...');
        await streamClient.reconnect(instanceId, videoElement);
        notificationManager.success('Переподключено');
    } catch (error) {
        notificationManager.error('Не удалось переподключиться');
    }
}
```

### Отключение потока
```javascript
function stopStreaming() {
    streamClient.disconnect();
    console.log('Поток отключен');
}
```

---

## ⌨️ InputManager - Управление входом

### Инициализация
```javascript
import { InputManager } from './services/input.js';
import { api } from './services/api.js';

// Создание менеджера входа
const inputManager = new InputManager(api);

// HTML элемент для фокуса ввода
const gameContainer = document.getElementById('game-container');
```

### Активация управления
```javascript
function startGameplay(instanceId) {
    // Зарегистрировать сессию для отправки входа
    inputManager.setCurrentInstance(instanceId);
    
    // Собрать слушатели событий (клавиши, мышь, геймпад)
    inputManager.setupListeners(gameContainer);
    
    console.log('Управление активировано');
}
```

### Примеры входа

#### Клавиатура
```javascript
// Автоматически обрабатывается InputManager
// При событии keydown:
// - ArrowUp, ArrowDown, ArrowLeft, ArrowRight
// - WASD для движения
// - Space для прыжка
// - Ctrl для спринта
// - E для взаимодействия

// Пример отправки входа напрямую:
inputManager.sendKeyboardInput('KeyW', true);  // нажата
inputManager.sendKeyboardInput('KeyW', false); // отпущена
```

#### Мышь
```javascript
// Автоматически отслеживается
// При движении мыши отправляется:
inputManager.sendMouseInput({
    x: 640,        // экранные координаты X
    y: 360,        // экранные координаты Y
    button: 'left' // 'left', 'right', 'middle'
});
```

#### Геймпад
```javascript
// Автоматически опрашивается каждый 16ms
// Поддержка:
// - Два стика (левый/правый)
// - Четыре кнопки (A, B, X, Y)
// - Плечевые кнопки (LB, RB, LT, RT)
// - Крестовина (dpad)

// Геймпад подключается автоматически после setupListeners()
```

### Отключение управления
```javascript
function stopGameplay() {
    inputManager.cleanup();
    console.log('Управление отключено');
}
```

---

## 💬 Чат и сообщения

### Отправка сообщения в чат
```javascript
async function sendChatMessage(instanceId, message) {
    try {
        const response = await api.sendChatMessage(instanceId, {
            text: message,
            timestamp: new Date().toISOString()
        });
        
        console.log('Сообщение отправлено');
        
        // Добавить сообщение в UI чат
        addChatMessage({
            user: 'Вы',
            text: message,
            timestamp: new Date()
        });
        
    } catch (error) {
        notificationManager.error('Ошибка отправки сообщения');
    }
}

// Использование:
const chatInput = document.getElementById('chat-input');
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendChatMessage(currentInstanceId, e.target.value);
        e.target.value = '';
    }
});
```

---

## 📢 NotificationManager - Уведомления

### Различные типы уведомлений
```javascript
import { notificationManager } from './services/notifications.js';

// Успех
notificationManager.success('Операция выполнена!');

// Ошибка
notificationManager.error('Произошла ошибка');

// Предупреждение
notificationManager.warning('Будьте внимательны');

// Информация
notificationManager.info('Вот это информация');

// Общее уведомление с иконкой
notificationManager.show('Сообщение', 'info', 3000);
```

### Кастомное уведомление
```javascript
// Увеличить время отображения
notificationManager.info('Долгое сообщение', 5000);

// Автоматически закроется через 5 секунд
```

---

## 🎮 Полный пример игровой сессии

```javascript
// СЦЕНАРИЙ: Пользователь нажимает "Играть" на игре

// 1. Создание сессии
async function launchGameSession(game) {
    // Показать загрузку
    showLoadingOverlay('Запуск игры...');
    
    try {
        // Создать экземпляр игры
        const instance = await api.createGameInstance({
            game_id: game.id,
            quality: userSettings.quality || 'high'
        });
        
        currentInstanceId = instance.instance_id;
        updateStreamStats({ status: 'connecting' });
        
        // 2. Подключиться к видеопотоку
        const videoElement = document.getElementById('game-video');
        await streamClient.connect(instance.instance_id, videoElement);
        
        updateStreamStats({ status: 'connected' });
        
        // 3. Активировать управление
        const gameContainer = document.getElementById('game-screen');
        inputManager.setCurrentInstance(instance.instance_id);
        inputManager.setupListeners(gameContainer);
        
        // 4. Начать мониторинг качества
        startQualityMonitoring();
        
        // 5. Скрыть главный экран, показать игру
        hideLoadingOverlay();
        showGameScreen();
        
        notificationManager.success('Игра запущена!');
        
    } catch (error) {
        hideLoadingOverlay();
        notificationManager.error(`Ошибка: ${error.message}`);
        showGameLibrary();
    }
}

// Мониторинг качества потока
function startQualityMonitoring() {
    qualityMonitorInterval = setInterval(async () => {
        const stats = await streamClient.getStats();
        updateStreamStats(stats);
        
        // Если FPS слишком низкий, снизить качество
        if (stats.fps < 30 && currentQuality !== 'low') {
            await streamClient.setQuality('low');
            currentQuality = 'low';
        }
    }, 1000);
}

// СЦЕНАРИЙ: Пользователь выходит из игры

async function exitGameSession() {
    try {
        // 1. Остановить мониторинг
        clearInterval(qualityMonitorInterval);
        
        // 2. Отключить управление
        inputManager.cleanup();
        
        // 3. Отключить видеопоток
        streamClient.disconnect();
        
        // 4. Остановить экземпляр на сервере
        await api.stopGameInstance(currentInstanceId);
        
        currentInstanceId = null;
        
        // 5. Вернуться в библиотеку
        showGameLibrary();
        notificationManager.info('Игра закончена');
        
    } catch (error) {
        console.error('Ошибка при выходе:', error);
        // Даже при ошибке вернёмся в библиотеку
        showGameLibrary();
    }
}
```

---

## 🔄 Обработка ошибок

### Типовые ошибки

```javascript
// Ошибка аутентификации (401)
try {
    await api.getGames();
} catch (error) {
    if (error.message.includes('401')) {
        // Токен истёк или неверный
        api.logout();
        showLoginScreen();
        notificationManager.error('Сессия истекла. Пожалуйста, войдите заново');
    }
}

// Ошибка сервера (500)
try {
    await api.createGameInstance({...});
} catch (error) {
    if (error.message.includes('500')) {
        notificationManager.error('Ошибка сервера. Попробуйте позже');
    }
}

// Ошибка сети
try {
    await api.getGames();
} catch (error) {
    if (error.message.includes('Failed to fetch')) {
        notificationManager.error('Нет подключения к интернету');
    }
}
```

---

## ⚙️ Настройки приложения

```javascript
// Сохранение пользовательских настроек
const userSettings = {
    quality: 'high',           // low, medium, high, ultra
    enableSound: true,
    enableChat: true,
    controllerMode: 'standard' // standard, inverted
};

// Сохранить в localStorage
localStorage.setItem('cloudgaming_settings', JSON.stringify(userSettings));

// Загрузить настройки
function loadSettings() {
    const stored = localStorage.getItem('cloudgaming_settings');
    if (stored) {
        return JSON.parse(stored);
    }
    return userSettings; // значения по умолчанию
}
```

---

## 📊 Метрики и аналитика

```javascript
// Отслеживание использования
function trackEvent(eventName, details = {}) {
    const event = {
        name: eventName,
        timestamp: new Date().toISOString(),
        details
    };
    
    // Отправить на сервер аналитики
    fetch('/api/analytics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event)
    });
}

// Примеры события
trackEvent('game_launched', { gameId: 1, qualitySetting: 'high' });
trackEvent('stream_disconnected', { duration: 3600 });
trackEvent('controller_connected', { controllerType: 'xbox' });
```

---

**Версия:** 1.0.0  
**Дата:** 2026-02-28  
**Язык:** JavaScript ES6+
