"""
config.py
---------
Central configuration for cBioAbstractor.
All tunable constants live here.

Notes
-----
The Anthropic API key is read directly from the ANTHROPIC_API_KEY environment
variable (or Streamlit secret / sidebar input) inside streamlit_app.py, so it
deliberately is not re-exported here.
"""
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
FEW_SHOT_DIR = os.getenv("FEW_SHOT_DIR", "./few_shot_examples")

# ── Detection / transform settings ────────────────────────────────────────────
DETECTION_SAMPLE_ROWS          = 10    # rows sampled for type detection
TRANSFORM_SAMPLE_ROWS          = 20    # rows sampled for LLM transform
DETECTION_CONFIDENCE_THRESHOLD = 0.6   # below this → fall back to LLM detection
