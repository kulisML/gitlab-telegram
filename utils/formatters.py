from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def get_mention(gitlab_username: str) -> str:
    """Возвращает @упоминание Telegram по GitLab username, или сам gitlab_username."""
    if not gitlab_username:
        return "неизвестно"
    try:
        from core.database import get_user_by_gitlab
        user = await get_user_by_gitlab(gitlab_username)
        if user and user.get("telegram_username"):
            return f"@{user['telegram_username']}"
    except Exception:
        pass
    return gitlab_username


async def format_push_message(data: dict) -> str:
    """Push event — кто, что, в какую ветку."""
    project_name = data.get("project", {}).get("name")
    branch = data.get("ref", "").replace("refs/heads/", "")
    user_name = data.get("user_name", "")
    commits = data.get("commits", [])
    project_url = data.get("project", {}).get("web_url")
    mention = await get_mention(user_name)

    msg = f"<b>🚀 Пуш в репозиторий:</b> <a href=\"{project_url}\">{project_name}</a>\n"
    msg += f"👤 <b>Автор:</b> {mention}\n"
    msg += f"🌿 <b>Ветка:</b> <code>{branch}</code>\n"
    msg += f"📦 <b>Коммитов:</b> {len(commits)}\n"

    if commits:
        msg += "\n<b>Коммиты:</b>\n"
        for commit in commits[:5]:
            short_id = commit.get("id", "")[:8]
            title = commit.get("message", "").split("\n")[0]
            url = commit.get("url")
            # Показываем изменённые файлы
            added = len(commit.get("added", []))
            modified = len(commit.get("modified", []))
            removed = len(commit.get("removed", []))
            file_info = ""
            parts = []
            if added: parts.append(f"+{added}")
            if modified: parts.append(f"~{modified}")
            if removed: parts.append(f"-{removed}")
            if parts:
                file_info = f" <i>({', '.join(parts)} файл(ов))</i>"
            msg += f"- <a href=\"{url}\">[{short_id}]</a> {title}{file_info}\n"
        if len(commits) > 5:
            msg += f"<i>...и ещё {len(commits) - 5} коммитов</i>\n"

    return msg


async def format_tag_push_message(data: dict) -> str:
    """Tag Push event."""
    project_name = data.get("project", {}).get("name")
    tag = data.get("ref", "").replace("refs/tags/", "")
    user_name = data.get("user_name", "")
    project_web_url = data.get("project", {}).get("web_url")
    tag_url = f"{project_web_url}/-/tags/{tag}"
    message = data.get("message", "")
    mention = await get_mention(user_name)

    msg = f"<b>🏷️ Новый тег:</b> <a href=\"{tag_url}\">{tag}</a>\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Автор:</b> {mention}\n"
    if message:
        msg += f"📝 <b>Заметка:</b> {message}\n"

    return msg


async def format_mr_message(data: dict) -> str:
    """Merge Request event."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    source = attr.get("source_branch", "")
    target = attr.get("target_branch", "")
    user_gl = data.get("user", {}).get("username") or data.get("user", {}).get("name", "")
    project_name = data.get("project", {}).get("name")
    mention = await get_mention(user_gl)

    status_emoji = {"open": "🆕", "merge": "✅", "close": "❌", "reopen": "🔄"}.get(action, "🛠️")
    action_text = {"open": "открыт", "merge": "смёрджен", "close": "закрыт", "reopen": "переоткрыт"}.get(action, action)

    msg = f"{status_emoji} <b>Merge Request {action_text}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Инициатор:</b> {mention}\n"
    if source and target:
        msg += f"🌿 <b>Ветки:</b> <code>{source}</code> → <code>{target}</code>\n"

    return msg


async def format_pipeline_message(data: dict) -> str:
    """Pipeline event — только success и failed."""
    attr = data.get("object_attributes", {})
    status = attr.get("status")
    ref = attr.get("ref")
    pipeline_id = attr.get("id")
    duration = attr.get("duration")
    project = data.get("project", {}).get("name")
    project_url = data.get("project", {}).get("web_url")
    pipeline_url = f"{project_url}/-/pipelines/{pipeline_id}"
    commit = data.get("commit", {})
    user_gl = commit.get("author", {}).get("name", "") if commit else ""
    mention = await get_mention(user_gl) if user_gl else ""

    emoji = {"success": "🏁", "failed": "🚫", "canceled": "🛑"}.get(status, "🔄")

    if status not in ["success", "failed"]:
        return ""

    msg = f"{emoji} <b>Pipeline {status.upper()}:</b> ID <a href=\"{pipeline_url}\">#{pipeline_id}</a>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"🌿 <b>Ветка:</b> <code>{ref}</code>\n"
    if duration:
        msg += f"⏱ <b>Время:</b> {duration} сек\n"
    if mention:
        msg += f"👤 <b>Автор:</b> {mention}\n"

    return msg


async def format_issue_message(data: dict) -> str:
    """Issue event."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    description = (attr.get("description") or "")[:150]
    user_gl = data.get("user", {}).get("username") or data.get("user", {}).get("name", "")
    project = data.get("project", {}).get("name")
    mention = await get_mention(user_gl)
    action_text = {"open": "открыта", "close": "закрыта", "reopen": "переоткрыта"}.get(action, action)

    msg = f"<b>📕 Issue {action_text}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {mention}\n"
    if description:
        msg += f"📝 <i>{description}{'...' if len(attr.get('description','')) > 150 else ''}</i>\n"

    return msg


async def format_comment_message(data: dict) -> str:
    """Comment/Note event."""
    note = data.get("object_attributes", {})
    user_gl = data.get("user", {}).get("username") or data.get("user", {}).get("name", "")
    url = note.get("url")
    text = note.get("note", "")
    project = data.get("project", {}).get("name")
    mention = await get_mention(user_gl)

    # Определяем к чему относится комментарий
    notable_type = note.get("noteable_type", "")
    context = {"MergeRequest": "Merge Request", "Issue": "Issue", "Commit": "коммиту"}.get(notable_type, "")
    context_str = f" к {context}" if context else ""

    msg = f"<b>💬 Новый комментарий{context_str}:</b>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {mention}\n"
    msg += f"📝 <i>{text[:200]}{'...' if len(text) > 200 else ''}</i>\n"
    msg += f"🔗 <a href=\"{url}\">Перейти к обсуждению</a>"

    return msg


async def format_job_message(data: dict) -> str:
    """Job/Build event — только success и failed."""
    status = data.get("build_status")
    name = data.get("build_name")
    user_gl = data.get("user", {}).get("name", "")
    project_name = data.get("project_name")
    project_url = data.get("project", {}).get("web_url", "")
    build_id = data.get("build_id")
    build_url = f"{project_url}/-/jobs/{build_id}" if project_url else "#"
    duration = data.get("build_duration")
    mention = await get_mention(user_gl)

    if status not in ["failed", "success"]:
        return ""

    emoji = "✅" if status == "success" else "❌"
    msg = f"{emoji} <b>Job {status.upper()}:</b> <code>{name}</code>\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Исполнитель:</b> {mention}\n"
    if duration:
        msg += f"⏱ <b>Время:</b> {int(duration)} сек\n"
    msg += f"🔗 <a href=\"{build_url}\">Детали задачи</a>"

    return msg


async def format_wiki_message(data: dict) -> str:
    """Wiki Page event."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    user_gl = data.get("user", {}).get("username") or data.get("user", {}).get("name", "")
    project = data.get("project", {}).get("name")
    mention = await get_mention(user_gl)
    action_text = {"create": "создана", "update": "обновлена", "delete": "удалена"}.get(action, action)

    msg = f"<b>📖 Wiki {action_text}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {mention}"

    return msg


FORMATTERS = {
    "push": format_push_message,
    "tag_push": format_tag_push_message,
    "merge_request": format_mr_message,
    "pipeline": format_pipeline_message,
    "issue": format_issue_message,
    "note": format_comment_message,
    "build": format_job_message,
    "wiki_page": format_wiki_message,
}
