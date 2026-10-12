import ast

# This is a basic guardrail, NOT a secure sandbox. Run untrusted generated code
# in an isolated container/VM for real deployments.
FORBIDDEN_NAMES = {
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "globals", "locals", "vars", "getattr", "setattr",
    "delattr", "help"
}
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "requests", "urllib",
    "shutil", "pathlib", "importlib", "pickle"
}
ALLOWED_IMPORTS = {"pandas", "numpy", "matplotlib", "seaborn", "plotly"}

def validate_generated_code(code: str, allowed_columns=None):
    if not code or len(code) > 20_000:
        raise ValueError("Generated code is empty or too large.")
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python syntax: {e}") from e

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            raise ValueError("Function/class definitions are not allowed in generated code.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_NAMES:
                raise ValueError(f"Disallowed function call: {node.func.id}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Dunder names are not allowed.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Dunder attribute access is not allowed.")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0] if node.module else ""]
            for name in names:
                if name in FORBIDDEN_MODULES or name not in ALLOWED_IMPORTS:
                    raise ValueError(f"Import is not allowed: {name}")
    # Require use of the provided CSV path and a saved graph.
    if "input.csv" not in code or ("output.png" not in code and "output.html" not in code):
        raise ValueError("Code must read CSV_FILE and save output.png or output.html.")
    return True
