"""GUSTO Smart Router — автовыбор лучшего сервера"""
import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass
from app.models.server import GustoServer
from app.config import settings


@dataclass
class ServerMetrics:
    server: GustoServer
    latency_ms: float
    load_score: float
    user_score: float
    geo_score: float
    stability_score: float
    total_score: float


class GustoSmartRouter:
    """GUSTO Smart Router v2.0"""

    WEIGHTS = {
        'latency': settings.ROUTER_LATENCY_WEIGHT,
        'load': settings.ROUTER_LOAD_WEIGHT,
        'users': settings.ROUTER_USERS_WEIGHT,
        'geo': settings.ROUTER_GEO_WEIGHT,
        'stability': 0.1
    }

    async def tcp_ping(self, host: str, port: int = 443, timeout: float = 3.0) -> float:
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return (time.perf_counter() - start) * 1000
        except:
            return float('inf')

    def normalize_latency(self, latency: float) -> float:
        if latency == float('inf'):
            return 0.0
        return max(0.0, min(1.0, 1 - (latency / settings.MAX_LATENCY_MS)))

    def calculate_load_score(self, cpu: float, memory: float) -> float:
        combined = (cpu * 0.7 + memory * 0.3) / 100
        return max(0.0, 1.0 - combined)

    def calculate_user_score(self, current: int, maximum: int) -> float:
        if maximum <= 0:
            return 1.0
        return max(0.0, 1.0 - (current / maximum) ** 2)

    def calculate_geo_score(self, user_country: str, server: GustoServer) -> float:
        if not user_country:
            return 0.5
        if user_country in (server.target_countries or []):
            return 1.0

        regions = {
            'RU': ['BY', 'KZ', 'UA', 'AM', 'GE'],
            'KZ': ['RU', 'BY', 'UZ', 'KG'],
            'BY': ['RU', 'KZ', 'UA', 'PL'],
        }
        if server.country_code in regions.get(user_country, []):
            return 0.85

        europe = ['NL', 'DE', 'FR', 'UK', 'FI', 'SE', 'PL', 'RO']
        asia = ['SG', 'JP', 'KR', 'HK', 'TH']

        if user_country in ['RU', 'BY', 'KZ', 'UA'] and server.country_code in europe:
            return 0.7
        if user_country in ['CN', 'JP', 'KR', 'SG'] and server.country_code in asia:
            return 0.7

        return 0.3

    def calculate_stability(self, server: GustoServer) -> float:
        if not server.is_online:
            return 0.0
        if server.cpu_load > 90:
            return 0.3
        if server.cpu_load > 70:
            return 0.7
        return 1.0

    async def find_best(
        self, user_country: str, servers: List[GustoServer],
        require_online: bool = True, protocol: str = "vless"
    ) -> Optional[ServerMetrics]:
        candidates = []

        for server in servers:
            if require_online and not server.is_online:
                continue
            if not server.is_active:
                continue
            if protocol == "vless" and not server.vless_inbound_id:
                continue

            latency = await self.tcp_ping(server.host, server.api_port or 443)
            if latency == float('inf'):
                continue

            latency_score = self.normalize_latency(latency)
            load_score = self.calculate_load_score(
                server.cpu_load or 0,
                (server.memory_used / server.memory_total * 100) if server.memory_total else 0
            )
            user_score = self.calculate_user_score(
                server.total_users or 0, server.max_users or 500
            )
            geo_score = self.calculate_geo_score(user_country, server)
            stability = self.calculate_stability(server)

            total = (
                latency_score * self.WEIGHTS['latency'] +
                load_score * self.WEIGHTS['load'] +
                user_score * self.WEIGHTS['users'] +
                geo_score * self.WEIGHTS['geo'] +
                stability * self.WEIGHTS['stability']
            )

            if server.is_premium:
                total += 0.05

            candidates.append(ServerMetrics(
                server=server, latency_ms=latency, load_score=load_score,
                user_score=user_score, geo_score=geo_score,
                stability_score=stability, total_score=total
            ))

        if not candidates:
            return None
        return max(candidates, key=lambda x: x.total_score)
