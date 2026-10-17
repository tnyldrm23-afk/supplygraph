"""Download the original openly licensed DataCo files with SHA verification."""

import hashlib
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "DataCoSupplyChainDataset.csv": (
        "72784be5-36d3-44fe-b75d-0edbf1999f65",
        "fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6",
    ),
    "DescriptionDataCoSupplyChain.csv": (
        "29dc7b05-dda6-4834-8354-5b5cc44430df",
        "9828e34669bd6d77e3b4463364cc44a5d52446b5e246fc258758cfe592566c4b",
    ),
}


def main():
    """Fetch only missing files; never silently accept changed source content."""
    directory = ROOT / "data/raw"
    directory.mkdir(parents=True, exist_ok=True)
    for name, (file_id, digest) in FILES.items():
        path = directory / name
        if not path.exists():
            url = f"https://data.mendeley.com/public-files/datasets/8gx2fvg2k6/files/{file_id}/file_downloaded"
            with urlopen(url, timeout=180) as response:
                path.write_bytes(response.read())
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"SHA-256 mismatch: {name}")
        print(f"Verified {name}")


if __name__ == "__main__":
    main()
