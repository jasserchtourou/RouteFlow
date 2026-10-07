import subprocess
import sys


def test_app_starts_in_a_fresh_process() -> None:
    """The test-suite imports every model module (factories, seed), which can hide missing
    imports in the real app. A fresh interpreter sees exactly what `uvicorn app.main:app` sees."""
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
