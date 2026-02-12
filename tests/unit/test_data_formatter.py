"""DataFormatter 단위 테스트"""

import logging
import pytest
from unittest.mock import patch, PropertyMock

from class_lib.data_layer.formatter import DataFormatter, FormattedContext


@pytest.fixture
def formatter():
    logger = logging.getLogger("test")
    with patch.object(DataFormatter, '__init__', lambda self, lg: None):
        f = DataFormatter.__new__(DataFormatter)
        f.logger = logger
        f.max_tokens = 2000
        return f


class TestBuildContext:
    """build_context 테스트"""

    def test_no_data(self, formatter):
        """데이터 없음"""
        result = formatter.build_context()
        assert result.text == ""
        assert result.token_count == 0
        assert result.data_sources == []

    def test_match_summary_only(self, formatter):
        """경기 요약만"""
        data = {
            "tournament": "Korea Open 2024",
            "round": "Final",
            "date": "2024-01-15",
            "status": "completed",
            "player1": {"name": "안세영", "nation": "KOR"},
            "player2": {"name": "야마구치", "nation": "JPN"},
            "scores": [
                {"game": 1, "p1_score": 21, "p2_score": 15},
                {"game": 2, "p1_score": 21, "p2_score": 18}
            ]
        }
        result = formatter.build_context(match_summary=data)
        assert "Korea Open 2024" in result.text
        assert "안세영" in result.text
        assert "야마구치" in result.text
        assert "21" in result.text
        assert "match_summary" in result.data_sources
        assert result.token_count > 0

    def test_player_stats(self, formatter):
        """선수 통계"""
        data = {
            "player_name": "안세영",
            "total_shots": 200,
            "winning_shots": 80,
            "errors": 20,
            "rally_wins": 45,
            "rally_losses": 28
        }
        result = formatter.build_context(player_stats=data)
        assert "안세영" in result.text
        assert "40.0%" in result.text  # 80/200
        assert "player_stats" in result.data_sources

    def test_shot_distribution(self, formatter):
        """샷 분포"""
        data = {
            "shots": [
                {"type": "smash", "count": 50, "success": 40},
                {"type": "drop", "count": 30, "success": 20}
            ]
        }
        result = formatter.build_context(shot_distribution=data)
        assert "smash" in result.text
        assert "80.0%" in result.text  # 40/50
        assert "shot_distribution" in result.data_sources

    def test_rally_analysis(self, formatter):
        """랠리 분석"""
        data = {
            "avg_rally_length": 8.5,
            "max_rally_length": 23,
            "winning_rally_length": 9.2,
            "losing_rally_length": 7.1
        }
        result = formatter.build_context(rally_analysis=data)
        assert "8.5" in result.text
        assert "23" in result.text
        assert "rally_analysis" in result.data_sources

    def test_multiple_sources(self, formatter):
        """복수 데이터 소스"""
        match = {"tournament": "Test", "round": "F", "date": "2024", "status": "done",
                 "player1": {"name": "A", "nation": "X"},
                 "player2": {"name": "B", "nation": "Y"}, "scores": []}
        rally = {"avg_rally_length": 5, "max_rally_length": 10,
                 "winning_rally_length": 6, "losing_rally_length": 4}

        result = formatter.build_context(match_summary=match, rally_analysis=rally)
        assert "match_summary" in result.data_sources
        assert "rally_analysis" in result.data_sources
        assert len(result.data_sources) == 2


class TestFormattedContext:
    """FormattedContext to_dict"""

    def test_to_dict(self):
        ctx = FormattedContext(text="test", token_count=10, data_sources=["a"])
        d = ctx.to_dict()
        assert d["text"] == "test"
        assert d["token_count"] == 10
        assert d["data_sources"] == ["a"]
