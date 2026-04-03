import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "bot.db"


async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT,
                gitlab_username TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                project TEXT,
                actor_gitlab TEXT,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Дефолтные настройки
        defaults = [
            ("report_time", "09:00"),
            ("enabled_events", "push,tag_push,merge_request,pipeline,issue,note,build,wiki_page"),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()
    logger.info("Database initialized: %s", DB_PATH)


# ── Users ──────────────────────────────────────────────────────────────────

async def upsert_user(telegram_id: int, telegram_username: str, gitlab_username: str = None):
    """Добавить или обновить пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, telegram_username, gitlab_username)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                telegram_username = excluded.telegram_username,
                gitlab_username = COALESCE(excluded.gitlab_username, gitlab_username)
        """, (telegram_id, telegram_username, gitlab_username))
        await db.commit()


async def get_user_by_gitlab(gitlab_username: str) -> dict | None:
    """Найти Telegram-пользователя по GitLab-логину."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE LOWER(gitlab_username) = LOWER(?)",
            (gitlab_username,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_users() -> list[dict]:
    """Список всех зарегистрированных пользователей."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY registered_at") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def set_user_gitlab(telegram_id: int, gitlab_username: str):
    """Привязать GitLab username к пользователю."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET gitlab_username = ? WHERE telegram_id = ?",
            (gitlab_username, telegram_id)
        )
        await db.commit()


# ── Events ─────────────────────────────────────────────────────────────────

async def save_event(event_type: str, project: str, actor_gitlab: str, data_json: str):
    """Сохранить событие GitLab в БД."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events (event_type, project, actor_gitlab, data_json) VALUES (?, ?, ?, ?)",
            (event_type, project, actor_gitlab, data_json)
        )
        await db.commit()


async def get_recent_events(limit: int = 10) -> list[dict]:
    """Последние N событий."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_daily_stats(date: str = None) -> dict:
    """
    Статистика за указанную дату (YYYY-MM-DD).
    Если date не указан — берём сегодня.
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Коммиты по разработчикам
        async with db.execute("""
            SELECT actor_gitlab, COUNT(*) as cnt
            FROM events
            WHERE event_type = 'push'
              AND DATE(created_at) = ?
              AND actor_gitlab IS NOT NULL
            GROUP BY actor_gitlab
            ORDER BY cnt DESC
        """, (date,)) as cur:
            commits_by_user = {r["actor_gitlab"]: r["cnt"] for r in await cur.fetchall()}

        # Pipeline статистика
        async with db.execute("""
            SELECT
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.status')='success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.status')='failed'  THEN 1 ELSE 0 END) as failed,
                COUNT(*) as total
            FROM events
            WHERE event_type = 'pipeline' AND DATE(created_at) = ?
        """, (date,)) as cur:
            pipeline_row = await cur.fetchone()
            pipelines = dict(pipeline_row) if pipeline_row else {"success": 0, "failed": 0, "total": 0}

        # Merge Requests
        async with db.execute("""
            SELECT
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.action')='open'  THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.action')='merge' THEN 1 ELSE 0 END) as merged,
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.action')='close' THEN 1 ELSE 0 END) as closed
            FROM events
            WHERE event_type = 'merge_request' AND DATE(created_at) = ?
        """, (date,)) as cur:
            mr_row = await cur.fetchone()
            mr = dict(mr_row) if mr_row else {"opened": 0, "merged": 0, "closed": 0}

        # Issues
        async with db.execute("""
            SELECT
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.action')='open'  THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN json_extract(data_json,'$.object_attributes.action')='close' THEN 1 ELSE 0 END) as closed
            FROM events
            WHERE event_type = 'issue' AND DATE(created_at) = ?
        """, (date,)) as cur:
            issue_row = await cur.fetchone()
            issues = dict(issue_row) if issue_row else {"opened": 0, "closed": 0}

        return {
            "date": date,
            "commits_by_user": commits_by_user,
            "pipelines": pipelines,
            "mr": mr,
            "issues": issues,
        }


# ── Settings ───────────────────────────────────────────────────────────────

async def get_setting(key: str, default: str = "") -> str:
    """Получить значение настройки."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    """Сохранить настройку."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        await db.commit()
