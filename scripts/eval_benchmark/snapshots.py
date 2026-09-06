from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from .artifacts import verify_benchmark_artifact_directory


def _verify_exact_snapshot(destination: Path, expected: dict[str, bytes]) -> None:
    if not destination.is_dir():
        raise ValueError("snapshot destination exists and is not a directory")
    actual = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    if actual != set(expected):
        raise ValueError("existing snapshot has unexpected or missing files; exact replay required")
    for relative, content in expected.items():
        if (destination / PurePosixPath(relative)).read_bytes() != content:
            raise ValueError(f"existing snapshot conflicts at {relative}; exact replay required")


def materialize_snapshot(source_artifact_dir: Path, repository_root: Path) -> Path:
    result, expected = verify_benchmark_artifact_directory(Path(source_artifact_dir))
    benchmark_id = result.get("benchmark_id")
    if not isinstance(benchmark_id, str):
        raise ValueError("verified benchmark result is missing benchmark_id")

    snapshot_root = Path(repository_root) / "evals/results/v1"
    destination = snapshot_root / benchmark_id
    snapshot_root.mkdir(parents=True, exist_ok=True)
    lock_path = snapshot_root / f".{benchmark_id}.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("snapshot destination is locked by another writer") from exc

    temp_path: Path | None = None
    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            _verify_exact_snapshot(destination, expected)
            return destination
        temp_path = Path(tempfile.mkdtemp(prefix=f".{benchmark_id}.", dir=str(snapshot_root)))
        for relative, content in expected.items():
            target = temp_path / PurePosixPath(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        if destination.exists():
            raise ValueError("snapshot destination appeared during materialization")
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
