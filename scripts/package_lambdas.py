#!/usr/bin/env python
"""Build and deploy the GridSense Lambda package.

Terraform provisions the functions with a placeholder stub and ignores code
changes; this script owns code delivery.

Dependencies are installed with pip's --platform flag so manylinux wheels
are fetched rather than whatever matches the build machine -- otherwise a
Windows build produces a package that fails at import time in Lambda.

Usage:
    python scripts/package_lambdas.py --dry-run
    python scripts/package_lambdas.py
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

import boto3

REGION = "ap-south-1"
PREFIX = "gridsense-energy-dev-"
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# boto3 ships in the Lambda runtime; only what is missing needs vendoring.
DEPENDENCIES = ["structlog"]


def build(staging: pathlib.Path) -> bytes:
    src_dest = staging / "src"
    shutil.copytree(REPO_ROOT / "src", src_dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    if DEPENDENCIES:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--quiet",
                "--target", str(staging),
                "--platform", "manylinux2014_x86_64",
                "--implementation", "cp",
                "--python-version", "3.12",
                "--only-binary=:all:",
                *DEPENDENCIES,
            ],
            check=True,
        )

    buf = pathlib.Path(tempfile.gettempdir()) / "gridsense-energy-lambda.zip"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(staging.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                z.write(path, path.relative_to(staging).as_posix())
    return buf.read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        payload = build(pathlib.Path(tmp))
    print("package: %.2f MB" % (len(payload) / 1e6))

    if args.dry_run:
        out = pathlib.Path(tempfile.gettempdir()) / "gridsense-energy-lambda.zip"
        print("dry-run: %s" % out)
        return 0

    client = boto3.client("lambda", region_name=REGION)
    names = sorted(
        f["FunctionName"]
        for page in client.get_paginator("list_functions").paginate()
        for f in page["Functions"]
        if f["FunctionName"].startswith(PREFIX)
    )
    if not names:
        print("no functions found with prefix %r" % PREFIX, file=sys.stderr)
        return 1

    for name in names:
        client.update_function_code(FunctionName=name, ZipFile=payload, Publish=False)
        print("  deployed -> %s" % name)
    print("done: %d function(s)" % len(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
