#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


PATCH_MAP = {
    "main.nf": "modules/local/dorado/basecaller/main.nf",
    "nextflow.config": "nextflow.config",
}


PLACEHOLDER = "__METHYLONG_IMAGE_DIR__"


def main():
    parser = argparse.ArgumentParser(
        description="Apply ModFlowAgent methylong compatibility patches."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Path to the methylong source directory.",
    )
    parser.add_argument(
        "--cache-dir",
        help="Singularity image/cache directory used by patched methylong config.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create .modflowagent.bak backups.",
    )

    args = parser.parse_args()

    patch_dir = Path(__file__).resolve().parent
    base_dir = Path(args.base).resolve()

    if not base_dir.exists():
        raise FileNotFoundError(f"Methylong base directory not found: {base_dir}")

    if not base_dir.is_dir():
        raise NotADirectoryError(f"Methylong base path is not a directory: {base_dir}")

    for src_name, dst_rel in PATCH_MAP.items():
        src = patch_dir / src_name
        dst = base_dir / dst_rel

        if not src.exists():
            raise FileNotFoundError(f"Patch source file not found: {src}")

        if not dst.exists():
            raise FileNotFoundError(f"Target file not found: {dst}")

        if not args.no_backup:
            backup = dst.with_suffix(dst.suffix + ".modflowagent.bak")
            shutil.copy2(dst, backup)
            print(f"[BACKUP] {dst} -> {backup}")

        content = src.read_text(encoding="utf-8")

        if args.cache_dir:
            cache_dir = str(Path(args.cache_dir).expanduser().resolve())
            if PLACEHOLDER in content:
                content = content.replace(PLACEHOLDER, cache_dir)
                print(f"[UPDATE] {src_name}: {PLACEHOLDER} -> {cache_dir}")
            else:
                print(f"[WARN] {src_name}: placeholder not found: {PLACEHOLDER}")

        dst.write_text(content, encoding="utf-8")
        print(f"[PATCH] {src} -> {dst}")

    print("[OK] Methylong compatibility patches applied.")


if __name__ == "__main__":
    main()