"""X3UI Client v3.x — Full API with Bearer Token, bulk ops, Smart Router"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
import base64

logger = logging.getLogger("gusto.x3ui")

@dataclass
class X3UIPanel:
    """3x-ui panel configuration"""
    host: str
    port: int
    api_token: str
    name: str

class GustoX3UIClient:
    """Async X3UI API Client"""

    def __init__(self, panel: X3UIPanel):
        self.panel = panel
        self.base_url = f"https://{panel.host}:{panel.port}/api/v1"
        self.headers = {
            "Authorization": f"Bearer {panel.api_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(
            verify=False,  # Self-signed certs in 3x-ui
            timeout=httpx.Timeout(30.0, connect=5.0)
        )

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request"""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = await self.client.request(method, url, headers=self.headers, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"X3UI {endpoint} error: {resp.status_code} - {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"X3UI request failed: {e}")
            return None

    async def get_server_status(self) -> Optional[Dict]:
        """Get server status (CPU, memory, network)"""
        return await self._request("GET", "/server/status")

    async def get_inbounds(self) -> List[Dict]:
        """Get all inbounds"""
        result = await self._request("GET", "/inbounds/list")
        return result.get("obj", []) if result else []

    async def create_client(self, inbound_ids: List[int], email: str, total_gb: float,
                           expiry_days: int, uuid_str: str, enable: bool = True,
                           tg_id: Optional[int] = None, ip_limit: int = 3,
                           flow: str = "xtls-rprx-vision") -> Optional[Dict]:
        """Create new client in 3x-ui"""
        settings = {
            "clients": [{
                "id": uuid_str,
                "email": email,
                "enable": enable,
                "tgId": tg_id,
                "subId": "",
                "flow": flow,
                "limitIp": ip_limit,
                "totalGB": total_gb,
                "expiryTime": expiry_days * 86400000  # days to ms
            }]
        }

        for inbound_id in inbound_ids:
            result = await self._request(
                "POST", f"/inbounds/addClient/{inbound_id}",
                json=settings
            )
            if not result or not result.get("success"):
                return None

        return {"uuid": uuid_str, "email": email, "config": await self._generate_config(uuid_str)}

    async def _generate_config(self, uuid_str: str) -> Dict:
        """Generate config for client"""
        return {
            "link": f"vless://{uuid_str}@{self.panel.host}:443?security=reality&flow=xtls-rprx-vision&type=tcp&fp=chrome&pbk=&sid=&sni={self.panel.host}#GUSTO-{self.panel.name}"
        }

    async def generate_vless_link(self, client_uuid: str, host: str, port: int,
                                 remark: str, public_key: str, short_id: str,
                                 server_name: str) -> str:
        """Generate VLESS link"""
        return (
            f"vless://{client_uuid}@{host}:{port}?"
            f"security=reality&flow=xtls-rprx-vision&type=tcp&fp=chrome&"
            f"pbk={public_key}&sid={short_id}&sni={server_name}#{remark}"
        )

    async def generate_trojan_link(self, password: str, host: str, port: int, remark: str) -> str:
        """Generate Trojan link"""
        return f"trojan://{password}@{host}:{port}?security=reality&sni={host}#{remark}"

    async def generate_vmess_link(self, config: Dict) -> str:
        """Generate VMess link"""
        json_str = json.dumps(config)
        b64 = base64.b64encode(json_str.encode()).decode()
        return f"vmess://{b64}"

    async def update_client(self, email: str, updates: Dict) -> bool:
        """Update client settings"""
        result = await self._request(
            "POST", f"/inbounds/updateClient/{email}",
            json=updates
        )
        return result.get("success", False) if result else False

    async def delete_client(self, email: str) -> bool:
        """Delete client from all inbounds"""
        result = await self._request("POST", f"/inbounds/delClient/{email}")
        return result.get("success", False) if result else False

    async def get_client_traffic(self, email: str) -> Optional[Dict]:
        """Get client traffic stats"""
        result = await self._request("GET", f"/inbounds/getClientTraffics/{email}")
        return result.get("obj") if result else None

    async def get_client_ips(self, email: str) -> List[str]:
        """Get client connected IPs"""
        result = await self._request("GET", f"/inbounds/clientIps/{email}")
        return result.get("obj", []) if result else []

    async def bulk_adjust_clients(self, emails: List[str], add_days: int = 0,
                                   add_bytes: int = 0) -> bool:
        """Bulk adjust expiry and traffic for multiple clients"""
        result = await self._request(
            "POST", "/inbounds/bulkAdjust",
            json={
                "emails": emails,
                "addDays": add_days,
                "addBytes": add_bytes
            }
        )
        return result.get("success", False) if result else False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
