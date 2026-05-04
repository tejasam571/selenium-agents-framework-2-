"""
tools/runner.py
"""
import subprocess
from pathlib import Path
from google.adk.tools import FunctionTool

JAVA_TESTS_DIR = Path("java_tests")

def run_maven_tests() -> str:
    result = subprocess.run(
        ["mvn", "clean", "test"],
        cwd=JAVA_TESTS_DIR,
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr
    return output

run_maven_tool = FunctionTool(func=run_maven_tests)