"""
Планировщик ежедневных отчётов.
Использует APScheduler для отправки отчёта в Telegram в настроенное время.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.bot import bot
from core.config import config
from core import database as db

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def send_daily_report():
    """Формирует и отправляет ежедневный отчёт в Telegram."""
    logger.info("Sending daily report...")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    stats = await db.get_daily_stats(yesterday)
    all_users = await db.get_all_users()
    gitlab_to_tg = {u["gitlab_username"]: u for u in all_users if u.get("gitlab_username")}

    lines = [f"📊 <b>Ежедневный отчёт — {yesterday}</b>\n"]

    # Активность разработчиков
    lines.append("👨‍💻 <b>Активность команды:</b>")
    if stats["commits_by_user"]:
        # Лидер
        leader_gl = max(stats["commits_by_user"], key=stats["commits_by_user"].get)
        leader_cnt = stats["commits_by_user"][leader_gl]
        leader_tg_user = gitlab_to_tg.get(leader_gl)
        leader_name = (f"@{leader_tg_user['telegram_username']}"
                       if leader_tg_user and leader_tg_user.get("telegram_username")
                       else leader_gl)
        for gl_user, cnt in stats["commits_by_user"].items():
            tg = gitlab_to_tg.get(gl_user)
            mention = f"@{tg['telegram_username']}" if tg and tg.get("telegram_username") else gl_user
            lines.append(f"  • {mention} — {cnt} коммит(ов)")
    else:
        lines.append("  • Коммитов не было")
        leader_name = None
        leader_cnt = 0

    # Нет активности
    active = set(stats["commits_by_user"].keys())
    inactive = [u for u in all_users if u.get("gitlab_username") and u["gitlab_username"] not in active]
    for u in inactive:
        mention = f"@{u['telegram_username']}" if u.get("telegram_username") else u["gitlab_username"]
        lines.append(f"  • {mention} — 0 коммитов ⚠️")

    # CI/CD
    p = stats["pipelines"]
    lines.append(f"\n🚦 <b>CI/CD пайплайны:</b>")
    lines.append(f"  • Всего: {p['total']} | ✅ {p['success']} | ❌ {p['failed']}")

    # MR
    mr = stats["mr"]
    lines.append(f"\n🔀 <b>Merge Requests:</b>")
    lines.append(f"  • Открыто: {mr['opened']} | Смёрджено: {mr['merged']} | Закрыто: {mr['closed']}")

    # Issues
    iss = stats["issues"]
    lines.append(f"\n📋 <b>Задачи (Issues):</b>")
    lines.append(f"  • Открыто: {iss['opened']} | Закрыто: {iss['closed']}")

    # Лидер дня
    if leader_name and leader_cnt > 0:
        lines.append(f"\n🏆 <b>Лидер дня:</b> {leader_name} — {leader_cnt} коммит(ов)!")

    message = "\n".join(lines)

    try:
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info("Daily report sent successfully.")
    except Exception as e:
        logger.error("Failed to send daily report: %s", e)


async def reschedule_report(time_str: str):
    """Перепланировать отчёт на новое время (ЧЧ:ММ)."""
    try:
        hour, minute = map(int, time_str.split(":"))
        if scheduler.get_job("daily_report"):
            scheduler.remove_job("daily_report")
        scheduler.add_job(
            send_daily_report,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_report",
            replace_existing=True,
        )
        logger.info("Daily report rescheduled to %s", time_str)
    except Exception as e:
        logger.error("Failed to reschedule report: %s", e)


async def start_scheduler():
    """Запустить планировщик с настроенным временем из БД."""
    report_time = await db.get_setting("report_time", "09:00")
    hour, minute = map(int, report_time.split(":"))
    scheduler.add_job(
        send_daily_report,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_report",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started. Daily report at %s", report_time)
