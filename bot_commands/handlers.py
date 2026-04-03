"""
Telegram Bot command handlers.
/tgbot — главная команда для настройки бота и регистрации участников.
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from core import database as db
from core.config import config

logger = logging.getLogger(__name__)
router = Router()

# ── FSM States ─────────────────────────────────────────────────────────────

class RegistrationStates(StatesGroup):
    waiting_for_gitlab_username = State()

class SettingsStates(StatesGroup):
    waiting_for_report_time = State()
    waiting_for_map_username = State()


# ── Keyboards ──────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика сейчас", callback_data="stats_now"),
            InlineKeyboardButton(text="📜 Последние события", callback_data="event_log"),
        ],
        [
            InlineKeyboardButton(text="📅 Расписание отчёта", callback_data="set_schedule"),
            InlineKeyboardButton(text="🔔 Типы событий", callback_data="set_events"),
        ],
        [
            InlineKeyboardButton(text="👥 Участники команды", callback_data="team_list"),
            InlineKeyboardButton(text="🔗 Мой GitLab", callback_data="my_gitlab"),
        ],
    ])


def events_keyboard(enabled: list[str]) -> InlineKeyboardMarkup:
    all_events = [
        ("push", "🚀 Push"),
        ("tag_push", "🏷️ Tag Push"),
        ("merge_request", "🔀 Merge Request"),
        ("pipeline", "🚦 Pipeline"),
        ("issue", "📕 Issue"),
        ("note", "💬 Комментарий"),
        ("build", "🔧 Job CI/CD"),
        ("wiki_page", "📖 Wiki"),
    ]
    buttons = []
    for key, label in all_events:
        check = "✅" if key in enabled else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{check} {label}",
            callback_data=f"toggle_event:{key}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Helpers ────────────────────────────────────────────────────────────────

async def get_enabled_events() -> list[str]:
    raw = await db.get_setting("enabled_events",
                               "push,tag_push,merge_request,pipeline,issue,note,build,wiki_page")
    return [e.strip() for e in raw.split(",") if e.strip()]


async def build_stats_text(date: str = None) -> str:
    stats = await db.get_daily_stats(date)
    all_users = await db.get_all_users()
    gitlab_to_tg = {u["gitlab_username"]: u for u in all_users if u.get("gitlab_username")}

    label = stats["date"]
    lines = [f"📊 <b>Статистика за {label}</b>\n"]

    # Активность разработчиков
    lines.append("👨‍💻 <b>Активность команды:</b>")
    if stats["commits_by_user"]:
        for gl_user, cnt in stats["commits_by_user"].items():
            tg = gitlab_to_tg.get(gl_user)
            mention = f"@{tg['telegram_username']}" if tg and tg.get("telegram_username") else gl_user
            lines.append(f"  • {mention} — {cnt} коммит(ов)")
    else:
        lines.append("  • Коммитов не было")

    # Пользователи без коммитов
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

    return "\n".join(lines)


# ── /tgbot command ─────────────────────────────────────────────────────────

@router.message(Command("tgbot"))
async def cmd_tgbot(message: Message, state: FSMContext):
    """Главная команда бота — регистрация + меню."""
    user = message.from_user

    # Авто-регистрация: сохраняем Telegram ID и username
    await db.upsert_user(
        telegram_id=user.id,
        telegram_username=user.username or "",
    )
    logger.info("User registered/updated: %s (id=%s)", user.username, user.id)

    # Получаем текущий gitlab_username если есть
    all_users = await db.get_all_users()
    current = next((u for u in all_users if u["telegram_id"] == user.id), None)
    gitlab_info = f"🔗 Ваш GitLab: <code>{current['gitlab_username']}</code>" \
                  if current and current.get("gitlab_username") else \
                  "⚠️ GitLab username не привязан — нажмите «Мой GitLab»"

    text = (
        f"🤖 <b>GitLab Bot — Панель управления</b>\n\n"
        f"👤 Вы: @{user.username or user.first_name} (ID: <code>{user.id}</code>)\n"
        f"{gitlab_info}\n\n"
        f"Выберите действие:"
    )
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


# ── Callbacks ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "🤖 <b>GitLab Bot — Панель управления</b>\n\nВыберите действие:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()


# ── Статистика сейчас ──────────────────────────────────────────────────────

@router.callback_query(F.data == "stats_now")
async def cb_stats_now(call: CallbackQuery):
    await call.answer("Загружаю статистику...")
    text = await build_stats_text()
    back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(text, reply_markup=back, parse_mode="HTML")


# ── Последние события ──────────────────────────────────────────────────────

@router.callback_query(F.data == "event_log")
async def cb_event_log(call: CallbackQuery):
    await call.answer("Загружаю события...")
    events = await db.get_recent_events(10)
    if not events:
        text = "📜 <b>Последние события</b>\n\nСобытий пока нет."
    else:
        lines = ["📜 <b>Последние 10 событий:</b>\n"]
        for e in events:
            ts = e["created_at"][:16] if e["created_at"] else "—"
            actor = e.get("actor_gitlab") or "—"
            lines.append(f"• <code>{ts}</code> <b>{e['event_type']}</b> · {e['project'] or '—'} · {actor}")
        text = "\n".join(lines)

    back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(text, reply_markup=back, parse_mode="HTML")


# ── Расписание отчёта ──────────────────────────────────────────────────────

@router.callback_query(F.data == "set_schedule")
async def cb_set_schedule(call: CallbackQuery, state: FSMContext):
    current_time = await db.get_setting("report_time", "09:00")
    await call.message.edit_text(
        f"📅 <b>Расписание ежедневного отчёта</b>\n\n"
        f"Текущее время: <code>{current_time}</code>\n\n"
        f"Введите новое время отправки отчёта в формате <code>ЧЧ:ММ</code>\n"
        f"Например: <code>09:00</code> или <code>18:30</code>",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_for_report_time)
    await call.answer()


@router.message(SettingsStates.waiting_for_report_time)
async def process_report_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите время в формате <code>ЧЧ:ММ</code>, например <code>09:00</code>", parse_mode="HTML")
        return

    await db.set_setting("report_time", time_str)

    # Перепланируем задачу в scheduler
    from core.scheduler import reschedule_report
    await reschedule_report(time_str)

    await state.clear()
    await message.answer(
        f"✅ Ежедневный отчёт теперь будет приходить в <b>{time_str}</b>\n\n"
        f"Возврат в меню: /tgbot",
        parse_mode="HTML"
    )


# ── Типы событий ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "set_events")
async def cb_set_events(call: CallbackQuery):
    enabled = await get_enabled_events()
    await call.message.edit_text(
        "🔔 <b>Управление типами событий</b>\n\nВключите/выключите нужные:",
        reply_markup=events_keyboard(enabled),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("toggle_event:"))
async def cb_toggle_event(call: CallbackQuery):
    event_key = call.data.split(":")[1]
    enabled = await get_enabled_events()
    if event_key in enabled:
        enabled.remove(event_key)
    else:
        enabled.append(event_key)
    await db.set_setting("enabled_events", ",".join(enabled))
    await call.message.edit_reply_markup(reply_markup=events_keyboard(enabled))
    await call.answer("✅ Обновлено")


# ── Участники команды ──────────────────────────────────────────────────────

@router.callback_query(F.data == "team_list")
async def cb_team_list(call: CallbackQuery):
    users = await db.get_all_users()
    if not users:
        text = "👥 <b>Участники команды</b>\n\nНикто ещё не зарегистрировался.\nНапишите /tgbot чтобы зарегистрироваться."
    else:
        lines = ["👥 <b>Участники команды:</b>\n"]
        for u in users:
            tg = f"@{u['telegram_username']}" if u.get("telegram_username") else f"ID:{u['telegram_id']}"
            gl = f"<code>{u['gitlab_username']}</code>" if u.get("gitlab_username") else "⚠️ не привязан"
            lines.append(f"• {tg} → GitLab: {gl}")
        text = "\n".join(lines)

    back = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(text, reply_markup=back, parse_mode="HTML")
    await call.answer()


# ── Привязка GitLab username ───────────────────────────────────────────────

@router.callback_query(F.data == "my_gitlab")
async def cb_my_gitlab(call: CallbackQuery, state: FSMContext):
    users = await db.get_all_users()
    current = next((u for u in users if u["telegram_id"] == call.from_user.id), None)
    current_gl = current.get("gitlab_username") if current else None
    hint = f"Текущий: <code>{current_gl}</code>\n\n" if current_gl else ""
    await call.message.edit_text(
        f"🔗 <b>Привязка GitLab username</b>\n\n"
        f"{hint}"
        f"Введите ваш GitLab username (тот, что указан в профиле GitLab):",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_for_map_username)
    await call.answer()


@router.message(SettingsStates.waiting_for_map_username)
async def process_gitlab_username(message: Message, state: FSMContext):
    gitlab_username = message.text.strip().lstrip("@")
    if not gitlab_username:
        await message.answer("❌ Введите корректный username")
        return

    await db.set_user_gitlab(message.from_user.id, gitlab_username)
    await state.clear()
    await message.answer(
        f"✅ GitLab username <code>{gitlab_username}</code> привязан к @{message.from_user.username}!\n\n"
        f"Теперь бот будет упоминать вас при событиях GitLab.\n"
        f"Возврат в меню: /tgbot",
        parse_mode="HTML"
    )
