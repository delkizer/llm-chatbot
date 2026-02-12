"""
Data Layer API Client

btn Open API를 통해 스포츠 데이터를 수집하는 비동기 클라이언트.
- BWF 배드민턴 데이터 수집
- Redis 캐시 지원
- 재시도 및 Graceful Degradation
"""

import json
import asyncio
from typing import Optional, Any

import httpx

from class_config.class_env import Config
from class_lib.data_layer.errors import DataLayerError, APIConnectionError, APIResponseError


class DataLayerClient:
    """btn Open API 클라이언트"""

    CACHE_PREFIX = "data:"

    def __init__(self, logger):
        self.logger = logger
        self.config = Config()

        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """httpx AsyncClient lazy 초기화"""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            api_key = self.config.btn_api_key
            if api_key:
                headers["X-API-Key"] = api_key

            self._client = httpx.AsyncClient(
                base_url=self.config.btn_api_base_url,
                headers=headers,
                timeout=httpx.Timeout(self.config.api_timeout)
            )
        return self._client

    async def close(self):
        """클라이언트 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self.logger.info("[DataLayer] Client closed")

    # ─────────────────────────────────────────────
    # BWF API Methods
    # ─────────────────────────────────────────────

    async def get_match_summary(self, match_id: str) -> Optional[dict]:
        """경기 요약 조회"""
        return await self._fetch(
            f"/api/bwf/matches/{match_id}",
            cache_key=f"match_summary:{match_id}"
        )

    async def get_player_stats(self, match_id: str, player_id: str) -> Optional[dict]:
        """선수 통계 조회"""
        return await self._fetch(
            f"/api/bwf/players/{player_id}/stats",
            params={"match_id": match_id},
            cache_key=f"player_stats:{match_id}:{player_id}"
        )

    async def get_shot_distribution(self, match_id: str, player_id: str) -> Optional[dict]:
        """샷 분포 조회"""
        return await self._fetch(
            "/api/bwf/rallies/shots",
            params={"match_id": match_id, "player_id": player_id},
            cache_key=f"shot_distribution:{match_id}:{player_id}"
        )

    async def get_rally_analysis(self, match_id: str) -> Optional[dict]:
        """랠리 분석 조회"""
        return await self._fetch(
            "/api/bwf/rallies/analysis",
            params={"match_id": match_id},
            cache_key=f"rally_analysis:{match_id}"
        )

    async def get_head_to_head(self, player1_id: str, player2_id: str) -> Optional[dict]:
        """상대 전적 조회"""
        # 캐시 키 정규화 (순서 무관)
        ids = sorted([player1_id, player2_id])
        return await self._fetch(
            "/api/bwf/players/head-to-head",
            params={"player1_id": player1_id, "player2_id": player2_id},
            cache_key=f"h2h:{ids[0]}:{ids[1]}",
            cache_ttl=3600  # H2H는 1시간 캐시
        )

    async def fetch_all_context(
        self,
        match_id: str,
        player_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        BWF 컨텍스트 데이터 일괄 수집 (병렬)

        Returns:
            dict: {match_summary, player_stats, shot_distribution, rally_analysis}
                  각 값은 API 응답 dict 또는 None
        """
        self.logger.info(f"[DataLayer] Fetching all context: match={match_id}, player={player_id}")

        tasks = {
            "match_summary": self.get_match_summary(match_id),
            "rally_analysis": self.get_rally_analysis(match_id),
        }

        if player_id:
            tasks["player_stats"] = self.get_player_stats(match_id, player_id)
            tasks["shot_distribution"] = self.get_shot_distribution(match_id, player_id)

        keys = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        context = {}
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                self.logger.warning(f"[DataLayer] {key} failed: {result}")
                context[key] = None
            else:
                context[key] = result

        fetched = [k for k, v in context.items() if v is not None]
        self.logger.info(f"[DataLayer] Fetched: {fetched}")

        return context

    # ─────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────

    async def _fetch(
        self,
        path: str,
        params: Optional[dict] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None
    ) -> Optional[dict]:
        """
        API 호출 (캐시 → API → fallback)

        1. Redis 캐시 확인
        2. 캐시 miss → API 호출 (재시도 포함)
        3. API 실패 → stale 캐시 반환
        4. 모두 실패 → None
        """
        ttl = cache_ttl or self.config.data_cache_ttl
        full_cache_key = f"{self.CACHE_PREFIX}{cache_key}" if cache_key else None

        # 1. 캐시 확인
        if full_cache_key:
            cached = self._get_cache(full_cache_key)
            if cached is not None:
                self.logger.debug(f"[DataLayer] Cache hit: {cache_key}")
                return cached

        # 2. API 호출
        try:
            data = await self._fetch_with_retry(path, params)

            # 캐시 저장
            if full_cache_key and data is not None:
                self._set_cache(full_cache_key, data, ttl)

            return data

        except (APIConnectionError, APIResponseError) as e:
            self.logger.warning(f"[DataLayer] API failed: {e}")

            # 3. stale 캐시 fallback
            if full_cache_key:
                stale = self._get_stale_cache(full_cache_key)
                if stale is not None:
                    self.logger.info(f"[DataLayer] Using stale cache: {cache_key}")
                    return stale

            # 4. 모두 실패
            return None

    async def _fetch_with_retry(
        self,
        path: str,
        params: Optional[dict] = None
    ) -> Optional[dict]:
        """API 호출 + 재시도 (지수 백오프)"""
        max_retries = self.config.api_max_retries
        client = self._get_client()

        for attempt in range(max_retries):
            try:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()

            except httpx.ConnectError as e:
                self.logger.warning(f"[DataLayer] Connection error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise APIConnectionError(str(e))
                await asyncio.sleep(2 ** attempt)  # 1, 2, 4초

            except httpx.HTTPStatusError as e:
                self.logger.warning(f"[DataLayer] HTTP {e.response.status_code} (attempt {attempt + 1})")
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise APIResponseError(e.response.status_code, str(e))

            except httpx.TimeoutException as e:
                self.logger.warning(f"[DataLayer] Timeout (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"Timeout: {e}")
                await asyncio.sleep(2 ** attempt)

        return None

    # ─────────────────────────────────────────────
    # Cache (Redis)
    # ─────────────────────────────────────────────

    def _get_redis(self):
        """Redis master 연결 (SessionClient와 동일 Sentinel 사용)"""
        from redis.sentinel import Sentinel
        sentinel = Sentinel(
            self.config.redis_sentinel_nodes,
            socket_timeout=3.0
        )
        return sentinel.master_for(
            self.config.redis_sentinel_master,
            password=self.config.redis_password,
            db=self.config.redis_db
        )

    def _get_cache(self, key: str) -> Optional[dict]:
        """캐시 조회"""
        try:
            redis = self._get_redis()
            data = redis.get(key)
            if data:
                return json.loads(data.decode() if isinstance(data, bytes) else data)
        except Exception as e:
            self.logger.debug(f"[DataLayer] Cache read error: {e}")
        return None

    def _set_cache(self, key: str, data: dict, ttl: int):
        """캐시 저장 (primary + stale)"""
        try:
            redis = self._get_redis()
            serialized = json.dumps(data, ensure_ascii=False)

            # primary 캐시
            redis.setex(key, ttl, serialized)

            # stale 캐시 (primary의 3배 TTL)
            stale_key = f"{key}:stale"
            stale_ttl = ttl * 3
            redis.setex(stale_key, stale_ttl, serialized)
        except Exception as e:
            self.logger.debug(f"[DataLayer] Cache write error: {e}")

    def _get_stale_cache(self, key: str) -> Optional[dict]:
        """만료된 캐시 조회 (stale 키)"""
        stale_key = f"{key}:stale"
        try:
            redis = self._get_redis()
            data = redis.get(stale_key)
            if data:
                return json.loads(data.decode() if isinstance(data, bytes) else data)
        except Exception as e:
            self.logger.debug(f"[DataLayer] Stale cache read error: {e}")
        return None
