"""
Data Layer Formatter

API JSON 데이터를 LLM 컨텍스트용 텍스트로 변환합니다.
- 우선순위 기반 섹션 구성
- 토큰 예산 관리
"""

from typing import Optional, Any
from dataclasses import dataclass, field

from class_config.class_env import Config


@dataclass
class FormattedContext:
    """포맷된 컨텍스트 데이터"""
    text: str
    token_count: int
    data_sources: list[str]

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "token_count": self.token_count,
            "data_sources": self.data_sources
        }


class DataFormatter:
    """JSON → LLM 컨텍스트 텍스트 변환"""

    # 섹션 우선순위 (높은 것부터)
    SECTION_PRIORITY = [
        "match_summary",
        "player_stats",
        "shot_distribution",
        "rally_analysis",
    ]

    def __init__(self, logger):
        self.logger = logger
        self.config = Config()
        self.max_tokens = self.config.data_max_tokens

    def build_context(
        self,
        match_summary: Optional[dict] = None,
        player_stats: Optional[dict] = None,
        shot_distribution: Optional[dict] = None,
        rally_analysis: Optional[dict] = None
    ) -> FormattedContext:
        """
        수집된 데이터를 LLM 컨텍스트 텍스트로 변환

        Args:
            match_summary: 경기 요약 데이터
            player_stats: 선수 통계 데이터
            shot_distribution: 샷 분포 데이터
            rally_analysis: 랠리 분석 데이터

        Returns:
            FormattedContext: 포맷된 컨텍스트
        """
        data_map = {
            "match_summary": match_summary,
            "player_stats": player_stats,
            "shot_distribution": shot_distribution,
            "rally_analysis": rally_analysis,
        }

        sections = []
        sources = []

        for key in self.SECTION_PRIORITY:
            data = data_map.get(key)
            if data is None:
                continue

            formatter = getattr(self, f"_format_{key}", None)
            if formatter is None:
                continue

            text = formatter(data)
            if text:
                sections.append(text)
                sources.append(key)

        if not sections:
            self.logger.info("[Formatter] No data available for context")
            return FormattedContext(text="", token_count=0, data_sources=[])

        # 토큰 예산 내로 자르기
        combined = self._truncate_sections(sections)
        token_count = self._estimate_tokens(combined)

        self.logger.info(
            f"[Formatter] Context built: {len(sources)} sources, "
            f"~{token_count} tokens"
        )

        return FormattedContext(
            text=combined,
            token_count=token_count,
            data_sources=sources
        )

    # ─────────────────────────────────────────────
    # Section Formatters
    # ─────────────────────────────────────────────

    def _format_match_summary(self, data: dict) -> str:
        """경기 요약 → 텍스트"""
        try:
            tournament = data.get("tournament", "")
            round_name = data.get("round", "")
            date = data.get("date", "")
            status = data.get("status", "")

            p1 = data.get("player1", {})
            p2 = data.get("player2", {})
            p1_name = p1.get("name", "선수1")
            p1_nation = p1.get("nation", "")
            p2_name = p2.get("name", "선수2")
            p2_nation = p2.get("nation", "")

            scores = data.get("scores", [])
            score_lines = []
            for s in scores:
                game = s.get("game", "")
                s1 = s.get("p1_score", 0)
                s2 = s.get("p2_score", 0)
                score_lines.append(f"  - {game}세트: {p1_name} {s1} - {s2} {p2_name}")

            score_text = "\n".join(score_lines) if score_lines else "  - 스코어 정보 없음"

            return (
                f"# 경기 정보\n"
                f"- 대회: {tournament}\n"
                f"- 라운드: {round_name}\n"
                f"- 날짜: {date}\n"
                f"- 상태: {status}\n"
                f"- {p1_name}({p1_nation}) vs {p2_name}({p2_nation})\n"
                f"- 스코어:\n{score_text}"
            )
        except Exception as e:
            self.logger.warning(f"[Formatter] match_summary format error: {e}")
            return ""

    def _format_player_stats(self, data: dict) -> str:
        """선수 통계 → 텍스트"""
        try:
            name = data.get("player_name", "선수")
            total = data.get("total_shots", 0)
            winning = data.get("winning_shots", 0)
            errors = data.get("errors", 0)
            rally_wins = data.get("rally_wins", 0)
            rally_losses = data.get("rally_losses", 0)

            win_rate = (winning / total * 100) if total > 0 else 0
            error_rate = (errors / total * 100) if total > 0 else 0

            return (
                f"# {name} 통계\n"
                f"- 총 샷: {total}\n"
                f"- 위닝샷: {winning} ({win_rate:.1f}%)\n"
                f"- 에러: {errors} ({error_rate:.1f}%)\n"
                f"- 랠리 승: {rally_wins}, 패: {rally_losses}"
            )
        except Exception as e:
            self.logger.warning(f"[Formatter] player_stats format error: {e}")
            return ""

    def _format_shot_distribution(self, data: dict) -> str:
        """샷 분포 → 텍스트"""
        try:
            shots = data.get("shots", [])
            if not shots:
                return ""

            lines = ["# 샷 분포"]
            for shot in shots:
                shot_type = shot.get("type", "")
                count = shot.get("count", 0)
                success = shot.get("success", 0)
                rate = (success / count * 100) if count > 0 else 0
                lines.append(f"- {shot_type}: {count}회 (성공 {success}회, {rate:.1f}%)")

            return "\n".join(lines)
        except Exception as e:
            self.logger.warning(f"[Formatter] shot_distribution format error: {e}")
            return ""

    def _format_rally_analysis(self, data: dict) -> str:
        """랠리 분석 → 텍스트"""
        try:
            avg = data.get("avg_rally_length", 0)
            max_len = data.get("max_rally_length", 0)
            win_len = data.get("winning_rally_length", 0)
            lose_len = data.get("losing_rally_length", 0)

            return (
                f"# 랠리 분석\n"
                f"- 평균 랠리 길이: {avg}타\n"
                f"- 최대 랠리 길이: {max_len}타\n"
                f"- 승리 랠리 평균: {win_len}타\n"
                f"- 패배 랠리 평균: {lose_len}타"
            )
        except Exception as e:
            self.logger.warning(f"[Formatter] rally_analysis format error: {e}")
            return ""

    # ─────────────────────────────────────────────
    # Token Management
    # ─────────────────────────────────────────────

    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (한글 약 3자/토큰, 영문 약 4자/토큰)"""
        if not text:
            return 0
        return len(text) // 3

    def _truncate_sections(self, sections: list[str]) -> str:
        """토큰 예산 내로 섹션 조합"""
        result = []
        current_tokens = 0

        for section in sections:
            section_tokens = self._estimate_tokens(section)
            if current_tokens + section_tokens > self.max_tokens:
                # 남은 예산만큼만 포함
                remaining = self.max_tokens - current_tokens
                if remaining > 50:  # 최소 50토큰은 있어야 의미 있음
                    truncated = section[:remaining * 3]  # 역산
                    result.append(truncated + "\n(데이터 일부 생략)")
                break

            result.append(section)
            current_tokens += section_tokens

        return "\n\n".join(result)
