import re
import pandas as pd
from docx import Document
from PyPDF2 import PdfReader
from collections import Counter

KNOWN_GENES = {
    "TP53", "KRAS", "EGFR", "BRAF", "ALK", "PIK3CA",
    "PTEN", "BRCA1", "BRCA2", "NRAS", "APC", "CTNNB1"
}

def extract_text_from_pdf(file_bytes):
    reader = PdfReader(file_bytes)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_excel(file_bytes):
    df = pd.read_excel(file_bytes)
    return df.astype(str).apply(" ".join, axis=1).str.cat(sep=" ")

def extract_text_from_docx(file_bytes):
    doc = Document(file_bytes)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_genes(text):
    words = re.findall(r'\b[A-Z0-9\-]{3,}\b', text.upper())
    return [word for word in words if word in KNOWN_GENES]

def compute_gene_frequencies(genes):
    total = len(genes)
    counts = Counter(genes)
    return {gene: round((count / total) * 100, 2) for gene, count in counts.items()} if total else {}

def process_file(file):
    name = file.filename.lower()
    if name.endswith(".pdf"):
        text = extract_text_from_pdf(file.file)
    elif name.endswith(".xlsx"):
        text = extract_text_from_excel(file.file)
    elif name.endswith(".docx"):
        text = extract_text_from_docx(file.file)
    else:
        raise ValueError("Unsupported file type")
    genes = extract_genes(text)
    return compute_gene_frequencies(genes)