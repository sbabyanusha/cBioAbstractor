"""
streamlit_app.py — SYNAPSE cBioPortal Transformer UI
=====================================================
Replaces the original streamlit_app.py with a full cBioPortal transformation
workflow while keeping the original Literature Retrieval section.
"""

import io
import json
import zipfile

import pandas as pd
import requests
import streamlit as st

# ── Config ───────────────────────────────────────────────────────────────────
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

CBIO_TYPE_LABELS = {
    "clinical_patient":  "🧑‍⚕️  Clinical — Patient",
    "clinical_sample":   "🧬  Clinical — Sample",
    "mutation":          "🔬  Mutation Data (MAF)",
    "cna_discrete":      "📊  Copy Number Alteration (Discrete)",
    "expression":        "📈  mRNA Expression",
    "structural_variant":"🔗  Structural Variant / Fusion",
    "timeline":          "📅  Timeline",
    "methylation":       "🧪  Methylation",
}

CONFIDENCE_COLOR = lambda c: "🟢" if c >= 0.8 else ("🟡" if c >= 0.5 else "🔴")

st.set_page_config(
    page_title="SYNAPSE · cBioPortal Transformer",
    page_icon="⬡",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap');
[data-testid="stSidebar"] { background: #060e16; }
.stButton > button {
    background: linear-gradient(135deg,#00c896,#00a8ff);
    color: #060e16; font-weight: 800; border: none; border-radius: 10px;
}
.block-container { padding-top: 1.5rem; }
.detection-card {
    background: #0a1420; border: 1px solid #0d3a2e; border-radius: 12px;
    padding: 18px 24px; margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⬡ SYNAPSE")
    st.markdown("**cBioPortal Data Transformer**")
    st.divider()

    nav = st.radio(
        "Navigate",
        ["🔄 Transform File", "🧠 Train AI (Save Examples)", "📚 Example Library", "🔬 Literature Retrieval"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Formats supported:")
    for k, v in CBIO_TYPE_LABELS.items():
        st.caption(f"  {v}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSFORM FILE
# ══════════════════════════════════════════════════════════════════════════════

if nav == "🔄 Transform File":
    st.title("🔄 Transform Supplemental File → cBioPortal")
    st.markdown(
        "Upload **any** supplemental file (CSV, TSV, TXT, Excel). "
        "The AI will **automatically detect** its type, then transform it into the "
        "correct cBioPortal format with matching meta file."
    )

    # ── Upload ────────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Drop supplemental file here",
        type=["csv", "tsv", "txt", "tab", "xlsx", "xls"],
        help="Any clinical or genomic supplemental file from Synapse, REDCap, GENIE, etc.",
    )

    if uploaded:
        raw_bytes = uploaded.read()
        uploaded.seek(0)

        st.success(f"📄 **{uploaded.name}** · {len(raw_bytes)/1024:.1f} KB")

        # Quick preview
        try:
            text = raw_bytes.decode("utf-8", errors="replace")
            lines = text.splitlines()
            preview_lines = [l for l in lines[:12] if not l.startswith("#")]
            st.code("\n".join(preview_lines[:8]), language="text")
        except Exception:
            pass

        st.divider()

        # ── Detection ─────────────────────────────────────────────────────────
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Step 1 — File Type Detection")
            detect_clicked = st.button("🔍 Auto-Detect File Type", use_container_width=True)

        if detect_clicked or "detection_result" in st.session_state:
            if detect_clicked:
                with st.spinner("Analyzing file structure…"):
                    resp = requests.post(
                        f"{API_URL}/detect/",
                        files={"input_file": (uploaded.name, raw_bytes, "application/octet-stream")},
                        timeout=60,
                    )
                if resp.status_code == 200:
                    st.session_state["detection_result"] = resp.json()
                    st.session_state["uploaded_name"] = uploaded.name
                    st.session_state["uploaded_bytes"] = raw_bytes
                else:
                    st.error(f"Detection failed: {resp.text}")

            dr = st.session_state.get("detection_result", {})
            if dr:
                conf = dr.get("confidence", 0)
                dtype = dr.get("type", "")

                st.markdown(f"""
<div class="detection-card">
<b>Detected Type:</b> {CBIO_TYPE_LABELS.get(dtype, dtype)}<br>
<b>Confidence:</b> {CONFIDENCE_COLOR(conf)} {conf:.0%}  &nbsp;&nbsp;
<b>Method:</b> {dr.get('method','')}<br>
<b>Reasoning:</b> <i>{dr.get('reasoning','')}</i><br>
<b>Input:</b> {dr.get('row_count','')} rows × {len(dr.get('columns',[]))} columns
</div>
""", unsafe_allow_html=True)

                if dr.get("column_mappings"):
                    with st.expander("Suggested column mappings"):
                        st.json(dr["column_mappings"])

                if dr.get("low_confidence"):
                    st.warning("⚠️ Low confidence — please verify or override the detected type below.")

        # ── Configuration ─────────────────────────────────────────────────────
        st.subheader("Step 2 — Configure")

        dr = st.session_state.get("detection_result", {})
        detected_type = dr.get("type", "clinical_sample")

        type_options = list(CBIO_TYPE_LABELS.keys())
        default_idx = type_options.index(detected_type) if detected_type in type_options else 0

        selected_type = st.selectbox(
            "Target cBioPortal format",
            options=type_options,
            index=default_idx,
            format_func=lambda x: CBIO_TYPE_LABELS[x],
        )

        col_a, col_b = st.columns(2)
        with col_a:
            study_id = st.text_input(
                "Cancer Study Identifier",
                value="my_study_2025",
                help="e.g. brca_tcga_2024",
            ).strip().lower().replace(" ", "_")
        with col_b:
            curator_notes = st.text_area(
                "Curator Notes (optional)",
                placeholder="e.g. 'survival column is in days, not months'\n'map column X to PATIENT_ID'",
                height=80,
            )

        # ── Transform ─────────────────────────────────────────────────────────
        st.subheader("Step 3 — Transform")

        transform_clicked = st.button("⚡ Transform to cBioPortal Format", use_container_width=True, type="primary")

        if transform_clicked:
            use_bytes = st.session_state.get("uploaded_bytes", raw_bytes)
            use_name = st.session_state.get("uploaded_name", uploaded.name)

            with st.spinner(f"Transforming to {CBIO_TYPE_LABELS[selected_type]}…"):
                resp = requests.post(
                    f"{API_URL}/transform/",
                    files={"input_file": (use_name, use_bytes, "application/octet-stream")},
                    data={
                        "cbio_type": selected_type,
                        "study_id": study_id,
                        "curator_notes": curator_notes,
                        "auto_detect": "false",
                    },
                    timeout=120,
                )

            if resp.status_code == 200:
                result = resp.json()
                st.session_state["transform_result"] = result
                st.success("✅ Transformation complete!")
            else:
                st.error(f"Transform failed: {resp.text}")

        # ── Results ───────────────────────────────────────────────────────────
        if "transform_result" in st.session_state:
            result = st.session_state["transform_result"]
            summary = result.get("summary", {})

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Input Rows", summary.get("input_rows", "—"))
            m2.metric("Input Cols", summary.get("input_cols", "—"))
            m3.metric("Output Rows", summary.get("output_rows", "—"))
            m4.metric("Output Cols", summary.get("output_cols", "—"))

            tab_data, tab_meta, tab_train = st.tabs(
                [f"📄 {result['data_filename']}", f"⚙️ {result['meta_filename']}", "🧠 Save as Training Example"]
            )

            with tab_data:
                st.code(result["data_content"], language="text")
                st.download_button(
                    f"⬇ Download {result['data_filename']}",
                    data=result["data_content"],
                    file_name=result["data_filename"],
                    mime="text/plain",
                    use_container_width=True,
                )

            with tab_meta:
                st.code(result["meta_content"], language="text")
                st.download_button(
                    f"⬇ Download {result['meta_filename']}",
                    data=result["meta_content"],
                    file_name=result["meta_filename"],
                    mime="text/plain",
                    use_container_width=True,
                )

            # Download both as ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                zf.writestr(result["data_filename"], result["data_content"])
                zf.writestr(result["meta_filename"], result["meta_content"])
            zip_buf.seek(0)
            st.download_button(
                "⬇ Download Both Files (ZIP)",
                data=zip_buf,
                file_name=f"{study_id}_cbio_files.zip",
                mime="application/zip",
                use_container_width=True,
            )

            with tab_train:
                st.markdown("""
**Is this output correct?**
If you edit the output above and want the AI to learn from this example,
paste the corrected TSV below and click **Save as Training Example**.
""")
                corrected = st.text_area(
                    "Corrected cBioPortal output (paste edited version)",
                    value=result["data_content"],
                    height=300,
                    key="corrected_output",
                )
                train_desc = st.text_input("Description (optional)", placeholder="e.g. REDCap clinical patient file with days→months conversion")

                if st.button("💾 Save as Training Example"):
                    use_bytes = st.session_state.get("uploaded_bytes", raw_bytes)
                    use_name = st.session_state.get("uploaded_name", uploaded.name)
                    save_resp = requests.post(
                        f"{API_URL}/save_example/",
                        files={
                            "input_file": (use_name, use_bytes, "application/octet-stream"),
                            "output_file": ("output.tsv", corrected.encode(), "text/plain"),
                        },
                        data={"cbio_type": selected_type, "description": train_desc},
                        timeout=30,
                    )
                    if save_resp.status_code == 200:
                        st.success(f"✅ {save_resp.json()['message']}")
                    else:
                        st.error(f"Save failed: {save_resp.text}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TRAIN AI
# ══════════════════════════════════════════════════════════════════════════════

elif nav == "🧠 Train AI (Save Examples)":
    st.title("🧠 Train the AI — Add Few-Shot Examples")
    st.markdown("""
The AI learns from **curator-validated example pairs**.
Each example teaches it how to handle a specific file pattern.

**How it works:**
1. Upload an input file (any supplemental file)
2. Upload the correct cBioPortal output for that file
3. Label the type — the AI will use this example immediately in future calls, no restart needed.
""")

    col1, col2 = st.columns(2)
    with col1:
        train_input = st.file_uploader("Input file (raw supplemental)", key="train_input")
    with col2:
        train_output = st.file_uploader("Correct cBioPortal output (TSV)", key="train_output")

    train_type = st.selectbox(
        "cBioPortal type of this example",
        options=list(CBIO_TYPE_LABELS.keys()),
        format_func=lambda x: CBIO_TYPE_LABELS[x],
        key="train_type",
    )
    train_desc = st.text_input("Description (what does this example teach?)", key="train_desc")

    if st.button("💾 Save Training Example", type="primary") and train_input and train_output:
        resp = requests.post(
            f"{API_URL}/save_example/",
            files={
                "input_file": (train_input.name, train_input.read(), "application/octet-stream"),
                "output_file": (train_output.name, train_output.read(), "text/plain"),
            },
            data={"cbio_type": train_type, "description": train_desc},
            timeout=30,
        )
        if resp.status_code == 200:
            d = resp.json()
            st.success(f"✅ Saved example **{d['example_id']}** for `{d['cbio_type']}`. "
                       "The AI will use this in all future calls.")
        else:
            st.error(f"Failed: {resp.text}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EXAMPLE LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

elif nav == "📚 Example Library":
    st.title("📚 Few-Shot Training Example Library")
    st.markdown("All curator-saved examples the AI is currently learning from.")

    resp = requests.get(f"{API_URL}/examples/", timeout=10)
    if resp.status_code == 200:
        examples = resp.json().get("examples", [])
        if not examples:
            st.info("No examples saved yet. Go to **Train AI** to add your first example.")
        else:
            st.metric("Total Examples", len(examples))
            # Group by type
            by_type: dict[str, list] = {}
            for ex in examples:
                by_type.setdefault(ex["type"], []).append(ex)

            for t, exs in by_type.items():
                with st.expander(f"{CBIO_TYPE_LABELS.get(t, t)}  ·  {len(exs)} example(s)"):
                    for ex in exs:
                        c1, c2, c3 = st.columns([1, 3, 1])
                        c1.code(ex["id"])
                        c2.write(ex.get("description") or "_no description_")
                        c3.caption(ex.get("created_at", "")[:10])
                        if c3.button("🗑 Delete", key=f"del_{ex['id']}"):
                            del_resp = requests.delete(f"{API_URL}/examples/{ex['id']}", timeout=10)
                            if del_resp.status_code == 200:
                                st.success(f"Deleted {ex['id']}")
                                st.rerun()
    else:
        st.error("Could not reach API.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ORIGINAL LITERATURE RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════════

elif nav == "🔬 Literature Retrieval":
    st.title("🔬 Literature Retrieval Evidence Summarization")
    st.markdown("_Original SYNAPSE functionality — preserved unchanged._")

    with st.expander("📥 Vector Store Management", expanded=False):
        uploaded_pdfs = st.file_uploader(
            "Upload PDF files", accept_multiple_files=True, type="pdf"
        )
        if st.button("Load PDFs"):
            if uploaded_pdfs:
                for pdf in uploaded_pdfs:
                    resp = requests.post(
                        f"{API_URL}/ingest_pdf/",
                        files={"file": (pdf.name, pdf.getvalue())},
                    )
                    if resp.status_code == 200:
                        st.success(f"✅ {pdf.name} ingested.")
                    else:
                        st.error(f"❌ {pdf.name} failed: {resp.text}")
            else:
                st.warning("Upload PDF files first.")

        if st.button("🗑 Clear Vector Store"):
            resp = requests.post(f"{API_URL}/clear_vector_store/")
            if resp.status_code == 200:
                st.success("Vector store cleared.")
            else:
                st.error("Clear failed.")

    question = st.text_input("Provide the parameters to generate evidence-based answers")
    if st.button("Get Answer"):
        if question:
            with st.spinner("Processing…"):
                resp = requests.post(f"{API_URL}/generate_evidence/", data={"question": question})
                if resp.status_code == 200:
                    st.write("**Answer:**")
                    st.write(resp.json()["answer"])
                else:
                    st.error("Error fetching answer.")
        else:
            st.warning("Please enter a question.")
