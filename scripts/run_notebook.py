"""Execute demo.ipynb using this project's actual Python interpreter and services."""

import os
from pathlib import Path
import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(root / ".cache/matplotlib")
notebook = nbformat.read(root / "demo.ipynb", as_version=4)
client = NotebookClient(
    notebook, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(root)}}
)
client.execute()
nbformat.write(notebook, root / "demo.ipynb")
print("All demonstration cells executed successfully.")
