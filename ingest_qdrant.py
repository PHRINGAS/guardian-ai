import os
import uuid
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models

load_dotenv()

# --- Configuración ---
QDRANT_URL = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]
QDRANT_COLLECTION_NAME = "gpdr_corpus" 
SOURCES = [
    {"name": "Ley 21.719 - Chile", "file": "ley_21719.txt"},
    {"name": "Análisis Experto 2024", "file": "analisis_experto_ley_21719.txt"}
]

def ingest_document(source_name: str, file_path: str, embedding_model, qdrant_client):
    """Procesa un único documento y lo inserta en Qdrant con la metadata correcta."""
    print(f"--- Procesando fuente: {source_name} desde {file_path} ---")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"ADVERTENCIA: Archivo no encontrado: {file_path}. Saltando este documento.")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = text_splitter.split_text(text)
    print(f"Texto dividido en {len(chunks)} chunks.")

    print("Generando embeddings...")
    vectors = embedding_model.embed_documents(chunks)
    print("Embeddings generados.")

    print("Insertando en Qdrant...")
    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=models.Batch(
            ids=[str(uuid.uuid4()) for _ in chunks],
            vectors=vectors,
            payloads=[{
                "page_content": chunk,
                "metadata": {"source_document": source_name, "article_number": "N/A"}
            } for chunk in chunks]
        ),
        wait=True
    )
    print(f"--- Fuente '{source_name}' procesada exitosamente. ---")

def main():
    print("Inicializando clientes...")
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    print(f"Recreando colección '{QDRANT_COLLECTION_NAME}' para una ingesta limpia...")
    qdrant_client.recreate_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        vectors_config=models.VectorParams(size=3072, distance=models.Distance.COSINE),
    )
    print("Colección recreada.")

    # Iteramos sobre todas las fuentes y las procesamos una por una
    for source in SOURCES:
        ingest_document(source["name"], source["file"], embedding_model, qdrant_client)

    print("\n¡Proceso de ingesta de todas las fuentes completado!")

if __name__ == "__main__":
    main()