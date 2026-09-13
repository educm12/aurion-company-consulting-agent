"""
retriever.py
Carga la colección persistida en ChromaDB y expone el retriever del RAG
para que lo use el agente (LangChain).
"""

from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración (debe coincidir exactamente con la usada en embeddings.py)
# ---------------------------------------------------------------------------
PERSIST_DIR = "resources/chroma_db"
COLLECTION_NAME = "manual_politicas_aurion"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_retriever(k: int = 4, search_type: str = "similarity"):
    """
    Devuelve un retriever de LangChain sobre la colección de Chroma
    ya indexada (manual de políticas de Aurion Consulting).

    Args:
        k: número de chunks a recuperar por consulta.
        search_type: "similarity", "mmr" o "similarity_score_threshold".

    Returns:
        Un VectorStoreRetriever listo para usar como tool del agente.
    """
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )

    retriever = vector_store.as_retriever(
        search_type=search_type,
        search_kwargs={"k": k},
    )

    return retriever


# ---------------------------------------------------------------------------
# Prueba rápida manual: python retriever.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    retriever = get_retriever()

    query = "¿Cuántos días de vacaciones tiene un empleado con más de cinco años de antigüedad?"
    results = retriever.invoke(query)

    print(f"Consulta: {query}\n")
    for i, doc in enumerate(results, start=1):
        print(f"--- Resultado {i} ---")
        print(doc.page_content[:300].replace("\n", " "), "...")
        print("Metadata:", doc.metadata)
        print()