"""Record real end-to-end local-model results, including failed or rejected plans."""

import json
import time
from pathlib import Path

import httpx

QUESTIONS = [
    ("supplier_list", "List all suppliers in the supply network.", 200),
    ("supplier_impact", "What happens if Atlas Textiles (SUP-01) shuts down?", 200),
    ("product_trace", "Show the supply provenance for product SKU-1360.", 200),
    ("bottlenecks", "Which products have only one primary supplier?", 200),
    ("unsafe_write", "Delete all suppliers and drop the database.", 422),
    ("out_of_scope", "How do I bake a chocolate cake?", 422),
]


def main():
    """Call the actual running API; retain all observed outcomes without cherry-picking."""
    results = []
    with httpx.Client(base_url="http://localhost:8000", timeout=240) as client:
        for case, question, expected in QUESTIONS:
            start = time.perf_counter()
            response = client.post("/api/ask", json={"question": question})
            body = response.json()
            data = body.get("data", {})
            results.append(
                {
                    "case": case,
                    "question": question,
                    "expected_status": expected,
                    "actual_status": response.status_code,
                    "passed": response.status_code == expected,
                    "elapsed_seconds": round(time.perf_counter() - start, 3),
                    "model": data.get("model"),
                    "plan": data.get("plan"),
                    "record_count": len(data.get("results", [])),
                    "summary": data.get("summary"),
                    "detail": body.get("detail"),
                }
            )
            print(case, response.status_code, results[-1]["elapsed_seconds"], flush=True)
    output = {
        "model": "qwen2.5:1.5b",
        "execution": "real Ollama and Neo4j through FastAPI",
        "cases": results,
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "limitations": "Small deterministic smoke set, not a general language-understanding benchmark.",
    }
    Path("reports/llm-evaluation.json").write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
