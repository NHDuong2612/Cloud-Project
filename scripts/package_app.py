"""Package trusted app code into a content-addressed deployment artifact."""

import argparse
from hashlib import sha256
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=["crud"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / "build" / f"{args.app}.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / "apps" / args.app).iterdir()):
            if path.is_file():
                info = zipfile.ZipInfo(path.name, (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    print(f"apps/{args.app}/{sha256(target.read_bytes()).hexdigest()}.zip")


if __name__ == "__main__":
    main()
