from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

def process_pdf(file_path: str):
    loader = PyPDFLoader(file_path)
    loaded_documents = loader.load()
    documents = [Document(page_content=doc.page_content, metadata={"source": doc.metadata}) for doc in loaded_documents]
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_documents(documents)