"""GUSTO 3x-ui Client — интеграция с актуальной панелью MHSanaei/3x-ui v3.x"""
import httpx
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger("gusto.x3ui")

@dataclass
class X3UIPanel:
    host: str
    port: int
    api_token: str  # API Token из Settings -> API Token
    name: str
    use_ssl: bool = True

    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"

class GustoX3UIClient:
    """Клиент для 3x-ui панели MHSanaei/3x-ui v3.x с Bearer Token авторизацией"""

    def __init__(self, panel: X3UIPanel):
        self.panel = panel
        self.headers = {
            "Authorization": f"Bearer {panel.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.session = httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10),
            headers=self.headers
        )

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Выполнить запрос к API с обработкой ошибок"""
        url = f"{self.panel.base_url}/panel/api{endpoint}"
        try:
            resp = await self.session.request(method, url, **kwargs)
            if resp.status_code in (401, 403):
                logger.error(f"❌ Auth failed for {self.panel.name}: {resp.status_code}")
            return resp
        except Exception as e:
            logger.error(f"❌ Request failed {self.panel.name}: {e}")
            raise

    # ==================== INBOUNDS ====================

    async def get_inbounds(self) -> List[Dict]:
        """Получить список всех inbound"""
        resp = await self._request("GET", "/inbounds/list")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_inbounds_slim(self) -> List[Dict]:
        """Получить краткий список inbound (для dropdown)"""
        resp = await self._request("GET", "/inbounds/list/slim")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_inbound(self, inbound_id: int) -> Optional[Dict]:
        """Получить inbound по ID"""
        resp = await self._request("GET", f"/inbounds/get/{inbound_id}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_inbound_options(self) -> List[Dict]:
        """Получить опции inbound для выбора"""
        resp = await self._request("GET", "/inbounds/options")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def add_inbound(self, inbound_data: Dict) -> Optional[Dict]:
        """Создать новый inbound"""
        resp = await self._request("POST", "/inbounds/add", json=inbound_data)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def delete_inbound(self, inbound_id: int) -> bool:
        """Удалить inbound"""
        resp = await self._request("POST", f"/inbounds/del/{inbound_id}")
        return resp.status_code == 200 and resp.json().get("success")

    async def set_inbound_enable(self, inbound_id: int, enable: bool) -> bool:
        """Включить/выключить inbound"""
        resp = await self._request("POST", f"/inbounds/setEnable/{inbound_id}", json={"enable": enable})
        return resp.status_code == 200 and resp.json().get("success")

    async def reset_inbound_traffic(self, inbound_id: int) -> bool:
        """Сбросить трафик inbound"""
        resp = await self._request("POST", f"/inbounds/{inbound_id}/resetTraffic")
        return resp.status_code == 200 and resp.json().get("success")

    # ==================== CLIENTS ====================

    async def get_clients(self) -> List[Dict]:
        """Получить список всех клиентов"""
        resp = await self._request("GET", "/clients/list")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_clients_paged(self, page: int = 1, size: int = 50, **filters) -> Dict:
        """Получить клиентов с пагинацией"""
        params = {"page": page, "size": size, **filters}
        resp = await self._request("GET", "/clients/list/paged", params=params)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", {}) if data.get("success") else {}
        return {}

    async def get_client(self, email: str) -> Optional[Dict]:
        """Получить клиента по email"""
        resp = await self._request("GET", f"/clients/get/{email}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_client_traffic(self, email: str) -> Optional[Dict]:
        """Получить статистику трафика клиента"""
        resp = await self._request("GET", f"/clients/traffic/{email}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_client_links(self, email: str) -> Optional[Dict]:
        """Получить ссылки подключения клиента"""
        resp = await self._request("GET", f"/clients/links/{email}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_client_sub_links(self, sub_id: str) -> Optional[Dict]:
        """Получить subscription links по subId"""
        resp = await self._request("GET", f"/clients/subLinks/{sub_id}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def create_client(
        self,
        inbound_ids: List[int],
        email: str,
        total_gb: float = 0,
        expiry_days: int = 30,
        uuid_str: Optional[str] = None,
        enable: bool = True,
        tg_id: int = 0,
        ip_limit: int = 0,
        flow: str = "xtls-rprx-vision"
    ) -> Optional[Dict]:
        """Создать нового клиента (актуальный API v3.x)"""
        client_uuid = uuid_str or str(uuid.uuid4())
        expiry_time = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)

        payload = {
            "inboundIds": inbound_ids,
            "clients": [{
                "id": client_uuid,
                "flow": flow,
                "email": email,
                "limitIp": ip_limit,
                "totalGB": int(total_gb * 1073741824) if total_gb > 0 else 0,
                "expiryTime": expiry_time,
                "enable": enable,
                "tgId": str(tg_id) if tg_id else "",
                "subId": str(uuid.uuid4())[:8],
                "reset": 0
            }]
        }

        resp = await self._request("POST", "/clients/add", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                logger.info(f"✅ Client created: {email}")
                return {
                    "uuid": client_uuid,
                    "email": email,
                    "expiry_time": expiry_time,
                    "sub_id": payload["clients"][0]["subId"]
                }
        logger.error(f"❌ Failed to create client {email}: {resp.text}")
        return None

    async def update_client(self, email: str, client_data: Dict) -> bool:
        """Обновить клиента по email"""
        resp = await self._request("POST", f"/clients/update/{email}", json=client_data)
        return resp.status_code == 200 and resp.json().get("success")

    async def delete_client(self, email: str) -> bool:
        """Удалить клиента по email"""
        resp = await self._request("POST", f"/clients/del/{email}")
        return resp.status_code == 200 and resp.json().get("success")

    async def attach_client(self, email: str, inbound_ids: List[int]) -> bool:
        """Привязать клиента к inbound"""
        resp = await self._request("POST", f"/clients/{email}/attach", json={"inboundIds": inbound_ids})
        return resp.status_code == 200 and resp.json().get("success")

    async def detach_client(self, email: str, inbound_ids: List[int]) -> bool:
        """Отвязать клиента от inbound"""
        resp = await self._request("POST", f"/clients/{email}/detach", json={"inboundIds": inbound_ids})
        return resp.status_code == 200 and resp.json().get("success")

    async def reset_client_traffic(self, email: str) -> bool:
        """Сбросить трафик клиента"""
        resp = await self._request("POST", f"/clients/resetTraffic/{email}")
        return resp.status_code == 200 and resp.json().get("success")

    async def update_client_traffic(self, email: str, upload: int, download: int) -> bool:
        """Обновить трафик клиента (ручная корректировка)"""
        resp = await self._request("POST", f"/clients/updateTraffic/{email}", json={
            "upload": upload,
            "download": download
        })
        return resp.status_code == 200 and resp.json().get("success")

    async def get_client_ips(self, email: str) -> List[str]:
        """Получить IP адреса клиента"""
        resp = await self._request("POST", f"/clients/ips/{email}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def clear_client_ips(self, email: str) -> bool:
        """Очистить IP адреса клиента"""
        resp = await self._request("POST", f"/clients/clearIps/{email}")
        return resp.status_code == 200 and resp.json().get("success")

    # ==================== BULK OPERATIONS ====================

    async def bulk_create_clients(self, payloads: List[Dict]) -> Dict:
        """Массовое создание клиентов"""
        resp = await self._request("POST", "/clients/bulkCreate", json=payloads)
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def bulk_delete_clients(self, emails: List[str], keep_traffic: bool = False) -> Dict:
        """Массовое удаление клиентов"""
        resp = await self._request("POST", "/clients/bulkDel", json={
            "emails": emails,
            "keepTraffic": keep_traffic
        })
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def bulk_adjust_clients(self, emails: List[str], add_days: int = 0, add_bytes: int = 0) -> Dict:
        """Массовое изменение клиентов (добавить дни/трафик)"""
        resp = await self._request("POST", "/clients/bulkAdjust", json={
            "emails": emails,
            "addDays": add_days,
            "addBytes": add_bytes
        })
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def bulk_attach_clients(self, emails: List[str], inbound_ids: List[int]) -> Dict:
        """Массовая привязка клиентов"""
        resp = await self._request("POST", "/clients/bulkAttach", json={
            "emails": emails,
            "inboundIds": inbound_ids
        })
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def bulk_detach_clients(self, emails: List[str], inbound_ids: List[int]) -> Dict:
        """Массовая отвязка клиентов"""
        resp = await self._request("POST", "/clients/bulkDetach", json={
            "emails": emails,
            "inboundIds": inbound_ids
        })
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def bulk_reset_traffic(self, emails: List[str]) -> Dict:
        """Массовый сброс трафика"""
        resp = await self._request("POST", "/clients/bulkResetTraffic", json={"emails": emails})
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    async def delete_depleted_clients(self) -> Dict:
        """Удалить исчерпанных клиентов (трафик/срок)"""
        resp = await self._request("POST", "/clients/delDepleted")
        if resp.status_code == 200:
            return resp.json()
        return {"success": False}

    # ==================== MONITORING ====================

    async def get_online_clients(self) -> List[Dict]:
        """Получить список онлайн клиентов"""
        resp = await self._request("POST", "/clients/onlines")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_online_by_guid(self) -> List[Dict]:
        """Получить онлайн клиентов по GUID"""
        resp = await self._request("POST", "/clients/onlinesByGuid")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_active_inbounds(self) -> List[Dict]:
        """Получить активные inbound"""
        resp = await self._request("POST", "/clients/activeInbounds")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    async def get_last_online(self) -> List[Dict]:
        """Получить последний онлайн клиентов"""
        resp = await self._request("POST", "/clients/lastOnline")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj", []) if data.get("success") else []
        return []

    # ==================== SERVER STATUS ====================

    async def get_server_status(self) -> Optional[Dict]:
        """Получить статус сервера"""
        resp = await self._request("GET", "/server/status")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_xray_version(self) -> Optional[Dict]:
        """Получить версию Xray"""
        resp = await self._request("GET", "/server/getXrayVersion")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def get_panel_update_info(self) -> Optional[Dict]:
        """Получить информацию об обновлении панели"""
        resp = await self._request("GET", "/server/getPanelUpdateInfo")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("obj") if data.get("success") else None
        return None

    async def restart_xray(self) -> bool:
        """Перезапустить Xray"""
        resp = await self._request("POST", "/server/restartXrayService")
        return resp.status_code == 200 and resp.json().get("success")

    async def stop_xray(self) -> bool:
        """Остановить Xray"""
        resp = await self._request("POST", "/server/stopXrayService")
        return resp.status_code == 200 and resp.json().get("success")

    # ==================== CONFIG GENERATION ====================

    def generate_vless_link(
        self,
        client_uuid: str,
        host: str,
        port: int,
        remark: str,
        public_key: str,
        short_id: str,
        server_name: str,
        flow: str = "xtls-rprx-vision",
        fingerprint: str = "chrome"
    ) -> str:
        """Сгенерировать VLESS + Reality ссылку"""
        return (
            f"vless://{client_uuid}@{host}:{port}?"
            f"security=reality&"
            f"flow={flow}&"
            f"sni={server_name}&"
            f"fp={fingerprint}&"
            f"pbk={public_key}&"
            f"sid={short_id}&"
            f"spx=%2F#{remark}"
        )

    def generate_vmess_link(self, config: Dict) -> str:
        """Сгенерировать VMess ссылку (base64)"""
        import base64
        config_str = json.dumps(config, ensure_ascii=False)
        encoded = base64.b64encode(config_str.encode()).decode()
        return f"vmess://{encoded}"

    def generate_trojan_link(
        self,
        password: str,
        host: str,
        port: int,
        remark: str,
        path: str = "/ws",
        ws_host: str = "cdn.cloudflare.com"
    ) -> str:
        """Сгенерировать Trojan ссылку"""
        return (
            f"trojan://{password}@{host}:{port}?"
            f"security=tls&type=ws&"
            f"path={path}&"
            f"host={ws_host}#{remark}"
        )

    # ==================== CLEANUP ====================

    async def close(self):
        """Закрыть сессию"""
        await self.session.aclose()
        logger.info(f"🔒 Closed connection to {self.panel.name}")
