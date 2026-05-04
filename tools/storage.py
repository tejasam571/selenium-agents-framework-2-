"""
tools/storage.py
"""
from pathlib import Path
from google.adk.tools import FunctionTool


def save_java_test(test_id: str, java_code: str) -> str:
    """Save generated Java Selenium test."""
    safe_id = test_id.replace(" ", "_").replace("-", "_")
    filename = f"{safe_id}.java" if safe_id.startswith("Test_") else f"Test_{safe_id}.java"
    out = Path("java_tests/src/test/java/tests") / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(java_code, encoding="utf-8")
    print(f"[Storage] Saved {out}")
    return str(out)


save_java_test_tool = FunctionTool(func=save_java_test)