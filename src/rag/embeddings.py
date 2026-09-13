"""
embeddings.py
Indexa el manual interno de políticas (PDF) en ChromaDB para el pipeline RAG.
"""

import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

def build_embeddings():
    # ---------------------------------------------------------------------------
    # Configuración
    # ---------------------------------------------------------------------------
    SOURCE_FILE = "resources/Manual Interno de Empleados — Aurion Consulting.pdf"
    PERSIST_DIR = "resources/chroma_db"
    COLLECTION_NAME = "manual_politicas_aurion"
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    # ---------------------------------------------------------------------------
    # 1. Carga del documento
    # ---------------------------------------------------------------------------
    loader = PyPDFLoader(SOURCE_FILE)
    data = loader.load()

    # ---------------------------------------------------------------------------
    # 2. Modelo de embeddings
    # ---------------------------------------------------------------------------
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # ---------------------------------------------------------------------------
    # 3. Semantic Chunker
    # ---------------------------------------------------------------------------
    text_splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90,
    )

    all_splits = text_splitter.split_documents(data)

    # Metadata común de origen (PyPDFLoader ya añade "source" y "page" por chunk,
    # pero lo normalizamos por si el path cambia entre entornos)
    for doc in all_splits:
        doc.metadata["source"] = "manual_politicas_aurion"

    print(f"Documento dividido en {len(all_splits)} chunks")

    # ---------------------------------------------------------------------------
    # 4. Persistencia en ChromaDB
    # ---------------------------------------------------------------------------
    os.makedirs(PERSIST_DIR, exist_ok=True)
    
    try:
        Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIR,
        ).delete_collection()
    except Exception:
        pass

    # Creamos la colección desde cero, limpia
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )

    ids = vector_store.add_documents(documents=all_splits)

    print(f"{len(ids)} chunks indexados en '{PERSIST_DIR}' (colección: {COLLECTION_NAME})")
    
if __name__ == "__main__":
    build_embeddings()