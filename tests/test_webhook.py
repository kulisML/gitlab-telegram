# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
Тесты webhook-событий GitLab.
Запуск: python tests/test_webhook.py
Убедитесь, что бот запущен на порту 80 (или измените BASE_URL).
"""
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:80/tgbotgit"
SECRET_TOKEN = "MySecret123"

HEADERS = {
    "Content-Type": "application/json",
    "X-Gitlab-Token": SECRET_TOKEN,
}

# --- Тестовые payload-данные ---

PUSH_EVENT = {
    "object_kind": "push",
    "user_name": "Иван Иванов",
    "ref": "refs/heads/main",
    "project": {"name": "MyProject", "web_url": "https://gitlab.com/myorg/myproject"},
    "commits": [
        {"id": "abc123def456", "message": "feat: добавлена новая функция\n\nПодробное описание", "url": "https://gitlab.com/myorg/myproject/-/commit/abc123"},
        {"id": "789xyz000aaa", "message": "fix: исправлена ошибка в конфигурации", "url": "https://gitlab.com/myorg/myproject/-/commit/789xyz"},
    ],
}

TAG_PUSH_EVENT = {
    "object_kind": "tag_push",
    "user_name": "Иван Иванов",
    "ref": "refs/tags/v1.0.0",
    "message": "Релиз версии 1.0.0 — стабильная версия",
    "project": {"name": "MyProject", "web_url": "https://gitlab.com/myorg/myproject"},
}

MERGE_REQUEST_EVENT = {
    "object_kind": "merge_request",
    "user": {"name": "Мария Петрова"},
    "project": {"name": "MyProject", "web_url": "https://gitlab.com/myorg/myproject"},
    "object_attributes": {
        "action": "open",
        "title": "Добавить авторизацию через OAuth",
        "url": "https://gitlab.com/myorg/myproject/-/merge_requests/42",
    },
}

PIPELINE_FAILED_EVENT = {
    "object_kind": "pipeline",
    "project": {"name": "MyProject", "web_url": "https://gitlab.com/myorg/myproject"},
    "object_attributes": {
        "id": 999,
        "status": "failed",
        "ref": "main",
    },
}

PIPELINE_SUCCESS_EVENT = {
    "object_kind": "pipeline",
    "project": {"name": "MyProject", "web_url": "https://gitlab.com/myorg/myproject"},
    "object_attributes": {
        "id": 1000,
        "status": "success",
        "ref": "feature/auth",
    },
}

ISSUE_EVENT = {
    "object_kind": "issue",
    "user": {"name": "Алексей Сидоров"},
    "project": {"name": "MyProject"},
    "object_attributes": {
        "action": "open",
        "title": "Падает сервис при старте в продакшене",
        "url": "https://gitlab.com/myorg/myproject/-/issues/15",
    },
}

COMMENT_EVENT = {
    "object_kind": "note",
    "user": {"name": "Оля Зайцева"},
    "project": {"name": "MyProject"},
    "object_attributes": {
        "note": "Отличная работа! Код выглядит чисто, можно мержить. Только проверьте unit-тесты перед слиянием.",
        "url": "https://gitlab.com/myorg/myproject/-/merge_requests/42#note_123",
    },
}

JOB_FAILED_EVENT = {
    "object_kind": "build",
    "build_status": "failed",
    "build_name": "test:unit",
    "build_id": 777,
    "project_name": "MyProject",
    "user": {"name": "CI Runner"},
    "project": {"web_url": "https://gitlab.com/myorg/myproject"},
}

WIKI_EVENT = {
    "object_kind": "wiki_page",
    "user": {"name": "Дмитрий Козлов"},
    "project": {"name": "MyProject"},
    "object_attributes": {
        "action": "create",
        "title": "Руководство по деплою",
        "url": "https://gitlab.com/myorg/myproject/-/wikis/deploy-guide",
    },
}


def send_event(name: str, payload: dict):
    """Отправляет тестовое событие на endpoint бота."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            print(f"  ✅ [{name}] → {resp.status} {body}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ [{name}] → HTTP {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"  ❌ [{name}] → Ошибка: {e}")


def run_health_check():
    """Проверка доступности бота."""
    try:
        url = BASE_URL.replace("/tgbotgit", "/health")
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode()
            print(f"✅ Health check пройден: {body}\n")
            return True
    except Exception as e:
        print(f"❌ Бот недоступен: {e}")
        print(f"   Убедитесь, что бот запущен: python main.py\n")
        return False


if __name__ == "__main__":
    print("=" * 55)
    print("  GitLab → Telegram Bot — Тестовый набор Webhook")
    print("=" * 55)

    if not run_health_check():
        exit(1)

    tests = [
        ("Push (коммиты в main)",        PUSH_EVENT),
        ("Tag Push (новый тег v1.0.0)",  TAG_PUSH_EVENT),
        ("Merge Request (открыт)",       MERGE_REQUEST_EVENT),
        ("Pipeline FAILED",              PIPELINE_FAILED_EVENT),
        ("Pipeline SUCCESS",             PIPELINE_SUCCESS_EVENT),
        ("Issue (открыт)",               ISSUE_EVENT),
        ("Comment / Note",               COMMENT_EVENT),
        ("Job FAILED",                   JOB_FAILED_EVENT),
        ("Wiki Page (создана)",          WIKI_EVENT),
    ]

    print(f"Отправляю {len(tests)} тестовых событий на {BASE_URL}...\n")
    for name, payload in tests:
        send_event(name, payload)

    print("\n✔  Готово! Проверьте Telegram — все уведомления должны прийти.")
