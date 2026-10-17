"""Remove only disposable Python caches within this repository."""

from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
for path in root.rglob("__pycache__"):
    if ".venv" not in path.parts:
        shutil.rmtree(path)
for name in (".pytest_cache", ".coverage"):
    path = root / name
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
print("Project caches cleaned; source, data and runtime volumes preserved.")
