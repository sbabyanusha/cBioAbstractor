# SYNAPSE — cBioPortal Data Transformer

An AI-powered tool that automatically detects and transforms any supplemental
clinical or genomic file into the correct [cBioPortal file format](https://docs.cbioportal.org/file-formats/).

Built on the original SYNAPSE Literature Retrieval platform.

---

## What's New

### Auto-Detection
Upload any CSV, TSV, TXT, or Excel file. The AI automatically identifies whether it is:

| Type | Detected by |
|------|-------------|
| `clinical_patient` | Patient-level columns: OS_STATUS, AGE, SEX, PATIENT_ID |
| `clinical_sample` | Sample-level columns: SAMPLE_ID, CANCER_TYPE, SUBTYPE |
| `mutation` | MAF columns: Hugo_Symbol, Chromosome, Variant_Classification |
| `cna_discrete` | Gene matrix with values in {-2,-1,0,1,2} |
| `expression` | Gene matrix with continuous float values |
| `structural_variant` | Site1/Site2 gene columns, SV_Status |
| `timeline` | START_DATE, STOP_DATE, EVENT_TYPE |
| `methylation` | Gene matrix with beta values in [0,1] |

### AI Transformation
The AI maps your column names → cBioPortal schema, adds the correct 5-row
clinical headers, normalizes survival status values, and generates the matching
`meta_*.txt` file.

### Few-Shot Learning (Self-Improving AI)
The AI learns from curator-validated examples **at inference time** — no
retraining, no code changes, no restart needed.

**To teach the AI a new file pattern:**
1. Upload your file in the UI
2. Review the AI's output
3. Edit it until it's correct
4. Click **"Save as Training Example"**

The next time a similar file is uploaded, the AI will use your example.

---

## Architecture

```
synapse_cbio/
├── query.py              # FastAPI backend (new endpoints + preserved originals)
├── streamlit_app.py      # Streamlit UI (transform + train + literature retrieval)
├── cbio_detector.py      # Auto-detection: heuristics → LLM few-shot
├── cbio_transformer.py   # LLM-powered transformation with few-shot injection
├── few_shot_manager.py   # Persist/load/delete curator examples
├── file_parser.py        # Parse CSV/TSV/Excel → DataFrame
├── config.py             # Settings and env vars
├── system_prompt_config.py
├── few_shot_examples/    # Auto-generated; stores curator examples
│   ├── 001.input.tsv
│   ├── 001.output.tsv
│   ├── 001.type.txt      # e.g. "clinical_patient"
│   └── 001.meta.json
└── requirements.txt
```

---

## Setup

```bash
# 1. Clone
git clone https://github.com/sbabyanusha/pixel.git
cd pixel/synapse

# 2. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...     # optional, for original RAG features

# 4. Run backend
uvicorn query:app --reload --port 8000

# 5. Run UI (separate terminal)
streamlit run streamlit_app.py
```

---

## API Endpoints

### New

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/detect/` | Auto-detect cBioPortal file type |
| `POST` | `/transform/` | Transform file → cBioPortal format |
| `POST` | `/save_example/` | Save a curator example for few-shot learning |
| `GET`  | `/examples/` | List all saved examples |
| `DELETE` | `/examples/{id}` | Delete an example |

### Preserved (original)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/summarize/` | Original RAG summarization |
| `POST` | `/ingest_pdf/` | Ingest PDF into vector store |
| `POST` | `/generate_evidence/` | Generate evidence-based answers |
| `POST` | `/clear_vector_store/` | Clear ChromaDB |

---

## Docker

```bash
docker build -t synapse-cbio .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  -v $(pwd)/few_shot_examples:/app/few_shot_examples \
  synapse-cbio
```

Mount `few_shot_examples/` as a volume so curator examples persist across container restarts.

---

## cBioPortal Format Reference

https://docs.cbioportal.org/file-formats/

## License

MIT
