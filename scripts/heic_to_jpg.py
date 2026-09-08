#!/usr/bin/env python3
"""Convert HEIC/HEIF images to JPEG.

On macOS uses `sips` (no extra packages). Elsewhere uses pillow-heif:
    pip install pillow pillow-heif
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HEIC_SUFFIXES = {".heic", ".heif", ".hec"}


def collect(paths: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in HEIC_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            files.extend(
                item
                for item in iterator
                if item.is_file() and item.suffix.lower() in HEIC_SUFFIXES
            )
        elif not path.exists():
            raise FileNotFoundError(path)
    return sorted(set(files))


def out_path(source: Path, output_dir: Path | None) -> Path:
    target_dir = output_dir or source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{source.stem}.jpg"


def convert_with_sips(source: Path, dest: Path, quality: int) -> None:
    # sips --setProperty formatOptions is 0-100, same idea as JPEG quality.
    subprocess.run(
        [
            "sips",
            "-s",
            "format",
            "jpeg",
            "-s",
            "formatOptions",
            str(quality),
            str(source),
            "--out",
            str(dest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def convert_with_pillow(source: Path, dest: Path, quality: int) -> None:
    from PIL import Image
    from pillow_heif import register_heif_opener

    register_heif_opener()
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        rgb.save(dest, format="JPEG", quality=quality, optimize=True)


def convert(source: Path, dest: Path, quality: int, use_sips: bool) -> None:
    if dest.exists() and dest.samefile(source):
        raise ValueError(f"Refusing to overwrite source: {source}")
    if use_sips:
        convert_with_sips(source, dest, quality)
        return
    convert_with_pillow(source, dest, quality)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert HEIC/HEIF images to JPG")
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories")
    parser.add_argument("-o", "--output-dir", type=Path, help="Write JPEGs here (default: next to each source)")
    parser.add_argument("-q", "--quality", type=int, default=90, help="JPEG quality 1-100 (default: 90)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directories recursively")
    parser.add_argument("--force", action="store_true", help="Overwrite existing JPGs")
    args = parser.parse_args()

    if not 1 <= args.quality <= 100:
        parser.error("quality must be between 1 and 100")

    use_sips = shutil.which("sips") is not None
    if not use_sips:
        try:
            import pillow_heif  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            print("Install pillow-heif (pip install pillow pillow-heif) or run this on macOS with sips.", file=sys.stderr)
            return 1

    try:
        sources = collect(args.paths, args.recursive)
    except FileNotFoundError as exc:
        print(f"Not found: {exc}", file=sys.stderr)
        return 1

    if not sources:
        print("No HEIC/HEIF files found.", file=sys.stderr)
        return 1

    converted = 0
    for source in sources:
        dest = out_path(source, args.output_dir)
        if dest.exists() and not args.force:
            print(f"skip  {dest} (exists, use --force)")
            continue
        try:
            convert(source, dest, args.quality, use_sips)
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or exc.stdout or str(exc)).strip()
            print(f"fail  {source}: {err}", file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"fail  {source}: {exc}", file=sys.stderr)
            continue
        print(f"ok    {source} -> {dest}")
        converted += 1

    print(f"Converted {converted}/{len(sources)}")
    return 0 if converted else 1


if __name__ == "__main__":
    raise SystemExit(main())
