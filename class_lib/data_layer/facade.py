"""
Data Layer 파사드

Open API를 통한 스포츠 데이터 수집 및 LLM 컨텍스트 주입 파사드.

사용법:
    from class_lib.data_layer.facade import DataLayer
    from class_lib.data_layer.formatter import FormattedContext

    data_layer = DataLayer(logger)
    context = await data_layer.get_badminton_context(
        match_id="abc-123",
        player_id="p456"
    )
    print(context.text)  # LLM에 주입할 텍스트
"""

from typing import Optional

from class_lib.data_layer.client import DataLayerClient
from class_lib.data_layer.formatter import DataFormatter, FormattedContext
from class_lib.data_layer.errors import DataLayerError, APIConnectionError, APIResponseError, CacheError


class DataLayer:
    """Data Layer 파사드 — 데이터 수집 + 포맷을 하나로 묶는 진입점"""

    def __init__(self, logger):
        self.logger = logger
        self.client = DataLayerClient(logger)
        self.formatter = DataFormatter(logger)

        self.logger.info("[DataLayer] Initialized")

    async def get_badminton_context(
        self,
        match_id: str,
        player_id: Optional[str] = None
    ) -> FormattedContext:
        """
        BWF 배드민턴 컨텍스트 수집 + 포맷

        Args:
            match_id: 경기 ID
            player_id: 선수 ID (선택)

        Returns:
            FormattedContext: LLM에 주입할 포맷된 텍스트
        """
        self.logger.info(
            f"[DataLayer] get_badminton_context: match={match_id}, player={player_id}"
        )

        try:
            # 1. 데이터 수집 (병렬)
            raw = await self.client.fetch_all_context(
                match_id=match_id,
                player_id=player_id
            )

            # 2. 포맷
            context = self.formatter.build_context(
                match_summary=raw.get("match_summary"),
                player_stats=raw.get("player_stats"),
                shot_distribution=raw.get("shot_distribution"),
                rally_analysis=raw.get("rally_analysis"),
            )

            self.logger.info(
                f"[DataLayer] Context ready: {context.token_count} tokens, "
                f"sources={context.data_sources}"
            )
            return context

        except Exception as e:
            self.logger.error(f"[DataLayer] get_badminton_context error: {e}")
            # Graceful Degradation: 빈 컨텍스트 반환
            return FormattedContext(text="", token_count=0, data_sources=[])

    async def close(self):
        """리소스 정리"""
        await self.client.close()
        self.logger.info("[DataLayer] Closed")
