import os, json, re, subprocess, sys, tempfile, textwrap
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent.workflow import run_analysis
from safety import validate_generated_code

load_dotenv()
st.set_page_config(page_title="CSV Analysis Agent", page_icon="📊", layout="wide")
st.title("📊 Natural Language to Data Visualization Agent")
st.caption("Upload a CSV, ask a question, and generate, validate, and run a visualization.")

uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
question = st.text_area("What would you like to analyze?", placeholder="Example: Show monthly sales trends and identify the best month.")
chart_lib = st.selectbox("Visualization library", ["matplotlib", "seaborn", "plotly"])

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        st.subheader("Dataset preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.write(f"Rows: **{len(df):,}** · Columns: **{len(df.columns)}**")
        schema = [{"column": str(c), "dtype": str(df[c].dtype), "nulls": int(df[c].isna().sum())} for c in df.columns]
        with st.expander("Column details"):
            st.json(schema)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    if st.button("Generate and run analysis", type="primary", disabled=not question.strip()):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Set OPENAI_API_KEY in your .env file first.")
            st.stop()

        with st.spinner("Generating analysis plan and Python code..."):
            try:
                result = run_analysis(
                    question=question.strip(),
                    csv_text=df.head(100).to_csv(index=False),
                    columns=[{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns],
                    library=chart_lib,
                )
            except Exception as e:
                st.error(f"Agent workflow failed: {e}")
                st.stop()

        code = result.get("code", "")
        st.subheader("Generated Python code")
        st.code(code, language="python")

        try:
            validate_generated_code(code, allowed_columns=[str(c) for c in df.columns])
        except ValueError as e:
            st.error(f"Code validation failed: {e}")
            st.info("Try rephrasing the question or choosing a simpler analysis.")
            st.stop()

        # The generated script receives a local temporary CSV path. It runs with a timeout.
        # For production, use a dedicated isolated container/VM with network disabled.
        with tempfile.TemporaryDirectory(prefix="csv_agent_") as td:
            temp_dir = Path(td)
            csv_path = temp_dir / "input.csv"
            script_path = temp_dir / "analysis.py"
            df.to_csv(csv_path, index=False)
            script_path.write_text(code, encoding="utf-8")
            env = os.environ.copy()
            env["CSV_FILE"] = str(csv_path)
            env["OUTPUT_DIR"] = str(temp_dir)
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(script_path)],
                    cwd=str(temp_dir),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if proc.returncode != 0:
                    st.error("Generated code failed during execution.")
                    st.code((proc.stderr or proc.stdout)[-5000:])
                    st.caption("This starter app reports execution errors but does not automatically retry them.")
                else:
                    # Plot scripts save figures to output.png or output.html.
                    png = temp_dir / "output.png"
                    html = temp_dir / "output.html"
                    if png.exists():
                        st.subheader("Analysis graph")
                        st.image(str(png), use_container_width=True)
                    elif html.exists():
                        st.subheader("Interactive analysis graph")
                        st.components.v1.html(html.read_text(encoding="utf-8"), height=600, scrolling=True)
                    else:
                        st.warning("Code ran, but no output.png or output.html was created.")
                    if proc.stdout.strip():
                        st.subheader("Computed results")
                        st.code(proc.stdout)
                    st.success("Execution completed.")
            except subprocess.TimeoutExpired:
                st.error("Execution stopped: exceeded the 15-second time limit.")
            except Exception as e:
                st.error(f"Execution error: {e}")

        with st.expander("Workflow result"):
            st.json({k: v for k, v in result.items() if k != "code"})
else:
    st.info("Upload a CSV to preview its columns and begin.")
