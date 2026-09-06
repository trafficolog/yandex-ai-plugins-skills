from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any

try:
    from .seo_weekly_model import canonical_json_bytes
except ImportError:
    from seo_weekly_model import canonical_json_bytes


MANIFEST_SCHEMA = "yandex-ai-artifact-manifest/v1"
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("created_at must be a non-empty timestamp")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be RFC3339/ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return text


def _validate_segment(value: str, field: str) -> str:
    if not isinstance(value, str) or not SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{field} contains an unsafe path segment")
    if value in {".", ".."} or "\x00" in value:
        raise ValueError(f"{field} contains an unsafe path segment")
    return value


def _validate_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("artifact path must be a non-empty POSIX relative path")
    if value == "manifest.json":
        raise ValueError("manifest.json is managed separately")
    if value.startswith("/") or value.endswith("/") or "//" in value:
        raise ValueError("artifact path must be relative and normalized")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ValueError("artifact path cannot contain traversal segments")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value:
        raise ValueError("artifact path must be normalized POSIX relative path")
    return value


def artifact_directory(output_root: Path, project_slug: str, period_end: str, report_id: str) -> Path:
    project = _validate_segment(project_slug, "project_slug")
    report = _validate_segment(report_id, "report_id")
    try:
        datetime.strptime(period_end, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise ValueError("period_end must use YYYY-MM-DD") from exc
    return Path(output_root) / project / period_end / f"weekly-organic-{report}"


def _file_metadata(path: str, content: bytes) -> dict[str, Any]:
    if path == "report.json":
        try:
            parsed = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("report.json must be valid UTF-8 JSON") from exc
        schema = parsed.get("schema") if isinstance(parsed, dict) else None
        if not isinstance(schema, str) or not schema:
            raise ValueError("report.json must declare schema")
        return {
            "path": path,
            "role": "PRIMARY_JSON",
            "media_type": "application/json",
            "sha256": hashlib.sha256(content).hexdigest(),
            "schema": schema,
        }
    if path == "report.html":
        return {
            "path": path,
            "role": "HTML_REPORT",
            "media_type": "text/html; charset=utf-8",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    if path.endswith(".mmd"):
        return {
            "path": path,
            "role": "MERMAID",
            "media_type": "text/plain; charset=utf-8",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    if path.endswith(".dot"):
        return {
            "path": path,
            "role": "DOT",
            "media_type": "text/vnd.graphviz; charset=utf-8",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    raise ValueError(f"unsupported managed artifact type: {path}")


def build_manifest(files: dict[str, bytes], *, report_bytes: bytes, created_at: str) -> dict[str, Any]:
    if not isinstance(files, dict) or "report.json" not in files:
        raise ValueError("artifact set must include report.json")
    if files["report.json"] != report_bytes:
        raise ValueError("report_bytes must equal files['report.json']")
    created = _validate_timestamp(created_at)
    items: list[dict[str, Any]] = []
    for raw_path in sorted(files):
        path = _validate_relative_path(raw_path)
        content = files[raw_path]
        if not isinstance(content, bytes):
            raise ValueError(f"artifact {path} content must be bytes")
        items.append(_file_metadata(path, content))
    return {
        "schema": MANIFEST_SCHEMA,
        "artifact_set_id": hashlib.sha256(report_bytes).hexdigest(),
        "created_at": created,
        "primary_artifact": "report.json",
        "files": items,
    }


def _expected_bytes(files: dict[str, bytes], manifest: dict[str, Any]) -> dict[str, bytes]:
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported artifact manifest schema")
    expected_manifest = build_manifest(
        files,
        report_bytes=files.get("report.json", b""),
        created_at=manifest.get("created_at"),
    )
    if manifest != expected_manifest:
        raise ValueError("artifact manifest does not match managed files")
    expected = dict(files)
    expected["manifest.json"] = canonical_json_bytes(manifest) + b"\n"
    return expected


def _verify_existing(destination: Path, expected: dict[str, bytes]) -> None:
    actual_paths = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    if actual_paths != set(expected):
        raise ValueError("existing artifact snapshot has unexpected or missing files")
    for relative, content in expected.items():
        if (destination / PurePosixPath(relative)).read_bytes() != content:
            raise ValueError(f"existing artifact snapshot conflicts at {relative}")


def publish_artifact_set(destination: Path, relative_files: dict[str, bytes], manifest: dict[str, Any]) -> Path:
    destination = Path(destination)
    expected = _expected_bytes(relative_files, manifest)
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    lock_path = parent / f".{destination.name}.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("artifact destination is locked by another writer") from exc
    temp_path: Path | None = None
    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            os.fsync(lock_file.fileno())
        if destination.exists():
            if not destination.is_dir():
                raise ValueError("artifact destination exists and is not a directory")
            _verify_existing(destination, expected)
            return destination
        temp_path = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=str(parent)))
        for relative, content in expected.items():
            target = temp_path / PurePosixPath(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        if destination.exists():
            raise ValueError("artifact destination appeared during publication")
        os.rename(temp_path, destination)
        temp_path = None
        return destination
    finally:
        if temp_path is not None and temp_path.exists():
            shutil.rmtree(temp_path)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
