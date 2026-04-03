from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_push_message(data: dict) -> str:
    """Formatter for Push events."""
    project_name = data.get("project", {}).get("name")
    branch = data.get("ref", "").replace("refs/heads/", "")
    user_name = data.get("user_name")
    commits = data.get("commits", [])
    project_url = data.get("project", {}).get("web_url")
    
    msg = f"<b>🚀 Пуш в репозиторий:</b> <a href=\"{project_url}\">{project_name}</a>\n"
    msg += f"👤 <b>Автор:</b> {user_name}\n"
    msg += f"🌿 <b>Ветка:</b> <code>{branch}</code>\n\n"
    
    if commits:
        msg += "<b>Коммиты:</b>\n"
        for commit in commits[:5]:
            short_id = commit.get("id", "")[:8]
            title = commit.get("message", "").split("\n")[0]
            url = commit.get("url")
            msg += f"- <a href=\"{url}\">[{short_id}]</a> {title}\n"
        
        if len(commits) > 5:
            msg += f"<i>...и еще {len(commits) - 5} коммитов</i>\n"
    
    return msg

def format_tag_push_message(data: dict) -> str:
    """Formatter for Tag Push events."""
    project_name = data.get("project", {}).get("name")
    tag = data.get("ref", "").replace("refs/tags/", "")
    user_name = data.get("user_name")
    project_web_url = data.get("project", {}).get("web_url")
    tag_url = f"{project_web_url}/-/tags/{tag}"
    message = data.get("message", "")

    msg = f"<b>🏷️ Новый тег:</b> <a href=\"{tag_url}\">{tag}</a>\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Автор:</b> {user_name}\n"
    if message:
        msg += f"📝 <b>Сообщение:</b> {message}\n"
    
    return msg

def format_mr_message(data: dict) -> str:
    """Formatter for Merge Request events."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    user = data.get("user", {}).get("name")
    project_name = data.get("project", {}).get("name")
    
    status_emoji = "🛠️"
    if action == "open": status_emoji = "🆕"
    elif action == "merge": status_emoji = "✅"
    elif action == "close": status_emoji = "❌"
    
    msg = f"{status_emoji} <b>Merge Request {action}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Инициатор:</b> {user}\n"
    
    return msg

def format_pipeline_message(data: dict) -> str:
    """Formatter for Pipeline events."""
    attr = data.get("object_attributes", {})
    status = attr.get("status")
    ref = attr.get("ref")
    pipeline_id = attr.get("id")
    project = data.get("project", {}).get("name")
    project_url = data.get("project", {}).get("web_url")
    pipeline_url = f"{project_url}/-/pipelines/{pipeline_id}"
    
    emoji = "🔄"
    if status == "success": emoji = "🏁"
    elif status == "failed": emoji = "🚫"
    elif status == "canceled": emoji = "🛑"
    
    if status not in ["success", "failed"]:
        return ""
        
    msg = f"{emoji} <b>Pipeline {status.upper()}:</b> ID #{pipeline_id}\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"🌿 <b>Ветка:</b> <code>{ref}</code>\n"
    msg += f"🔗 <a href=\"{pipeline_url}\">Посмотреть в GitLab</a>"
    
    return msg

def format_issue_message(data: dict) -> str:
    """Formatter for Issue events."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    user = data.get("user", {}).get("name")
    project = data.get("project", {}).get("name")
    
    msg = f"<b>📕 Issue {action}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {user}"
    
    return msg

def format_comment_message(data: dict) -> str:
    """Formatter for Comment (note) events."""
    note = data.get("object_attributes", {})
    user = data.get("user", {}).get("name")
    url = note.get("url")
    text = note.get("note", "")
    project = data.get("project", {}).get("name")
    
    msg = f"<b>💬 Новый комментарий:</b>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {user}\n"
    msg += f"📝 <i>{text[:200]}</i>" + ("..." if len(text) > 200 else "") + "\n"
    msg += f"🔗 <a href=\"{url}\">Перейти к обсуждению</a>"
    
    return msg

def format_job_message(data: dict) -> str:
    """Formatter for Job events (CI/CD)."""
    status = data.get("build_status")
    name = data.get("build_name")
    user = data.get("user", {}).get("name")
    project_name = data.get("project_name")
    project_url = data.get("project", {}).get("web_url")
    build_id = data.get("build_id")
    build_url = f"{project_url}/-/jobs/{build_id}"

    if status not in ["failed", "success"]:
        return ""

    emoji = "✅" if status == "success" else "❌"
    msg = f"{emoji} <b>Job {status.upper()}:</b> {name}\n"
    msg += f"📁 <b>Проект:</b> {project_name}\n"
    msg += f"👤 <b>Исполнитель:</b> {user}\n"
    msg += f"🔗 <a href=\"{build_url}\">Детали работы</a>"
    
    return msg

def format_wiki_message(data: dict) -> str:
    """Formatter for Wiki Page events."""
    attr = data.get("object_attributes", {})
    action = attr.get("action")
    title = attr.get("title")
    url = attr.get("url")
    user = data.get("user", {}).get("name")
    project = data.get("project", {}).get("name")

    msg = f"<b>📖 Wiki {action}:</b> <a href=\"{url}\">{title}</a>\n"
    msg += f"📁 <b>Проект:</b> {project}\n"
    msg += f"👤 <b>Автор:</b> {user}"
    
    return msg

FORMATTERS = {
    "push": format_push_message,
    "tag_push": format_tag_push_message,
    "merge_request": format_mr_message,
    "pipeline": format_pipeline_message,
    "issue": format_issue_message,
    "note": format_comment_message,
    "build": format_job_message, # GitLab calls jobs "build" in webhooks
    "wiki_page": format_wiki_message
}
