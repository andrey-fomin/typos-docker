#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UPSTREAM_REPO = "crate-ci/typos"
UPSTREAM_API = f"https://api.github.com/repos/{UPSTREAM_REPO}"
ARCH_TO_TARGET = {
    "amd64": "x86_64-unknown-linux-musl",
    "arm64": "aarch64-unknown-linux-musl",
}


def fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def github_get(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "andreyfomin-typos-docker",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            fail(f"GitHub release not found: {url}")
        details = exc.read().decode("utf-8", errors="replace").strip()
        fail(f"GitHub API request failed ({exc.code}): {details or exc.reason}")


def normalize_version(version: str | None) -> str | None:
    if version is None:
        return None
    version = version.strip()
    if not version:
        return None
    return version if version.startswith("v") else f"v{version}"


def release_url_for(version: str | None) -> str:
    if version is None:
        return f"{UPSTREAM_API}/releases/latest"
    quoted = urllib.parse.quote(version, safe="")
    return f"{UPSTREAM_API}/releases/tags/{quoted}"


def get_release(version: str | None) -> dict:
    release = github_get(release_url_for(normalize_version(version)))
    if release.get("draft"):
        fail("Draft releases are not supported")
    if release.get("prerelease"):
        fail("Prereleases are not supported")
    return release


def strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def release_metadata(release: dict) -> dict:
    tag = release["tag_name"]
    version_no_v = strip_v(tag)
    parts = version_no_v.split(".")
    if len(parts) != 3:
        fail(f"Unsupported typos version format: {tag}")

    assets_by_name = {asset["name"]: asset for asset in release.get("assets", [])}
    assets = {}
    for arch, target in ARCH_TO_TARGET.items():
        asset_name = f"typos-{tag}-{target}.tar.gz"
        asset = assets_by_name.get(asset_name)
        if asset is None:
            fail(f"Missing expected release asset: {asset_name}")
        digest = asset.get("digest", "")
        if not digest.startswith("sha256:"):
            fail(f"Missing sha256 digest for asset: {asset_name}")
        assets[arch] = {
            "name": asset_name,
            "url": asset["browser_download_url"],
            "digest": digest.removeprefix("sha256:"),
            "target": target,
        }

    return {
        "version": tag,
        "version_no_v": version_no_v,
        "major": parts[0],
        "minor": parts[1],
        "patch": parts[2],
        "release_url": release["html_url"],
        "assets": assets,
    }


def resolve_metadata(version: str | None) -> dict:
    requested = normalize_version(version)
    selected = release_metadata(get_release(requested))
    latest = release_metadata(get_release(None))
    selected["floating_tags_enabled"] = str(
        selected["version"] == latest["version"]
    ).lower()
    return selected


def write_outputs(metadata: dict, output_path: Path) -> None:
    lines = [
        f"version={metadata['version']}",
        f"version_no_v={metadata['version_no_v']}",
        f"major={metadata['major']}",
        f"minor={metadata['minor']}",
        f"patch={metadata['patch']}",
        f"release_url={metadata['release_url']}",
        f"floating_tags_enabled={metadata['floating_tags_enabled']}",
    ]
    for arch, asset in metadata["assets"].items():
        lines.extend(
            [
                f"{arch}_asset_name={asset['name']}",
                f"{arch}_asset_url={asset['url']}",
                f"{arch}_asset_digest={asset['digest']}",
                f"{arch}_asset_target={asset['target']}",
            ]
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_metadata(args: argparse.Namespace) -> int:
    metadata = resolve_metadata(args.version)
    if args.github_output is not None:
        write_outputs(metadata, Path(args.github_output))
    json.dump(metadata, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def download_to_path(url: str, destination: Path) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "andreyfomin-typos-docker"},
    )
    digest = hashlib.sha256()
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            handle.write(chunk)
    return digest.hexdigest()


def extract_binary(archive_path: Path, output_dir: Path) -> None:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        member = next(
            (
                item
                for item in archive.getmembers()
                if item.isfile() and Path(item.name).name == "typos"
            ),
            None,
        )
        if member is None:
            fail("Downloaded release archive does not contain a typos binary")
        with archive.extractfile(member) as source:
            if source is None:
                fail("Failed to extract typos binary from release archive")
            destination = output_dir / "typos"
            with destination.open("wb") as handle:
                shutil.copyfileobj(source, handle)
            destination.chmod(0o755)


def cmd_fetch(args: argparse.Namespace) -> int:
    if args.arch not in ARCH_TO_TARGET:
        fail(f"Unsupported architecture: {args.arch}")

    metadata = release_metadata(get_release(args.version))
    asset = metadata["assets"][args.arch]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = Path(tmp_dir) / asset["name"]
        actual_digest = download_to_path(asset["url"], archive_path)
        if actual_digest != asset["digest"]:
            fail(
                "Downloaded asset digest mismatch: "
                f"expected {asset['digest']}, got {actual_digest}"
            )
        extract_binary(archive_path, output_dir)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve typos release metadata")
    subparsers = parser.add_subparsers(dest="command", required=True)

    metadata_parser = subparsers.add_parser(
        "metadata",
        help="Print stable release metadata for typos",
    )
    metadata_parser.add_argument(
        "--version",
        help="Upstream typos version tag, with or without a leading v",
    )
    metadata_parser.add_argument(
        "--github-output",
        help="Write workflow outputs to this file",
    )
    metadata_parser.set_defaults(func=cmd_metadata)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Download and verify a typos release asset for one architecture",
    )
    fetch_parser.add_argument(
        "--version",
        required=True,
        help="Upstream typos version tag, with or without a leading v",
    )
    fetch_parser.add_argument(
        "--arch",
        required=True,
        choices=sorted(ARCH_TO_TARGET),
        help="Container architecture to resolve",
    )
    fetch_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory that will receive the typos binary",
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
