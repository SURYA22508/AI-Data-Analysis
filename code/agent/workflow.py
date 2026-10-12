import json, os
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
import ast

class AnalysisState(TypedDict, total=False):
    question: str
    csv_text: str
    columns: list
    library: str
    code: str
    plan: str
    checks: list
    error: str

SYSTEM_PROMPT = """
You generate a single Python script to analyze a user-provided CSV.
Return ONLY valid JSON with keys: plan, code, checks.
Requirements:
- Use pandas plus the requested visualization library.
- Read the CSV using: df = pd.read_csv("input.csv")
- Do not import os or other system modules.
- Save the chart as output.png or output.html.
- Read the full dataset with: df = pd.read_csv(os.environ["CSV_FILE"])
- Use only columns provided in the schema. Do not assume other columns exist.
- Handle missing values and suitable data types where relevant.
- The script must save exactly one main visualization:
  * matplotlib/seaborn: plt.savefig("output.png", bbox_inches="tight", dpi=140)
  * plotly: fig.write_html("output.html", include_plotlyjs="cdn")
- For matplotlib/seaborn, import matplotlib.pyplot as plt and call plt.tight_layout().
- Print concise numerical findings that directly answer the question.
- Do not use network, filesystem access beyond the input CSV and output graph,
  subprocesses, shell commands, dynamic imports, eval, exec, or function definitions.
- Keep code under 100 lines. No markdown fences.
"""

def _generate(state: AnalysisState) -> dict:
    llm = ChatGroq(model="qwen/qwen3.8-27b",api_key="your key", temperature=0)
    prompt = f"""{SYSTEM_PROMPT}
Question: {state['question']}
Requested library: {state['library']}
CSV columns and types: {json.dumps(state['columns'])}
Sample rows (CSV, first 100 rows):
{state['csv_text']}

Remember: return JSON only."""
    response = llm.invoke(prompt)
    raw = response.content if isinstance(response.content, str) else str(response.content)
    raw = raw.strip()
    print("generate:",raw)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    code = data.get("code", "")


    # Add required imports for env access if the model omitted them.
    return {"plan": data.get("plan", ""), "code": code, "checks": data.get("checks", [])}


def _verify(state: AnalysisState) -> dict:
    code = state.get("code", "")
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"Invalid Python syntax: {e}"}

    # Check whether the script loads a CSV
    reads_csv = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_csv"
        for node in ast.walk(tree)
    )

    if not reads_csv:
        issues.append("Script must load the uploaded CSV using pandas.")

    if state["library"] == "plotly":
        if "write_html" not in code or "output.html" not in code:
            issues.append("Plotly script must save output.html.")
    else:
        if "savefig" not in code or "output.png" not in code:
            issues.append("Matplotlib/Seaborn script must save output.png.")

    return {"error": "; ".join(issues)}
def build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("generate", _generate)
    graph.add_node("verify", _verify)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "verify")
    graph.add_edge("verify", END)
    return graph.compile()

_app = None
def run_analysis(question, csv_text, columns, library):
    global _app
    if _app is None:
        _app = build_graph()
    result = _app.invoke({
        "question": question,
        "csv_text": csv_text,
        "columns": columns,
        "library": library,
    })
    if result.get("error"):
        raise ValueError(result["error"])
    return result
