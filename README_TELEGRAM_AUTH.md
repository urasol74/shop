# Авторизация через Telegram Mini App

Этот проект реализует авторизацию пользователей через Telegram Mini App без необходимости регистрации.

## Как это работает

1. **Пользователь открывает Mini App** из Telegram-бота
2. **Telegram передает данные** пользователя в `initData`:
   - `id` - Telegram ID пользователя
   - `first_name`, `last_name` - имя и фамилия
   - `username` - username пользователя
   - `auth_date`, `hash` - для проверки подлинности данных
3. **Сервер проверяет подпись** по токену бота
4. **Создается сессия** для авторизованного пользователя

## Структура проекта

```
shop/
├── app.py                 # Flask приложение с API авторизации
├── static/
│   └── script.js         # JavaScript для работы с Telegram
├── templates/
│   ├── index.html        # Главная страница с авторизацией
│   └── test_auth.html    # Страница для тестирования
└── README_TELEGRAM_AUTH.md

shop-bot/
└── shop-bot.py           # Telegram бот
```

## API Endpoints

### Авторизация
- `POST /api/auth/telegram` - авторизация через Telegram
- `GET /api/auth/status` - проверка статуса авторизации
- `GET /api/auth/logout` - выход из системы

### Тестирование
- `GET /test-auth` - страница для тестирования авторизации

## Настройка

### 1. Токен бота
В файле `app.py` замените токен на ваш:
```python
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
```

### 2. Секретный ключ Flask
В файле `app.py` замените секретный ключ:
```python
app.secret_key = 'your-secret-key-here-change-this-in-production'
```

### 3. URL Mini App
В файле `shop-bot.py` укажите правильный URL вашего сайта:
```python
webapp_url = "https://your-domain.com/"
```

## Использование

### Запуск Flask приложения
```bash
cd shop
python app.py
```

### Запуск Telegram бота
```bash
cd shop-bot
python shop-bot.py
```

### Тестирование
1. Откройте бота в Telegram
2. Отправьте команду `/start`
3. Нажмите кнопку "Открыть Benetton Shop"
4. Или перейдите на `/test-auth` для тестирования

## Безопасность

- **Проверка подписи**: Все данные от Telegram проверяются по HMAC-SHA256
- **Сессии**: Используются Flask сессии для хранения состояния авторизации
- **Токены**: Токен бота хранится в переменных окружения (рекомендуется)

## JavaScript API

### Получение данных пользователя
```javascript
// Проверка авторизации
if (window.TelegramAuth && window.TelegramAuth.isUserAuthenticated()) {
    const userId = window.TelegramAuth.getUserId();
    console.log('Пользователь авторизован:', userId);
}
```

### Отправка данных на сервер
```javascript
// Автоматически выполняется при загрузке страницы
// Данные отправляются на /api/auth/telegram
```

## Примеры использования

### Проверка авторизации в других скриптах
```javascript
// В любом JavaScript файле
if (window.TelegramAuth && window.TelegramAuth.isUserAuthenticated()) {
    // Пользователь авторизован
    const userData = window.TelegramAuth.userData;
    console.log('Добро пожаловать,', userData.first_name);
} else {
    // Пользователь не авторизован
    console.log('Необходимо авторизоваться');
}
```

### Защита функционала
```javascript
function protectedFunction() {
    if (!window.TelegramAuth || !window.TelegramAuth.isUserAuthenticated()) {
        alert('Необходимо авторизоваться');
        return;
    }
    
    // Выполняем защищенную функцию
    console.log('Функция выполнена для пользователя:', window.TelegramAuth.getUserId());
}
```

## Устранение неполадок

### Проблема: Данные пользователя не получаются
**Решение**: Проверьте, что Mini App открывается из Telegram, а не в обычном браузере

### Проблема: Ошибка проверки подписи
**Решение**: Убедитесь, что токен бота в `app.py` совпадает с токеном в `shop-bot.py`

### Проблема: Сессии не сохраняются
**Решение**: Проверьте, что установлен секретный ключ Flask и включены сессии

## Дополнительные возможности

### Сохранение пользователей в базе данных
Можно расширить функционал, добавив модель User в `models.py`:

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    username = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Аналитика и статистика
Добавить отслеживание:
- Количество авторизаций
- Время пребывания на сайте
- Просмотренные товары
- Корзина и заказы

## Поддержка

При возникновении проблем:
1. Проверьте логи Flask приложения
2. Проверьте логи Telegram бота
3. Используйте страницу `/test-auth` для отладки
4. Проверьте консоль браузера на ошибки JavaScript
