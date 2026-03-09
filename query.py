"""
query.py — Enhanced FastAPI backend for SYNAPSE cBioPortal Transformer
=======================================================================
Extends the original Literature Retrieval app with:

  POST /detect/        — detect cBioPortal file type (heuristic + LLM few-shot)
  POST /transform/     — transform supplemental file → cBioPortal format
  POST /save_example/  — save a curator-corrected example for few-shot learning
  GET  /examples/      — list all saved few-shot examples
  DELETE /examples/{id}— remove an example
  POST /summarize/     — original endpoint (preserved)

All original endpoints are preserved unchanged.
"""

import os
import io
import json
import tempfile
import logging

import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from file_parser import parse_file, get_raw_text
from cbio_detector import detect_file_type
from cbio_transformer import transform_to_cbio, META_TEMPLATES, DATA_FILENAMES, META_FILENAMES
from few_shot_manager import save_example, list_examples, delete_example
from system_prompt_config import load_system_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SYNAPSE — cBioPortal Data Transformer",
    description=(
        "Upload any supplemental file. The AI auto-detects whether it is a "
        "clinical patient, clinical sample, mutation, CNA, expression, SV, "
        "timeline, or methylation file — then transforms it into the correct "
        "cBioPortal format. Curators can save examples to continuously improve accuracy."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_df_and_raw(file: UploadFile) -> tuple[pd.DataFrame, bytes]:
    raw = file.file.read()
    file.file.seek(0)
    df = parse_file(raw, file.filename)
    return df, raw


# ---------------------------------------------------------------------------
# NEW: Detect endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/detect/",
    summary="Auto-detect cBioPortal file type",
    response_description="Detection result with type, confidence, reasoning, and suggested column mappings",
)
async def detect(
    input_file: UploadFile = File(..., description="The supplemental file to classify"),
):
    """
    Detect whether the uploaded file is:
    clinical_patient, clinical_sample, mutation, cna_discrete,
    expression, structural_variant, timeline, or methylation.

    Uses fast column-name heuristics first; falls back to LLM few-shot detection
    when confidence is low.
    """
    try:
        df, _ = _get_df_and_raw(input_file)
        result = detect_file_type(
            df,
            anthropic_api_key=ANTHROPIC_API_KEY,
            openai_api_key=OPENAI_API_KEY,
        )
        result["columns"] = list(df.columns)
        result["row_count"] = len(df)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Detection failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# NEW: Transform endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/transform/",
    summary="Transform supplemental file to cBioPortal format",
)
async def transform(
    input_file: UploadFile = File(..., description="The supplemental file to transform"),
    cbio_type: str = Form(
        None,
        description=(
            "Target cBioPortal type. If omitted, auto-detected. "
            "Options: clinical_patient, clinical_sample, mutation, cna_discrete, "
            "expression, structural_variant, timeline, methylation"
        ),
    ),
    study_id: str = Form("my_study_2025", description="Cancer study identifier"),
    curator_notes: str = Form("", description="Optional hints for the AI (e.g. 'survival is in days')"),
    auto_detect: bool = Form(True, description="Auto-detect file type if cbio_type not provided"),
):
    """
    Full pipeline:
    1. Parse the uploaded file
    2. Auto-detect or use provided cBioPortal type
    3. Transform using AI + few-shot examples
    4. Return both data file and meta file content
    """
    try:
        df, raw_bytes = _get_df_and_raw(input_file)

        # Auto-detect if type not provided
        column_mappings = {}
        detection_result = {}
        if not cbio_type or auto_detect:
            detection_result = detect_file_type(
                df,
                anthropic_api_key=ANTHROPIC_API_KEY,
                openai_api_key=OPENAI_API_KEY,
            )
            if not cbio_type:
                cbio_type = detection_result["type"]
            column_mappings = detection_result.get("column_mappings", {})

        if cbio_type not in META_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown cbio_type '{cbio_type}'. Valid: {list(META_TEMPLATES.keys())}",
            )

        result = transform_to_cbio(
            df=df,
            cbio_type=cbio_type,
            study_id=study_id,
            column_mappings=column_mappings,
            curator_notes=curator_notes,
            anthropic_api_key=ANTHROPIC_API_KEY,
        )

        # Count output rows/cols for summary
        lines = [l for l in result["data_content"].splitlines() if l and not l.startswith("#")]
        out_rows = max(len(lines) - 1, 0)  # subtract header
        out_cols = len(lines[0].split("\t")) if lines else 0

        return JSONResponse(content={
            "cbio_type": cbio_type,
            "detection": detection_result,
            "data_content": result["data_content"],
            "meta_content": result["meta_content"],
            "data_filename": result["data_filename"],
            "meta_filename": result["meta_filename"],
            "summary": {
                "input_rows": len(df),
                "input_cols": len(df.columns),
                "output_rows": out_rows,
                "output_cols": out_cols,
                "study_id": study_id,
            },
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transform failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# NEW: Save few-shot example (curator feedback loop)
# ---------------------------------------------------------------------------

@app.post(
    "/save_example/",
    summary="Save a curator-corrected example for few-shot learning",
)
async def save_example_endpoint(
    input_file: UploadFile = File(..., description="Original supplemental file"),
    output_file: UploadFile = File(..., description="Curator-corrected cBioPortal output (TSV)"),
    cbio_type: str = Form(..., description="The correct cBioPortal type for this example"),
    description: str = Form("", description="Optional description of what this example teaches"),
):
    """
    Save a new training example. The AI will automatically use this example
    in future detection and transformation calls (no restart needed).
    """
    try:
        input_raw = await input_file.read()
        output_raw = await output_file.read()

        input_text = get_raw_text(input_raw, input_file.filename)
        output_text = output_raw.decode("utf-8", errors="replace")

        eid = save_example(
            input_tsv=input_text,
            output_tsv=output_text,
            cbio_type=cbio_type,
            description=description,
        )

        return JSONResponse(content={
            "message": f"Example {eid} saved successfully. It will be used in future calls.",
            "example_id": eid,
            "cbio_type": cbio_type,
        })
    except Exception as e:
        logger.exception("Save example failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# NEW: List examples
# ---------------------------------------------------------------------------

@app.get("/examples/", summary="List all saved few-shot examples")
async def list_examples_endpoint():
    return JSONResponse(content={"examples": list_examples()})


# ---------------------------------------------------------------------------
# NEW: Delete example
# ---------------------------------------------------------------------------

@app.delete("/examples/{example_id}", summary="Delete a few-shot example")
async def delete_example_endpoint(example_id: str):
    deleted = delete_example(example_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Example '{example_id}' not found")
    return JSONResponse(content={"message": f"Example {example_id} deleted."})


# ---------------------------------------------------------------------------
# PRESERVED: Original summarize endpoint
# ---------------------------------------------------------------------------

@app.post("/summarize/", summary="[Original] Summarize a file using RAG")
async def summarize(
    input_file: UploadFile = File(...),
    prompt_file: UploadFile = File(None),
    temperature: float = Form(0.7),
    top_k: int = Form(5),
):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, input_file.filename)
        with open(input_path, "wb") as f:
            f.write(await input_file.read())

        prompt = None
        if prompt_file:
            prompt_path = os.path.join(temp_dir, prompt_file.filename)
            with open(prompt_path, "wb") as f:
                f.write(await prompt_file.read())
            prompt = load_system_prompt(prompt_path)

        try:
            from backend_summary import summarize_file
            summary = summarize_file(input_path, prompt=prompt, temperature=temperature, top_k=top_k)
            return JSONResponse(content={"summary": summary})
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="backend_summary module not installed. Original summarize endpoint unavailable.",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
