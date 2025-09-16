from sentence_transformers import CrossEncoder

def main():
    print("Descargando y cacheadando el modelo de reranker...")
    # Esta línea buscará el modelo. Si no está en el cache, lo descargará.
    CrossEncoder('BAAI/bge-reranker-base')
    print("Modelo descargado y cacheado exitosamente.")

if __name__ == "__main__":
    main()