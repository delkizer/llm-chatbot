import pytest


class TestHelloEndpoint:
    """GET /api/chat/hello/{name} 테스트"""

    def test_hello_english(self, client):
        """영문 이름"""
        response = client.get("/api/chat/hello/Claude")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello Claude"}

    def test_hello_korean(self, client):
        """한글 이름"""
        response = client.get("/api/chat/hello/클로드")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello 클로드"}

    def test_hello_with_space(self, client):
        """공백 포함 이름"""
        response = client.get("/api/chat/hello/Test%20User")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello Test User"}


class TestHealthEndpoint:
    """GET /api/chat/health 테스트"""

    def test_health_success(self, client):
        """헬스체크 성공"""
        response = client.get("/api/chat/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "ollama_host" in data
        assert "ollama_model" in data

    def test_health_response_format(self, client):
        """응답 형식 확인"""
        response = client.get("/api/chat/health")

        data = response.json()
        assert isinstance(data["ollama_host"], str)
        assert isinstance(data["ollama_model"], str)


class TestSwaggerDocs:
    """Swagger 문서 테스트"""

    def test_swagger_ui_available(self, client):
        """Swagger UI 접근 가능"""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json_available(self, client):
        """OpenAPI JSON 접근 가능"""
        response = client.get("/api/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_openapi_paths_exist(self, client):
        """필수 경로 존재 확인"""
        response = client.get("/api/openapi.json")
        paths = response.json()["paths"]

        assert "/api/chat/hello/{name}" in paths
        assert "/api/chat/health" in paths
        assert "/api/chat/" in paths
