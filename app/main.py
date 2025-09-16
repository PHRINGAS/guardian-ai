from dotenv import load_dotenv

load_dotenv()
import os
import uuid
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.security import APIKeyHeader
import structlog

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


from app.schemas import ComplianceQuery, ComplianceReport
from app.core import run_compliance_pipeline

def get_request_identifier(request: Request) -> str:
    """
    Identifica al cliente por la cabecera X-Forwarded-For (si existe) o por su IP directa.
    Es una forma más robusta de identificar al cliente en un entorno de nube.
    """
    return request.headers.get("x-forwarded-for", request.client.host)

# --- CONFIGURACIÓN DE SEGURIDAD ---
API_KEY_HEADER = APIKeyHeader(name="x-api-key", auto_error=False)
SECRET_API_KEY = os.getenv("GUARDIAN_API_KEY")
limiter = Limiter(key_func=get_request_identifier)

async def get_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    """
    Dependencia de seguridad. Verifica la API key del header contra la secreta.
    """
    if not SECRET_API_KEY:
        raise HTTPException(status_code=500, detail="Error de configuración del servidor: la API Key no está definida.")
    if api_key_header == SECRET_API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=401, detail="API Key inválida o faltante.")

#------ Configuración del logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.JSONRenderer()
    ],
)
logger = structlog.get_logger()
#--------------------------------------------------

app = FastAPI(
    title="GuardianAI - Compliance Accelerator",
    description="Un acelerador de Dicsys para auditorías de compliance usando IA Generativa.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MIddleware para Trace ID y Loggin de Requests ---
@app.middleware("http")
async def log_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    logger.info("request_started", method=request.method, url=str(request.url))
    response = await call_next(request)
    logger.info("request_finished", status_code=response.status_code)
    response.headers["X-Trace-ID"] = trace_id
    return response

#--------------------------------------------------

@app.get("/health", summary="Verifica el estado del servicio")
def health_check():
    """
    Endpoint para monitoreo. Devuelve 200 si el servicio esta activo.
    """
    logger.info("Health check ok")
    return {"status": "ok"}

@app.post("/check-compliance", response_model=ComplianceReport, summary="Realiza un análisis de compliance", tags=["Compliance"], dependencies=[Security(get_api_key)])
@limiter.limit("10/minute")
async def check_compliance(request: Request, query: ComplianceQuery):
    """
    Recibe una consulta, realiza un análisis RAG contra un corpus de normativas
    y devuelve un reporte estructurado.
    """
    log = logger.bind(user_id=query.user_id)
    log.info("compliance_check_initiated")
    
    trace_id = structlog.contextvars.get_contextvars().get("trace_id")
    
    try:
        result = await run_compliance_pipeline(query, trace_id)
        report = ComplianceReport(**result)
        log.info("compliance_check_successful")
        return report
    except Exception as e:
        log.error("pipeline_execution_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno en el procesamiento. Trace ID: {trace_id}")
