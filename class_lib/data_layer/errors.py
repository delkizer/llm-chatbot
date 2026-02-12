"""
Data Layer Exceptions

Data Layer 도메인 전용 예외 클래스
"""


class DataLayerError(Exception):
    """Data Layer 기본 예외"""
    pass


class APIConnectionError(DataLayerError):
    """API 연결 실패"""
    pass


class APIResponseError(DataLayerError):
    """API 응답 에러 (4xx, 5xx)"""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")


class CacheError(DataLayerError):
    """캐시 관련 에러"""
    pass
