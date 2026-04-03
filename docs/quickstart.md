# Быстрый старт

Эта страница поможет запустить бота за 5 минут.

## Предварительные требования

| Что нужно | Где получить |
|-----------|-------------|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) |
| **Telegram Bot Token** | [@BotFather](https://t.me/BotFather) → `/newbot` |
| **Telegram Chat ID** | см. [Как найти Chat ID](#как-найти-chat-id) |
| **GitLab-репозиторий** | с правами на настройку Webhooks |

---

## Шаг 1. Клонируйте репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/gitlab-telegram-bot.git
cd gitlab-telegram-bot
```

## Шаг 2. Установите зависимости

```bash
pip install -r requirements.txt
```

## Шаг 3. Создайте файл `.env`

```bash
cp .env.example .env
```

Откройте `.env` и заполните обязательные поля:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAExample...
TELEGRAM_CHAT_ID=1196267761
GITLAB_SECRET_TOKEN=MySecret123
APP_PORT=80
```

> Полное описание всех переменных: [Конфигурация](./configuration.md)

## Шаг 4. Запустите бота

```bash
python main.py
```

Вы увидите:
```
✅ Database initialized: bot.db
✅ FastAPI: http://0.0.0.0:80
✅ Telegram bot polling — активен
✅ Scheduler started. Daily report at 09:00
```

## Шаг 5. Настройте GitLab Webhook

1. Откройте ваш GitLab репозиторий
2. Перейдите в **Settings → Webhooks → Add new webhook**
3. Укажите URL: `http://ВАШ_IP/tgbotgit`
4. Укажите **Secret token**: значение из `GITLAB_SECRET_TOKEN`
5. Выберите нужные события
6. Нажмите **Add webhook**, затем **Test**

> Если сервер за NAT/firewall — используйте [NGrok](./ngrok-setup.md)

## Шаг 6. Зарегистрируйтесь в боте

Напишите в Telegram-чате:
```
/tgbot
```

Бот запомнит ваш Telegram ID и покажет панель управления. Нажмите **«🔗 Мой GitLab»** и введите ваш GitLab username — бот начнёт делать @упоминания при событиях.

---

## Как найти Chat ID

### Личный чат
1. Напишите боту любое сообщение
2. Перейдите в браузере: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Найдите поле `"chat": {"id": 123456789}`

### Группа или канал
1. Добавьте бота в группу, напишите любое сообщение
2. Перейдите: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. ID группы начинается с `-100` (например `-1001234567890`)

### Через @userinfobot
Напишите [@userinfobot](https://t.me/userinfobot) — он вернёт ваш personal ID.
