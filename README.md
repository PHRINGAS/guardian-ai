# GuardianAI - Acelerador de Compliance (PoC)

**GuardianAI** es un prototipo de grado producción de un sistema de IA diseñado para acelerar las auditorías de compliance regulatorio. Utiliza una arquitectura avanzada de Generación Aumentada por Recuperación (RAG) para responder preguntas complejas sobre normativas legales, fusionando el texto oficial de la ley con análisis de expertos. Este servicio está desplegado como un microservicio seguro en Google Cloud Platform y cuenta con una interfaz web interactiva para su demostración.

---

## 📋 Funcionalidades Principales

- **Análisis de Compliance Multi-Fuente:** El sistema no solo consulta el texto de la ley, sino que lo enriquece con un corpus de análisis estratégico, permitiendo responder no solo a "¿Qué dice la ley?" sino también a "¿Qué implica y cómo debemos actuar?".

- **Pipeline RAG de Alta Precisión:** Utiliza un pipeline que incluye:
  1. **Embeddings** (text-embedding-3-large) para una comprensión semántica profunda.
  2. Una fase de **recuperación inicial** para encontrar documentos candidatos.
  3. Una fase de **reranking con Cross-Encoder** (BAAI/bge-reranker-base) para refinar y priorizar el contexto más relevante, mejorando drásticamente la precisión.

- **API Segura y Robusta:** El acceso al servicio está protegido mediante autenticación por **API Key** y cuenta con un **limitador de peticiones (rate limiting)** para prevenir abusos y controlar costos.

- **Reporte de Costos (FinOps):** Cada respuesta de la API incluye un desglose del **uso de tokens**, permitiendo un monitoreo y presupuestación precisos de los costos operativos.

- **Trazabilidad Completa:** Todas las peticiones son marcadas con un trace_id único, desde el middleware hasta la respuesta final, facilitando la depuración y auditoría.

- **Dashboard Interactivo:** Una interfaz web construida con Streamlit permite una fácil interacción con la API, visualización de resultados, métricas y fuentes.

---

## 🏛️ Arquitectura del Sistema

El proyecto está diseñado como un sistema de microservicios desacoplado, siguiendo las mejores prácticas de MLOps y seguridad en la nube.

- **Frontend:** Una aplicación **Streamlit** desplegada en Streamlit Community Cloud, que actúa como el cliente interactivo.

- **Backend API:**
  - **Framework:** **FastAPI** corriendo sobre Uvicorn.
  - **Contenerización:** La aplicación está empaquetada en una imagen **Docker** optimizada.
  - **Despliegue:** Servido globalmente a través de **Google Cloud Run**, permitiendo un escalado sin servidor.

- **Base de Conocimiento (RAG):**
  - **Base de Datos Vectorial:** **Qdrant Cloud** para almacenar los embeddings de los documentos.
  - **Modelos:**
    - **Embeddings:** OpenAI text-embedding-3-large.
    - **Reranker:** Open Source BAAI/bge-reranker-base ("horneado" en la imagen de Docker para arranques rápidos).
    - **Generación:** OpenAI gpt-5-mini.

- **Seguridad y Red:**
  - **Gestión de Secretos:** Todas las claves de API se gestionan de forma segura a través de **Google Secret Manager**.
  - **Identidad del Servicio:** Una **Cuenta de Servicio de IAM** dedicada con permisos de mínimo privilegio.
  - **Conectividad de Red:** El tráfico de salida de Cloud Run se enruta a través de un **Conector VPC Serverless y Cloud NAT** para garantizar una conectividad a Internet robusta y segura.

---

## 🚀 Cómo Probar el Servicio

### Prerrequisitos

- La URL del servicio desplegado.
- Una GUARDIAN_API_KEY válida.

### Opción 1: Usando el Dashboard Interactivo (Recomendado)

1. Navega a la URL del dashboard de Streamlit.
2. Introduce una consulta en el área de texto.
3. Haz clic en "Generar Análisis".

### Opción 2: Usando la Documentación de la API (Swagger UI)

1. Navega a la URL del servicio de Cloud Run y añade `/docs` al final. (Ej: `https://guardian-api-service-....run.app/docs`).
2. Haz clic en el botón verde **"Authorize"** en la esquina superior derecha.
3. Pega tu GUARDIAN_API_KEY en el campo "Value" y autoriza.
4. Expande el endpoint POST `/check-compliance`, haz clic en "Try it out" y ejecuta tu consulta.

### Opción 3: Usando curl desde la Terminal

```bash
curl -X 'POST' \
  'URL_DE_TU_API/check-compliance' \
  -H 'accept: application/json' \
  -H 'x-api-key: TU_GUARDIAN_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "Tu pregunta de compliance aquí...",
  "user_id": "curl_test_user"
}'
```

---

## ⚙️ Cómo Ejecutar el Proyecto Localmente

### Prerrequisitos

- Python 3.10+
- Docker y Docker Compose
- Una cuenta de OpenAI y Qdrant Cloud
- Un archivo `.env` en la raíz del proyecto con las siguientes claves:

```env
OPENAI_API_KEY="..."
QDRANT_URL="..."
QDRANT_API_KEY="..."
GUARDIAN_API_KEY="..."
API_URL="http://127.0.0.1:8000/check-compliance"
```

### Ejecución

1. Clona el repositorio:

```bash
git clone https://github.com/PHRINGAS/guardian-ai.git
cd guardian-ai
```

2. Crea y activa el entorno virtual:

```bash
python -m venv venv
source venv/Scripts/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
pip install -r dashboard/requirements.txt
```

4. Inicia el backend API:

```bash
uvicorn app.main:app --reload
```

5. Inicia el frontend (en otra terminal):

```bash
streamlit run dashboard/app.py
```

La aplicación estará disponible en `http://localhost:8501`.
