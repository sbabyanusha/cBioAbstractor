import os

DEFAULT_SYSTEM_PROMPT = (
    "You are a bioinformatician that only provides answers based on the given documents. "
    "If the information is not available in the documents, respond with "
    "'I do not know the answer based on the provided documents.'"
)

CBIO_TRANSFORM_SYSTEM_PROMPT = (
    "You are a bioinformatics data curation expert specializing in cBioPortal data formats. "
    "Transform input data into the exact cBioPortal file format specified. "
    "Return ONLY the correctly formatted TSV — no explanations, no markdown fences, no preamble."
)


def load_system_prompt(path: str) -> str:
    """Load a system prompt from a text file, or return the default."""
    if path and os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return DEFAULT_SYSTEM_PROMPT
