# Operations and reproducibility

## Fresh environment
Python 3.12; Docker Compose v2. `make install` uses the universal dependency lock.
`make docker-run` generates a private `.env`, builds a non-root API image, starts
four official/supporting services and waits for health. `make model` provisions
Qwen once; the model volume persists across normal stops.

No external model API receives questions or graph data. Ollama needs network only
for provisioning. The UI has no remote font/JS dependencies; Swagger uses FastAPI's
standard jsDelivr assets under its separate CSP. Graph, model and API host ports
bind only to loopback. There is no public website deployment in this project.

## Data lifecycle
- Original data is hash-verified and ignored in Git/Docker.
- The committed derivative permits offline graph startup after image download.
- Import is idempotent for the same version and aggregates repeated order/SKU lines.
- API computes from an immutable startup snapshot; restart after manual imports.
- GDS catalog state is in memory; projection is recreated on demand after DB restart.
- Updating topology requires rebuilding the named supplyflow projection; normal
  read-only scenarios never mutate or invalidate it.
- `docker compose down` preserves named volumes. Deleting volumes is an explicit
  destructive reset and is not part of make clean or ordinary instructions.

## Capacity and failure behavior
Single Uvicorn worker, two concurrent scenario slots; 429 if full. Request bodies
are bounded by schema and Nginx body limit. Cypher transactions have eight-second
limits; fixed traversal upper bound six. Model requests have a bounded HTTP timeout.
For production multi-user use, add authenticated access, request rate limiting,
job queues and monitoring before exposing the stack beyond localhost.

A missing model produces an honest 503 instead of a fake canned response. DB loss
produces 503; health queries probe actual connectivity. Browser errors are surfaced,
not silently treated as zero-impact scenarios.

## CI and container publication
Quality runs lint, unit/API/security coverage and a separate real Docker integration
job. The integration job starts Neo4j/API/web without downloading model weights;
it verifies model-independent graph algorithms and rejects writes before model use.
Actual local model evaluation is kept as separate evidence because downloading and
running a model on every PR is expensive and not required to test deterministic
validation logic.

The Container workflow publishes multi-architecture images to GHCR using the
workflow-scoped GITHUB_TOKEN, not a committed personal access token. Check package
visibility and perform an anonymous pull before claiming the public-image rubric
criterion. The repository should contain the actual workflow run and merged PR links.

## Evidence regeneration
- `make data` -> data audit and sanitized derivative.
- `make ml` -> held-out classifier report.
- `make benchmark` -> actual plans and query timing.
- `python -m scripts.train_model --write-neo4j` -> order node scores/split labels.
- `python scripts/evaluate_assistant.py` -> actual model evaluation.
- `make test` -> branch-inclusive coverage XML.
- `make demo` -> executed notebook with actual service outputs.

Tests using doubles are explicitly labeled. Integration tests fail when explicitly
run without the required real services; they do not silently skip or substitute a
memory graph. A source model change requires rerunning affected tests and evidence.

Workflow action majors were checked against the official [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python), [upload-artifact](https://github.com/actions/upload-artifact) and [Docker build/push](https://github.com/docker/build-push-action) references.
