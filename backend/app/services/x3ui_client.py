"""GUSTO 3x-ui Client — интеграция с панелями"""
import httpx
import uuid
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("gusto.x3ui")


@dataclass
class X3UIPanel:
    host: str
    port: int
    username: str
    password: str
    name: str
    use_ssl: bool = True

    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"


class GustoX3UIClient:
    """Клиент для 3x-ui панели с cookie-based авторизацией"""

    def __init__(self, panel: X3UIPanel):
        self.panel = panel
        self.session = httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10)
        )
        self._cookies = {}
        self._logged_in = False
        self._last_login = None

    async def _login(self) -> bool:
        if self._logged_in and self._last_login:
            if datetime.utcnow() - self._last_login < timedelta(minutes=10):
                return True

        try:
            resp = await self.session.post(
                f"{self.panel.base_url}/login",
                data={"username": self.panel.username, "password": self.panel.password}
            )
            if resp.status_code == 200 and "session" in resp.cookies:
                self._cookies = dict(resp.cookies)
                self._logged_in = True
                self._last_login = datetime.utcnow()
                logger.info(f"✅ Logged into {self.panel.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Login failed {self.panel.name}: {e}")
            return False

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        if not self._logged_in:
            await self._login()

        url = f"{self.panel.base_url}/xui/API/inbounds{endpoint}"
        resp = await self.session.request(method, url, cookies=self._cookies, **kwargs)

        if resp.status_code in (401, 403) or "login" in resp.text.lower():
            await self._login()
            resp = await self.session.request(method, url, cookies=self._cookies, **kwargs)

        return resp

    async def get_inbounds(self) -> List[Dict]:
        resp = await self._request("GET", "/list")
        if resp.status_code == 200:
            return resp.json().get("obj", [])
        return []

    async def get_inbound(self, inbound_id: int) -> Optional[Dict]:
        resp = await self._request("GET", f"/get/{inbound_id}")
        if resp.status_code == 200:
            return resp.json().get("obj")
        return None

    async def add_client(
        self, inbound_id: int, email: str, total_gb: float,
        expiry_days: int, uuid_str: Optional[str] = None,
        enable: bool = True, tg_id: int = 0, ip_limit: int = 0
    ) -> Optional[Dict]:
        client_uuid = uuid_str or str(uuid.uuid4())
        expiry_time = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)

        client = {
            "id": client_uuid,
            "email": email,
            "limitIp": ip_limit,
            "totalGB": int(total_gb * 1073741824),
            "expiryTime": expiry_time,
            "enable": enable,
            "tgId": tg_id,
            "subId": str(uuid.uuid4())[:8],
            "reset": 0
        }

        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return None

        settings = json.loads(inbound.get("settings", "{}"))
        clients = settings.get("clients", [])

        if any(c.get("email") == email for c in clients):
            logger.error(f"❌ Email {email} already exists!")
            return None

        clients.append(client)
        settings["clients"] = clients

        resp = await self._request(
            "POST", f"/updateClient/{client_uuid}",
            json={"id": inbound_id, "settings": json.dumps(settings)}
        )

        if resp.status_code == 200 and resp.json().get("success"):
            return {
                "uuid": client_uuid,
                "email": email,
                "expiry_time": expiry_time,
                "config": self._generate_config(inbound, client_uuid)
            }
        return None

    def _generate_config(self, inbound: Dict, client_uuid: str) -> Dict:
        stream = json.loads(inbound.get("streamSettings", "{}"))
        protocol = inbound.get("protocol", "vless")
        port = inbound.get("port", 443)
        remark = inbound.get("remark", "GUSTO")

        config = {"protocol": protocol, "port": port, "remark": remark}

        if protocol == "vless" and stream.get("security") == "reality":
            reality = stream.get("realitySettings", {})
            server_names = reality.get("serverNames", [self.panel.host])

            config["link"] = (
                f"vless://{client_uuid}@{self.panel.host}:{port}?"
                f"security=reality&"
                f"flow={stream.get('settings', {}).get('flow', 'xtls-rprx-vision')}&"
                f"sni={server_names[0]}&fp=chrome&"
                f"pbk={reality.get('publicKey', '')}&"
                f"sid={reality.get('shortIds', [''])[0]}&"
                f"spx=%2F#{remark}"
            )
        elif protocol == "trojan":
            ws = stream.get("wsSettings", {})
            config["link"] = (
                f"trojan://{client_uuid}@{self.panel.host}:{port}?"
                f"security=tls&type=ws&"
                f"path={ws.get('path', '/ws')}&"
                f"host={ws.get('headers', {}).get('Host', 'cdn.cloudflare.com')}#{remark}"
            )

        return config

    async def get_client_stats(self, email: str) -> Optional[Dict]:
        resp = await self._request("GET", f"/getClientTraffics/{email}")
        if resp.status_code == 200:
            return resp.json().get("obj")
        return None

    async def get_client_ips(self, email: str) -> List[str]:
        resp = await self._request("GET", f"/clientIps/{email}")
        if resp.status_code == 200:
            return resp.json().get("obj", [])
        return []

    async def reset_client_traffic(self, email: str) -> bool:
        resp = await self._request("POST", f"/{email}/resetTraffic")
        return resp.status_code == 200

    async def clear_client_ips(self, email: str) -> bool:
        resp = await self._request("POST", f"/clearClientIps/{email}")
        return resp.status_code == 200

    async def delete_client(self, inbound_id: int, email: str) -> bool:
        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return False

        settings = json.loads(inbound.get("settings", "{}"))
        clients = [c for c in settings.get("clients", []) if c.get("email") != email]
        settings["clients"] = clients

        resp = await self._request(
            "POST", f"/updateClients/{inbound_id}",
            json={"clients": clients}
        )
        return resp.status_code == 200

    async def get_server_status(self) -> Optional[Dict]:
        resp = await self._request("POST", "/xrayStatus")
        if resp.status_code == 200:
            return resp.json()
        return None

    async def close(self):
        await self.session.aclose()
        self._logged_in = False
