"""Create local configuration without printing or committing credentials."""

from pathlib import Path
import secrets

path = Path(".env")
if not path.exists():
    template = Path(".env.example").read_text()
    path.write_text(
        template.replace("replace-with-a-long-random-local-password", secrets.token_urlsafe(30))
    )
    path.chmod(0o600)
    print("Created private .env with a unique random password.")
else:
    print("Using existing .env.")
