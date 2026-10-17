"""Produce an immutable Lambda archive. Boto3 is supplied by the Lambda runtime."""

from hashlib import sha256
from pathlib import Path
import sys
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / "build" / "worker.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / "src" / "cloudhub").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".json"}:
                info = zipfile.ZipInfo(path.relative_to(root / "src").as_posix(), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    print(f"worker/{sha256(target.read_bytes()).hexdigest()}.zip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
