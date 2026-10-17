"""Require actual healthy status for every application service, not just ps exit 0."""

import json
import subprocess

response = subprocess.run(
    ["docker", "compose", "ps", "--format", "json"], text=True, capture_output=True, check=True
)
text = response.stdout.strip()
containers = (
    json.loads(text)
    if text.startswith("[")
    else [json.loads(line) for line in text.splitlines() if line.strip()]
)
expected = {"neo4j", "api", "web", "ollama"}
actual = {c["Service"] for c in containers}
assert expected <= actual, f"Missing containers: {expected-actual}"
for container in containers:
    assert container["State"] == "running", f'{container["Service"]}: {container["State"]}'
    assert (
        container.get("Health") == "healthy"
    ), f'{container["Service"]}: {container.get("Health")}'
print(
    json.dumps(
        [{"service": c["Service"], "state": c["State"], "health": c["Health"]} for c in containers],
        indent=2,
    )
)
