import logging
import subprocess

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def linter_tool(file_path: str = "") -> str:
    """Run the `ruff` linter on project files. Pass an optional file path (relative to the project folder) to lint a single file; omit it to lint the entire project."""
    logger.info(f"Tool_Invoked,'linter_tool','{file_path}'")

    # Import here so we get the latest PROJECT_FOLDER value at call time
    from .files import get_project_folder

    proj = get_project_folder()
    if not proj:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    target = file_path.strip() if file_path else proj

    try:
        result = subprocess.run(
            ["ruff", "check", target],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=proj,
        )

        output_lines = [f"Ruff check on '{target}':"]
        if result.stdout.strip():
            output_lines.append(result.stdout.strip())
        if result.stderr.strip():
            output_lines.append(result.stderr.strip())

        rc_label = "PASS" if result.returncode == 0 else "FAIL"
        output_lines.append(f"[{rc_label}] (exit code {result.returncode})")
        return "\n".join(output_lines)

    except FileNotFoundError:
        return "Error: ruff is not installed or not on PATH. Install with `pip install ruff`."
    except subprocess.TimeoutExpired:
        return "Error: ruff check timed out after 120 seconds."
    except Exception as exc:
        return f"Error running ruff: {exc}"
