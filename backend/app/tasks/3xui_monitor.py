"""
GUSTO 3x-ui Update Monitor — отслеживание изменений репозитория MHSanaei/3x-ui
"""
import httpx
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger("gusto.monitoring")

GITHUB_API = "https://api.github.com/repos/MHSanaei/3x-ui"

class ThreeXUIMonitor:
    """Мониторинг изменений 3x-ui"""

    def __init__(self, state_file: str = "/app/data/3xui_state.json"):
        self.state_file = state_file
        self.state = self._load_state()
        self.client = httpx.AsyncClient(timeout=30.0)

    def _load_state(self) -> Dict:
        """Загрузить сохраненное состояние"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_version": None,
            "last_commit": None,
            "last_check": None,
            "notified_changes": []
        }

    def _save_state(self):
        """Сохранить состояние"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    async def check_new_release(self) -> Optional[Dict]:
        """Проверить новый релиз"""
        try:
            resp = await self.client.get(f"{GITHUB_API}/releases/latest")
            if resp.status_code != 200:
                return None

            data = resp.json()
            latest_version = data.get("tag_name")

            if latest_version != self.state.get("last_version"):
                return {
                    "type": "release",
                    "version": latest_version,
                    "published_at": data.get("published_at"),
                    "changelog": data.get("body", "")[:2000],
                    "zipball_url": data.get("zipball_url"),
                    "html_url": data.get("html_url"),
                    "is_prerelease": data.get("prerelease", False)
                }
            return None

        except Exception as e:
            logger.error(f"Release check failed: {e}")
            return None

    async def check_new_commits(self, since_hours: int = 24) -> List[Dict]:
        """Проверить новые коммиты"""
        try:
            since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
            resp = await self.client.get(
                f"{GITHUB_API}/commits",
                params={"since": since, "per_page": 10}
            )

            if resp.status_code != 200:
                return []

            commits = resp.json()
            new_commits = []

            for commit in commits:
                sha = commit.get("sha", "")[:7]
                if sha not in self.state.get("notified_changes", []):
                    new_commits.append({
                        "type": "commit",
                        "sha": sha,
                        "message": commit.get("commit", {}).get("message", "")[:200],
                        "author": commit.get("commit", {}).get("author", {}).get("name", "Unknown"),
                        "date": commit.get("commit", {}).get("author", {}).get("date"),
                        "url": commit.get("html_url")
                    })

            return new_commits

        except Exception as e:
            logger.error(f"Commit check failed: {e}")
            return []

    async def check_api_changes(self) -> Optional[Dict]:
        """Проверить изменения в API (swagger)"""
        try:
            # Получить swagger/openapi документацию
            resp = await self.client.get(
                "https://raw.githubusercontent.com/MHSanaei/3x-ui/master/web/controller/client.go"
            )

            if resp.status_code != 200:
                return None

            content = resp.text

            # Простая проверка: сравнить хеш контента
            import hashlib
            current_hash = hashlib.md5(content.encode()).hexdigest()

            if current_hash != self.state.get("api_hash"):
                return {
                    "type": "api_change",
                    "hash": current_hash,
                    "message": "Обнаружены изменения в API endpoints. Проверьте совместимость!"
                }
            return None

        except Exception as e:
            logger.error(f"API check failed: {e}")
            return None

    async def run_check(self, notifier=None) -> List[Dict]:
        """Запустить полную проверку"""
        changes = []

        # Check releases
        release = await self.check_new_release()
        if release:
            changes.append(release)
            self.state["last_version"] = release["version"]
            self.state["notified_changes"].append(release["version"])

        # Check commits
        commits = await self.check_new_commits()
        for commit in commits:
            changes.append(commit)
            self.state["notified_changes"].append(commit["sha"])

        # Check API changes
        api_change = await self.check_api_changes()
        if api_change:
            changes.append(api_change)
            self.state["api_hash"] = api_change["hash"]

        self.state["last_check"] = datetime.utcnow().isoformat()
        self._save_state()

        # Notify admins
        if changes and notifier:
            for change in changes:
                await self._notify_admins(notifier, change)

        return changes

    async def _notify_admins(self, notifier, change: Dict):
        """Уведомить админов об изменениях"""
        from app.config import settings

        if change["type"] == "release":
            text = (
                f"🚀 <b>Новый релиз 3x-ui!</b>

"
                f"Версия: <b>{change['version']}</b>
"
                f"Дата: {change['published_at'][:10]}
"
                f"Pre-release: {'Да' if change['is_prerelease'] else 'Нет'}

"
                f"<b>Changelog:</b>
"
                f"{change['changelog'][:1000]}

"
                f"<a href='{change['html_url']}'>Подробнее</a>

"
                f"⚠️ Проверьте совместимость перед обновлением!"
            )

        elif change["type"] == "commit":
            text = (
                f"🔧 <b>Новый коммит 3x-ui</b>

"
                f"SHA: <code>{change['sha']}</code>
"
                f"Автор: {change['author']}
"
                f"Сообщение: {change['message']}

"
                f"<a href='{change['url']}'>Посмотреть</a>"
            )

        elif change["type"] == "api_change":
            text = (
                f"⚠️ <b>Изменения в API 3x-ui!</b>

"
                f"{change['message']}

"
                f"Проверьте endpoints перед обновлением!"
            )

        else:
            text = f"📋 <b>Изменение 3x-ui:</b>

{json.dumps(change, indent=2, ensure_ascii=False)[:1000]}"

        for admin_id in settings.ADMIN_IDS:
            try:
                await notifier.send_notification(admin_id, text)
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

    async def close(self):
        await self.client.aclose()
