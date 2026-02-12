"""
Response Formatter

LLM 응답에서 텍스트와 차트 JSON을 분리하는 모듈
"""

import re
import json
from dataclasses import dataclass


CHART_BLOCK_PATTERN = re.compile(
    r'```json\s*\n(.*?)\n\s*```',
    re.DOTALL
)

ALLOWED_CHART_TYPES = {"bar", "line", "pie"}


@dataclass
class ParsedResponse:
    """파싱된 응답"""
    text: str
    charts: list[dict]
    raw_content: str
    has_charts: bool

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "charts": self.charts,
            "raw_content": self.raw_content,
            "has_charts": self.has_charts
        }


class ResponseFormatter:
    """LLM 응답 파서 - 텍스트와 차트 JSON 분리"""

    def __init__(self, logger):
        self.logger = logger

    def parse(self, content: str) -> ParsedResponse:
        """
        LLM 응답 원문을 파싱하여 텍스트와 차트를 분리한다.

        Args:
            content: LLM 응답 원문

        Returns:
            ParsedResponse: 파싱 결과 (항상 유효한 객체 반환, 예외 없음)
        """
        if not content or not content.strip():
            self.logger.debug("[Formatter] Empty content")
            return ParsedResponse(
                text="",
                charts=[],
                raw_content=content or "",
                has_charts=False
            )

        matches = list(CHART_BLOCK_PATTERN.finditer(content))

        if not matches:
            self.logger.debug("[Formatter] No JSON blocks found")
            return ParsedResponse(
                text=content.strip(),
                charts=[],
                raw_content=content,
                has_charts=False
            )

        all_charts = []
        chart_block_matches = []

        for match in matches:
            json_str = match.group(1)
            charts = self._parse_chart_json(json_str)

            if charts is not None:
                all_charts.extend(charts)
                chart_block_matches.append(match)

        text = self._remove_blocks(content, chart_block_matches)

        self.logger.info(
            f"[Formatter] Parsed: {len(all_charts)} charts, "
            f"text={len(text)} chars"
        )

        return ParsedResponse(
            text=text,
            charts=all_charts,
            raw_content=content,
            has_charts=len(all_charts) > 0
        )

    def _parse_chart_json(self, json_str: str) -> list[dict] | None:
        """
        JSON 문자열에서 차트 데이터를 추출한다.

        Returns:
            list[dict]: 유효한 차트 리스트 ("charts" 키 존재 시)
            None: 차트가 아닌 JSON (일반 JSON 코드블록)
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.warning(f"[Formatter] JSON parse error: {e}")
            return None

        if not isinstance(data, dict) or "charts" not in data:
            return None

        raw_charts = data["charts"]
        if not isinstance(raw_charts, list):
            self.logger.warning("[Formatter] 'charts' is not a list")
            return None

        valid_charts = []
        for i, chart in enumerate(raw_charts):
            if self._validate_chart(chart):
                valid_charts.append(chart)
            else:
                self.logger.warning(f"[Formatter] Invalid chart at index {i}, skipped")

        return valid_charts

    def _validate_chart(self, chart: dict) -> bool:
        """차트 객체의 유효성을 검증한다."""
        chart_type = chart.get("type")
        if chart_type not in ALLOWED_CHART_TYPES:
            self.logger.warning(
                f"[Formatter] Invalid chart type: {chart_type}, "
                f"allowed: {ALLOWED_CHART_TYPES}"
            )
            return False

        title = chart.get("title")
        if not isinstance(title, str) or not title.strip():
            self.logger.warning("[Formatter] Missing or empty chart title")
            return False

        data = chart.get("data")
        if not isinstance(data, dict):
            self.logger.warning("[Formatter] Missing chart data")
            return False

        labels = data.get("labels")
        if not isinstance(labels, list) or len(labels) == 0:
            self.logger.warning("[Formatter] Missing or empty labels")
            return False

        if not all(isinstance(l, str) for l in labels):
            self.logger.warning("[Formatter] Labels must be list[str]")
            return False

        datasets = data.get("datasets")
        if not isinstance(datasets, list) or len(datasets) == 0:
            self.logger.warning("[Formatter] Missing or empty datasets")
            return False

        for j, ds in enumerate(datasets):
            if not self._validate_dataset(ds, labels):
                self.logger.warning(f"[Formatter] Invalid dataset at index {j}")
                return False

        return True

    def _validate_dataset(self, dataset: dict, labels: list) -> bool:
        """개별 데이터셋의 유효성을 검증한다."""
        if not isinstance(dataset, dict):
            return False

        label = dataset.get("label")
        if not isinstance(label, str) or not label.strip():
            self.logger.warning("[Formatter] Dataset missing label")
            return False

        data = dataset.get("data")
        if not isinstance(data, list) or len(data) == 0:
            self.logger.warning("[Formatter] Dataset missing data")
            return False

        if not all(isinstance(v, (int, float)) for v in data):
            self.logger.warning("[Formatter] Dataset data must be list[number]")
            return False

        if len(data) != len(labels):
            self.logger.warning(
                f"[Formatter] Length mismatch: labels={len(labels)}, "
                f"data={len(data)}"
            )
            return False

        return True

    def _remove_blocks(self, content: str, matches: list) -> str:
        """원문에서 차트 코드블록을 제거하고 정리된 텍스트를 반환한다."""
        if not matches:
            return content.strip()

        result = content
        for match in reversed(matches):
            start, end = match.start(), match.end()
            result = result[:start] + result[end:]

        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()
