import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Obtenemos la API key de prueba desde las variables de entorno
TEST_API_KEY = os.getenv("GUARDIAN_API_KEY", "test_key_123")
HEADERS = {"x-api-key": TEST_API_KEY}

def test_health_check():
    """Prueba que el endpoint de salud funciona sin autenticación."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_compliance_check_no_auth():
    """Prueba que el endpoint protegido devuelve 401 Unauthorized sin una API key."""
    response = client.post("/check-compliance", json={"text": "test query"})
    assert response.status_code == 401
    assert "inválida o faltante" in response.json()["detail"]

def test_compliance_check_wrong_auth():
    """Prueba que el endpoint protegido devuelve 401 Unauthorized con una API key incorrecta."""
    response = client.post(
        "/check-compliance", 
        headers={"x-api-key": "esta-clave-es-incorrecta"},
        json={"text": "test query"}
    )
    assert response.status_code == 401

def test_compliance_check_mocked_success(mocker):
    """
    Prueba una llamada exitosa al endpoint, mockeando el pipeline de IA
    para que la prueba sea rápida y no dependa de servicios externos.
    """
    # Simulamos la respuesta
    mock_pipeline_result = {
        "analysis": "Análisis simulado.",
        "sources": [],
        "token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "trace_id": "mock_trace_id"
    }
    
    # mock-data
    mocker.patch("app.main.run_compliance_pipeline", return_value=mock_pipeline_result)

    
    response = client.post(
        "/check-compliance",
        headers=HEADERS,
        json={"text": "Esta es una consulta de prueba válida."}
    )
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["analysis"] == "Análisis simulado."
    assert response_data["token_usage"]["total_tokens"] == 30