from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
from typing import Iterator, TextIO


def _fsync_parent(path: Path) -> None:
    if os.name != "posix":
        return
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        fd = os.open(str(path), flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
        _fsync_parent(path.parent)
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _lock(handle: TextIO) -> str:
    if os.name == "posix":
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return "POSIX_FLOCK"
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return "WINDOWS_MSVCRT"
    return "UNAVAILABLE"


def _unlock(handle: TextIO, capability: str) -> None:
    if capability == "POSIX_FLOCK":
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    elif capability == "WINDOWS_MSVCRT":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


@contextmanager
def locked_text_file(path: Path) -> Iterator[tuple[TextIO, str]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r+", encoding="utf-8", newline="\n") as handle:
        capability = _lock(handle)
        try:
            yield handle, capability
        finally:
            _unlock(handle, capability)


def append_durable_line(handle: TextIO, line: str) -> None:
    if "\n" in line or "\r" in line:
        raise ValueError("durable append accepts exactly one logical line")
    handle.seek(0, os.SEEK_END)
    handle.write(line + "\n")
    handle.flush()
    os.fsync(handle.fileno())
