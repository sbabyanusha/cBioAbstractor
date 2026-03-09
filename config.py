import os

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Vector store
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store")
PUBLICATIONS_DIR = "publications"

# Few-shot examples directory — drop sample input/output pairs here for in-context learning
FEW_SHOT_DIR = os.getenv("FEW_SHOT_DIR", "./few_shot_examples")

# cBioPortal supported format identifiers
CBIO_FORMAT_IDS = [
    "clinical_patient",
    "clinical_sample",
    "mutation",
    "cna_discrete",
    "expression",
    "structural_variant",
    "timeline",
    "methylation",
]

# Confidence threshold below which the system will ask user to confirm detected type
DETECTION_CONFIDENCE_THRESHOLD = 0.6

# Max rows to use for detection (keep fast)
DETECTION_SAMPLE_ROWS = 20

# Max rows to send to the transform LLM
TRANSFORM_SAMPLE_ROWS = 300
