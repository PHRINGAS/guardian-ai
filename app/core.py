import os
import structlog
import asyncio
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain.schema.output_parser import StrOutputParser  # unused, avoid import errors with newer langchain
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

from app.schemas import ComplianceQuery, DocumentSource, TokenUsage

logger = structlog.get_logger()

# --- Incicialización de Clientes y Modelo ---

try:
    logger.info("Initializing Qdrant client...")
    qdrant_client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ.get("QDRANT_API_KEY"))
    logger.info("Qdrant client initialized.")

    logger.info("Initializing OpenAI embedding model...")
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
    logger.info("OpenAI embedding model initialized.")

    logger.info("Initializing reranker model...")
    reranker_model = CrossEncoder('BAAI/bge-reranker-base', local_files_only=True)
    logger.info("Reranker model initialized.")

    logger.info("Initializing OpenAI chat model...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    logger.info("OpenAI chat model initialized.")

    logger.info("All clients initialized successfully")
except KeyError as e:
    logger.error("Missing environment variable", error=str(e))
    raise RuntimeError(f"Falta la variable de entorno: {e}")
except Exception as e:
    logger.error("An error occurred during client initialization", error=str(e), exc_info=True)
    raise

QDRANT_COLLECTION_NAME = "gpdr_corpus"

def rerank_documents(query: str, docs:list[Document]) -> list[Document]:
    if not docs:
        return []
    pairs = [[query, doc.page_content] for doc in docs]
    scores = reranker_model.predict(pairs)
    doc_scores = list(zip(docs, scores))
    doc_scores.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, score in doc_scores]

def format_docs_for_prompt(docs: list[Document]) -> str:
    """Prepara el contenido de los documentos, indicando el origen de cada uno."""
    formatted_chunks = []
    for doc in docs:
        # Extraemos el nombre de la fuente desde la metadata que guardamos durante la ingesta
        source_name = doc.metadata.get('source_document', 'Fuente Desconocida')
        chunk_content = (
            f"--- INICIO DEL FRAGMENTO DE: {source_name} ---\n"
            f"Contenido: {doc.page_content}\n"
            f"--- FIN DEL FRAGMENTO ---\n"
        )
        formatted_chunks.append(chunk_content)
    return "\n".join(formatted_chunks)

# Función clave del pipeline, completamente asincrónica y no bloqueante

async def run_compliance_pipeline(query: ComplianceQuery, trace_id: str) -> dict:
    log = logger.bind(trace_id=trace_id, user_id=query.user_id)

    # Loop de eventos
    loop = asyncio.get_running_loop()

    # --- 1. ETAPA DE RECUPERACIÓN ---
    log.info("retrieval_started")
    query_embedding = await embedding_model.aembed_query(query.text)

    # run_in_executor para la llamada síncrona a la base de datos
    retrieved_points = await loop.run_in_executor(
        None,
        lambda: qdrant_client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            limit=20,
            with_payload=True
        )
    )

    retrieved_docs = [
        Document(page_content=point.payload['page_content'], metadata=point.payload['metadata'])
        for point in retrieved_points
    ]
    log.info("retrieval_finished", num_docs=len(retrieved_docs))
    
    # --- 2. ETAPA DE RERANKING ---
    log.info("reranking_started")
    reranked_docs = await loop.run_in_executor(
        None, rerank_documents, query.text, retrieved_docs
    )
    final_context_docs = reranked_docs[:5]  # Variable de chunks que quedarán
    log.info("reranking_finished", num_docs_after=len(final_context_docs))

    # --- 3. ETAPA DE GENERACIÓN ---
    log.info("llm_generation_started")
    prompt = ChatPromptTemplate.from_template(
        """
        Eres **GuardianAI**, asesor estratégico de IA para la consultora Dicsys, especializado en la nueva Ley de Protección de Datos de Chile (Ley 21.719).
        **Tu misión:** brindar respuestas claras, precisas y accionables, combinando dos fuentes principales:  
        - El texto oficial de la ley.  
        - El análisis estratégico experto de la base de conocimiento.
        ---
        ### Contexto Recuperado
        {context}
        ### Consulta del Cliente
        {question}
        ---
        ### Instrucciones de Respuesta
        1. **Sintetiza e integra**: No repitas literalmente el contexto. Combina lo normativo con el análisis estratégico para dar una visión completa.  
        2. **Distingue fuentes**:  
        - Lo que dice la ley → “Según el Artículo X de la Ley 21.719...”  
        - Lo que aporta el análisis → “El análisis estratégico indica que el principal desafío es...”  
        3. **Tono consultivo**: Comunica como un consultor de negocio: ejecutivo, claro y orientado a la acción. Prioriza riesgos y oportunidades.  
        4. **Recomendaciones**: Siempre que sea posible, ofrece una hoja de ruta o pasos concretos aplicables al cliente.  
        5. **Citas**: Al final, incluye una breve lista de los documentos/contextos utilizados (formato: lista con título o identificador).  
        6. **Si falta información**: Señala la limitación y sugiere la mejor aproximación estratégica posible.  
        7. **Disclaimer obligatorio**: Cierra siempre con:  
        > *Nota: Esta respuesta es de carácter informativo y estratégico. No constituye asesoramiento legal formal.*  
        """
    )
    chain_without_parser = prompt | llm
    context_str = format_docs_for_prompt(final_context_docs)
    llm_response = await chain_without_parser.ainvoke({"context": context_str, "question": query.text})
    
    analysis_result = llm_response.content
    token_usage_data = llm_response.response_metadata.get("token_usage", {})

    token_usage = TokenUsage(
        prompt_tokens=token_usage_data.get("prompt_tokens", 0),
        completion_tokens=token_usage_data.get("completion_tokens", 0),
        total_tokens=token_usage_data.get("total_tokens", 0)
    )

    log.info("llm_generation_finished", 
             prompt_tokens=token_usage.prompt_tokens, 
             completion_tokens=token_usage.completion_tokens)

    # --- 4. ETAPA DE FORMATEO DE RESPUESTA ---
    sources = [
        DocumentSource(
            source_document=doc.metadata.get('source_document', 'Desconocido'),
            article_number=doc.metadata.get('article_number', 'N/A'),
            content_chunk=doc.page_content
        ) for doc in final_context_docs
    ]
    
    return {
        "analysis": analysis_result,
        "sources": sources,
        "token_usage": token_usage,
        "trace_id": trace_id,
    }
