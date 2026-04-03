# Развёртывание на сервере

Руководство по запуску бота в production-режиме на Linux-сервере (Ubuntu/Debian).

---

## Вариант 1: systemd (рекомендуется)

`systemd` — это встроенный менеджер служб Linux. Он автоматически перезапускает бота при падении и запускает его после перезагрузки сервера.

### Шаг 1. Загрузите проект на сервер

```bash
# Через git
git clone https://github.com/YOUR_USERNAME/gitlab-telegram-bot.git /opt/gitlab-telegram-bot
cd /opt/gitlab-telegram-bot

# Или через scp с локального компьютера
scp -r ./gitlab-telegram-bot user@your-server:/opt/
```

### Шаг 2. Установите Python и зависимости

```bash
# Установка Python 3.10+
sudo apt update && sudo apt install python3.10 python3-pip -y

# Установка зависимостей
cd /opt/gitlab-telegram-bot
pip3 install -r requirements.txt
```

### Шаг 3. Настройте `.env`

```bash
cp .env.example .env
nano .env  # Заполните TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID и т.д.
```

### Шаг 4. Создайте systemd-службу

```bash
sudo nano /etc/systemd/system/gitlab-bot.service
```

Вставьте:

```ini
[Unit]
Description=GitLab → Telegram Notification Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/gitlab-telegram-bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Шаг 5. Запустите службу

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitlab-bot    # автозапуск при ребуте
sudo systemctl start gitlab-bot

# Проверить статус
sudo systemctl status gitlab-bot

# Смотреть логи в реальном времени
sudo journalctl -u gitlab-bot -f
```

---

## Вариант 2: NGrok (быстро, для тестов)

NGrok создаёт публичный HTTPS-туннель к вашему локальному серверу. Полезно, если нет белого IP или нужно быстро протестировать.

1. [Зарегистрируйтесь на ngrok.com](https://ngrok.com/) и получите Auth Token
2. Скачайте `ngrok.exe` (Windows) или установите через `apt`
3. Настройте токен:
   ```bash
   ./ngrok config add-authtoken ВАШ_ТОКЕН
   ```
4. Запустите туннель:
   ```bash
   ./ngrok http 80
   ```
5. Скопируйте URL вида `https://xxxx.ngrok-free.app` и вставьте в GitLab Webhook

> ⚠️ URL меняется при каждом перезапуске NGrok (на бесплатном плане). Обновляйте URL в GitLab после каждого перезапуска.

---

## Вариант 3: Nginx как обратный прокси

Если у вас уже есть Nginx — можно запустить бота на порту 8000 и проксировать через Nginx.

Конфигурация Nginx (`/etc/nginx/sites-available/gitlab-bot`):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /tgbotgit {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Gitlab-Token $http_x_gitlab_token;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

В `.env` установите:
```env
APP_PORT=8000
```

---

## Перенос данных на новый сервер

Для переноса бота со всей историей и настройками:

```bash
# На старом сервере
scp bot.db user@new-server:/opt/gitlab-telegram-bot/

# Также перенесите .env
scp .env user@new-server:/opt/gitlab-telegram-bot/
```

---

## Мониторинг

### Проверка работоспособности

```bash
curl http://localhost:80/health
# {"status":"healthy","bot_initialized":true,"version":"2.0.0"}
```

### Просмотр логов

```bash
# systemd
sudo journalctl -u gitlab-bot -n 100

# Без systemd
tail -f bot.log
```

### Проверка наличия записей в БД

```bash
sqlite3 bot.db "SELECT COUNT(*), event_type FROM events GROUP BY event_type;"
```
