import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

VECTORSTORE_DIR = "./vector_store"
collection_name = "pdf_chunks"
embeddings_model = OpenAIEmbeddings()

vector_store = Chroma(
    collection_name=collection_name,
    embedding_function=embeddings_model,
    persist_directory=VECTORSTORE_DIR
)

def add_embeddings(chunks):
    texts = [chunk.page_content for chunk in chunks]
    metadata = [{"source": chunk.metadata["source"]} for chunk in chunks]
    vector_store.add_texts(texts=texts, metadata=metadata)
    return len(texts)

def search_vector_store(question, k=5):
    query_embedding = embeddings_model.embed_query(question)
    results = vector_store.similarity_search_by_vector(query_embedding, k=k)
    return [doc.page_content for doc in results]

def clear_vector_store():
    vector_store.delete_collection()
    global vector_store
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings_model,
        persist_directory=VECTORSTORE_DIR
    )