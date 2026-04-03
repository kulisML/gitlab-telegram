# Инструкция по настройке и запуску

## Шаг 1: Настройка бота в Telegram

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram.
2. Создайте нового бота (`/newbot`) и получите `API TOKEN`.
3. Создайте группу (или используйте существующую) и добавьте в неё бота.
4. Узнайте `CHAT_ID` вашей группы (через [@userinfobot](https://t.me/userinfobot) или посмотрев `id` в ответе `https://api.telegram.org/bot<TOKEN>/getUpdates` после того, как кто-то напишет в группу).

## Шаг 2: Настройка переменных окружения

Создайте файл `.env` в корневой директории проекта и скопируйте туда содержимое из `.env.example`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_CHAT_ID=-100123456789
GITLAB_SECRET_TOKEN=my_secret_key
```

## Шаг 3: Запуск сервера

Для запуска в контейнере Docker:

```bash
docker-compose up -d --build
```

Для локального запуска (нужен Python 3.10+):

```bash
pip install -r requirements.txt
python main.py
```

## Шаг 4: Настройка вебхука в GitLab

1. Перейдите в ваш проект GitLab -> **Settings** -> **Webhooks**.
2. Укажите в поле **URL**: `http://<ВАШ_IP_ИЛИ_ДОМЕН>:8000/gitlab`.
3. В поле **Secret token** укажите тот же ключ, что и в `.env` (`GITLAB_SECRET_TOKEN`).
4. Выберите события (**Trigger**):
   - Push events
   - Issue events
   - Merge request events
   - Note events (comments)
   - Pipeline events
5. Нажмите **Add webhook**.

---

### Тестирование
Вы можете нажать кнопку **Test** рядом с созданным вебхуком в GitLab, чтобы проверить доставку уведомлений.

⚠️ **Важно:** Бот должен быть доступен по внешней ссылке. Если вы запускаете его локально для теста, используйте [ngrok](https://ngrok.com/) или [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/).
