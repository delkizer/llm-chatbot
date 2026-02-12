"""ResponseFormatter 단위 테스트"""

import logging
import pytest

from class_lib.response_formatter import ResponseFormatter, ParsedResponse


@pytest.fixture
def formatter():
    logger = logging.getLogger("test")
    return ResponseFormatter(logger)


class TestParseBasic:
    """기본 파싱 테스트"""

    def test_empty_content(self, formatter):
        """빈 문자열"""
        result = formatter.parse("")
        assert result.text == ""
        assert result.charts == []
        assert result.has_charts is False

    def test_none_content(self, formatter):
        """None 입력"""
        result = formatter.parse(None)
        assert result.text == ""
        assert result.has_charts is False

    def test_plain_text(self, formatter):
        """차트 없는 일반 텍스트"""
        text = "안세영 선수는 2024년 파리 올림픽 금메달리스트입니다."
        result = formatter.parse(text)
        assert result.text == text
        assert result.charts == []
        assert result.has_charts is False
        assert result.raw_content == text


class TestParseWithChart:
    """차트 포함 응답 파싱 테스트"""

    def test_single_chart(self, formatter):
        """차트 1개 포함"""
        content = '분석 결과입니다.\n\n```json\n{\n  "charts": [\n    {\n      "type": "bar",\n      "title": "샷 유형별 득점률",\n      "data": {\n        "labels": ["스매시", "드롭"],\n        "datasets": [{"label": "득점률", "data": [78, 65]}]\n      }\n    }\n  ]\n}\n```'
        result = formatter.parse(content)
        assert result.has_charts is True
        assert len(result.charts) == 1
        assert result.charts[0]["type"] == "bar"
        assert result.charts[0]["title"] == "샷 유형별 득점률"
        assert "분석 결과입니다." in result.text
        assert "```json" not in result.text

    def test_multiple_charts(self, formatter):
        """차트 여러 개"""
        content = '결과:\n\n```json\n{\n  "charts": [\n    {\n      "type": "bar",\n      "title": "차트1",\n      "data": {"labels": ["A", "B"], "datasets": [{"label": "값", "data": [1, 2]}]}\n    },\n    {\n      "type": "pie",\n      "title": "차트2",\n      "data": {"labels": ["X", "Y"], "datasets": [{"label": "비율", "data": [60, 40]}]}\n    }\n  ]\n}\n```'
        result = formatter.parse(content)
        assert len(result.charts) == 2
        assert result.charts[0]["type"] == "bar"
        assert result.charts[1]["type"] == "pie"

    def test_chart_plus_normal_json(self, formatter):
        """차트 JSON + 일반 JSON 혼재"""
        content = 'API 예시:\n\n```json\n{"player_id": 123, "name": "test"}\n```\n\n분석 결과:\n\n```json\n{\n  "charts": [\n    {\n      "type": "line",\n      "title": "추세",\n      "data": {"labels": ["1월", "2월"], "datasets": [{"label": "값", "data": [10, 20]}]}\n    }\n  ]\n}\n```'
        result = formatter.parse(content)
        assert len(result.charts) == 1
        assert result.charts[0]["type"] == "line"
        # 일반 JSON은 텍스트에 유지
        assert "player_id" in result.text


class TestValidation:
    """차트 유효성 검증 테스트"""

    def test_invalid_chart_type(self, formatter):
        """허용되지 않는 차트 타입"""
        content = '```json\n{\n  "charts": [\n    {"type": "scatter", "title": "테스트", "data": {"labels": ["A"], "datasets": [{"label": "v", "data": [1]}]}}\n  ]\n}\n```'
        result = formatter.parse(content)
        assert result.charts == []
        assert result.has_charts is False

    def test_missing_title(self, formatter):
        """title 누락"""
        content = '```json\n{\n  "charts": [\n    {"type": "bar", "data": {"labels": ["A"], "datasets": [{"label": "v", "data": [1]}]}}\n  ]\n}\n```'
        result = formatter.parse(content)
        assert result.charts == []

    def test_labels_data_length_mismatch(self, formatter):
        """labels/data 길이 불일치"""
        content = '```json\n{\n  "charts": [\n    {"type": "bar", "title": "테스트", "data": {"labels": ["A", "B", "C"], "datasets": [{"label": "v", "data": [1, 2]}]}}\n  ]\n}\n```'
        result = formatter.parse(content)
        assert result.charts == []

    def test_invalid_json(self, formatter):
        """잘못된 JSON → Graceful Degradation"""
        content = '텍스트\n\n```json\n{invalid json here}\n```'
        result = formatter.parse(content)
        assert result.charts == []
        # 잘못된 JSON 코드블록은 텍스트에 유지
        assert "invalid json here" in result.text


class TestParsedResponse:
    """ParsedResponse to_dict 테스트"""

    def test_to_dict(self, formatter):
        result = formatter.parse("hello")
        d = result.to_dict()
        assert d["text"] == "hello"
        assert d["charts"] == []
        assert d["has_charts"] is False
        assert "raw_content" in d
