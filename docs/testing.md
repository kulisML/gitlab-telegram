# Тестирование

## Запуск полного тест-набора

Убедитесь, что бот запущен (`python main.py`), затем:

```bash
python tests/test_webhook.py
```

Скрипт отправит **9 тестовых событий** (по одному на каждый тип) и выведет результат.

**Ожидаемый вывод:**
```
=======================================================
  GitLab → Telegram Bot — Тестовый набор Webhook
=======================================================
✅ Health check пройден: {"status":"healthy","bot_initialized":true}

Отправляю 9 тестовых событий...

  ✅ [Push (коммиты в main)]       → 200 {"status":"ok"}
  ✅ [Tag Push (новый тег v1.0.0)] → 200 {"status":"ok"}
  ✅ [Merge Request (открыт)]      → 200 {"status":"ok"}
  ✅ [Pipeline FAILED]             → 200 {"status":"ok"}
  ✅ [Pipeline SUCCESS]            → 200 {"status":"ok"}
  ✅ [Issue (открыт)]              → 200 {"status":"ok"}
  ✅ [Comment / Note]              → 200 {"status":"ok"}
  ✅ [Job FAILED]                  → 200 {"status":"ok"}
  ✅ [Wiki Page (создана)]         → 200 {"status":"ok"}

✔  Готово! Проверьте Telegram — все уведомления должны прийти.
```

---

## Ручное тестирование через curl

```bash
# Push событие
curl -X POST http://localhost:80/tgbotgit \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: MySecret123" \
  -d '{
    "object_kind": "push",
    "user_name": "test_user",
    "ref": "refs/heads/main",
    "project": {"name": "TestProject", "web_url": "https://gitlab.com/test"},
    "commits": [{"id": "abc123def456", "message": "test commit", "url": "https://gitlab.com/test/-/commit/abc123"}]
  }'
```

---

## Health check

```bash
curl http://localhost:80/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "bot_initialized": true,
  "data_dir": "data/webhooks",
  "version": "2.0.0"
}
```

---

## Тест через GitLab

В настройках Webhook GitLab (**Settings → Webhooks**) нажмите **Test** рядом с нужным webhook и выберите тип события. GitLab отправит реальный тестовый payload.
