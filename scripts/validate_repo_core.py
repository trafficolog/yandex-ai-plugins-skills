#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

try:
    from .bilingual_docs import validate_bilingual_docs
    from .contract_controls import (
        MAX_REFERENCE_AGE_DAYS,
        parse_verified_date,
        validate_contract_matrix,
        validate_reference_freshness,
    )
except ImportError:
    from bilingual_docs import validate_bilingual_docs
    from contract_controls import (
        MAX_REFERENCE_AGE_DAYS,
        parse_verified_date,
        validate_contract_matrix,
        validate_reference_freshness,
    )

FORBIDDEN_RUNTIME_PATHS = (
    "~/.openclaw/",
    "~/.claude/",
    "~/.codex/",
    "~/.agents/",
    "$HOME/",
    "${HOME}/",
)
ALLOWED_EVAL_WRITE = {"preview-first", "approval-required"}
ALLOWED_EVAL_OUTCOMES = {"comply", "comply_with_limitations", "refuse"}
EVAL_TOKEN_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
EVAL_TOKEN_SCAN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.:-])([A-Za-z][A-Za-z0-9_.:-]*)(?![A-Za-z0-9_.:-])"
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".toml"}
CAPABILITY_HEADER = "| Capability | Read | Write | MCP/App | Bundled API | File fallback |"
CROSS_SERVICE_PLUGINS = {"yandex-seo", "yandex-marketing"}
SUPPORTED_AUTHENTICATION_POLICIES = {"ON_INSTALL", "ON_USE"}
MIN_SKILL_DESCRIPTION_CHARS = 32
MAX_SKILL_DESCRIPTION_CHARS = 500
MAX_SKILL_BYTES = 15 * 1024
WRITE_SKILL_SAFETY_MARKERS = (
    "approval-contract: exact-preview",
    "untrusted-data-policy: data-not-instructions",
)
SECRET_PATTERNS = (
    re.compile(r"Authorization\s*:\s*(?:Bearer|OAuth)\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE),
    re.compile(r"Api-Key\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE),
    re.compile(r"\bAQVN[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?<![A-Za-z0-9_-])y0_[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])"),
    re.compile(r"(?<![A-Za-z0-9_-])AQAA[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])"),
    re.compile(r"(?<![A-Za-z0-9_-])t1\.[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])"),
)
FORBIDDEN_TRANSPORT_ROOTS = {
    "http",
    "socket",
    "ssl",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "pycurl",
    "importlib",
    "subprocess",
}
YANDEX_API_ENDPOINT_PATTERN = re.compile(
    r"https://(?:[a-z0-9-]+\.)*yandex\.(?:com|net|ru)(?![a-z0-9.-])",
    re.IGNORECASE,
)


def _load_json(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing required JSON file: {path}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
    return None


def _frontmatter(text: str) -> dict[str, str] | None:
    normalized = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return None
    body = normalized[4:]
    delimiter = re.search(r"\n---(?:\n|$)", body)
    if delimiter is None:
        return None
    lines = body[:delimiter.start()].splitlines()
    result: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace() or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {">", "|"}:
            folded: list[str] = []
            index += 1
            while index < len(lines):
                continuation = lines[index]
                if continuation and not continuation[:1].isspace():
                    break
                if continuation.strip():
                    folded.append(continuation.strip())
                index += 1
            result[key] = " ".join(folded) if value == ">" else "\n".join(folded)
            continue
        result[key] = value.strip('"\'')
        index += 1
    return result


def _validate_skill(skill_path: Path, errors: list[str]) -> None:
    raw = skill_path.read_bytes()
    if len(raw) > MAX_SKILL_BYTES:
        errors.append(
            f"skill file exceeds size limit {MAX_SKILL_BYTES} bytes: {skill_path}"
        )
    text = raw.decode("utf-8")
    fm = _frontmatter(text)
    if fm is None:
        errors.append(f"skill frontmatter missing or malformed: {skill_path}")
        return
    name = fm.get("name", "")
    if not name:
        errors.append(f"skill frontmatter missing name: {skill_path}")
    elif name != skill_path.parent.name:
        errors.append(
            f"skill frontmatter name '{name}' must match directory '{skill_path.parent.name}': {skill_path}"
        )
    description = fm.get("description", "")
    if not description.startswith("Use when"):
        errors.append(f"skill description must start with 'Use when': {skill_path}")
    if not MIN_SKILL_DESCRIPTION_CHARS <= len(description) <= MAX_SKILL_DESCRIPTION_CHARS:
        errors.append(
            f"skill description length must be {MIN_SKILL_DESCRIPTION_CHARS}-{MAX_SKILL_DESCRIPTION_CHARS} characters: {skill_path}"
        )


def _validate_marketplace_skill_names(skill_files: list[Path], errors: list[str]) -> None:
    by_name: dict[str, list[Path]] = {}
    for skill_path in skill_files:
        try:
            text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _frontmatter(text)
        if fm is None:
            continue
        name = fm.get("name", "").strip()
        if not name:
            continue
        by_name.setdefault(name.casefold(), []).append(skill_path)
    for paths in by_name.values():
        if len(paths) > 1:
            errors.append(
                "duplicate skill name across marketplace: " + ", ".join(str(path) for path in paths)
            )


def _eval_plugin_vocabulary(plugin_path: Path) -> set[str]:
    """Collect plugin vocabulary without allowing evals/tests to self-validate exact tokens."""
    tokens: set[str] = set()
    eval_path = plugin_path / "evals/scenarios.json"
    for candidate in plugin_path.rglob("*"):
        if not candidate.is_file() or candidate == eval_path:
            continue
        relative = candidate.relative_to(plugin_path)
        if relative.parts and relative.parts[0] in {"evals", "tests"}:
            continue
        if candidate.name != ".env.example" and candidate.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        tokens.update(EVAL_TOKEN_SCAN_PATTERN.findall(text))
    return tokens


def _eval_token_registry(plugin_path: Path, errors: list[str]) -> set[str]:
    """Load the explicit per-plugin allowlist for exact eval tokens."""
    registry_path = plugin_path.parent.parent / "docs/EVAL_TOKEN_REGISTRY.json"
    data = _load_json(registry_path, errors)
    if not isinstance(data, dict):
        return set()
    if data.get("version") != 1:
        errors.append(f"eval exact-token registry must use version 1: {registry_path}")
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        errors.append(f"eval exact-token registry missing plugins object: {registry_path}")
        return set()
    values = plugins.get(plugin_path.name)
    if not isinstance(values, list):
        errors.append(
            f"eval exact-token registry missing list for plugin {plugin_path.name}: {registry_path}"
        )
        return set()

    valid: list[str] = []
    for token in values:
        if not isinstance(token, str) or not token.strip() or EVAL_TOKEN_PATTERN.fullmatch(token) is None:
            errors.append(
                f"eval exact-token registry contains invalid token for {plugin_path.name}: {token!r}"
            )
            continue
        valid.append(token)
    if len(valid) != len(set(valid)):
        errors.append(f"eval exact-token registry contains duplicate tokens for {plugin_path.name}")
    return set(valid)


def _valid_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _valid_eval_write(value: Any) -> bool:
    return value is False or (isinstance(value, str) and value in ALLOWED_EVAL_WRITE)


def _validate_evals(plugin_path: Path, errors: list[str]) -> None:
    path = plugin_path / "evals/scenarios.json"
    data = _load_json(path, errors)
    if not isinstance(data, dict):
        return
    scenarios = data.get("scenarios")
    if data.get("version") != 2:
        errors.append(f"eval schema must use version 2: {path}")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append(f"invalid evals/scenarios.json structure: {path}")
        return

    vocabulary = _eval_plugin_vocabulary(plugin_path)
    all_mentioned_tokens: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        expect = scenario.get("expect")
        if not isinstance(expect, dict):
            continue
        mentioned_tokens = expect.get("must_mention_tokens")
        if not isinstance(mentioned_tokens, list):
            continue
        all_mentioned_tokens.update(
            token
            for token in mentioned_tokens
            if isinstance(token, str) and token.strip()
        )
    registered_tokens = _eval_token_registry(plugin_path, errors) if all_mentioned_tokens else set()
    for token in sorted(registered_tokens):
        if token not in vocabulary:
            errors.append(
                f"registered exact token '{token}' is absent from plugin contract vocabulary: {plugin_path}"
            )

    discoverable_skills = {
        skill_file.parent.name
        for skill_file in (plugin_path / "skills").glob("*/SKILL.md")
        if skill_file.is_file()
    }
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            errors.append(f"invalid eval scenario #{index}: {path}")
            continue
        prompt = scenario.get("prompt")
        skill = scenario.get("skill")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"eval scenario #{index} missing prompt: {path}")
        if not isinstance(skill, str) or not skill.strip():
            errors.append(f"eval scenario #{index} missing skill: {path}")
        elif skill not in discoverable_skills:
            errors.append(
                f"eval scenario #{index} skill '{skill}' is not a discoverable immediate-child skill name with SKILL.md: {path}"
            )

        write_mode = scenario.get("write")
        if not _valid_eval_write(write_mode):
            errors.append(f"eval scenario #{index} has invalid write mode: {path}")
        elif write_mode == "approval-required" and isinstance(skill, str) and skill in discoverable_skills:
            skill_path = plugin_path / "skills" / skill / "SKILL.md"
            try:
                skill_text = skill_path.read_text(encoding="utf-8").casefold()
            except (OSError, UnicodeDecodeError):
                skill_text = ""
            for marker in WRITE_SKILL_SAFETY_MARKERS:
                if marker not in skill_text:
                    errors.append(
                        f"write-capable skill missing safety marker '{marker}': {skill_path}"
                    )

        expect = scenario.get("expect")
        if not isinstance(expect, dict):
            errors.append(f"eval scenario #{index} missing expect object: {path}")
            continue
        route = expect.get("must_route_to")
        if not isinstance(route, str) or not route.strip():
            errors.append(f"eval scenario #{index} expect.must_route_to is required: {path}")
        elif isinstance(skill, str) and route != skill:
            errors.append(f"eval scenario #{index} expect.must_route_to must match skill: {path}")

        outcome = expect.get("outcome")
        if not isinstance(outcome, str) or outcome not in ALLOWED_EVAL_OUTCOMES:
            errors.append(
                f"eval scenario #{index} expect.outcome must be one of {sorted(ALLOWED_EVAL_OUTCOMES)}: {path}"
            )

        for legacy_field in ("must_refuse", "must_mention"):
            if legacy_field in expect:
                errors.append(
                    f"eval scenario #{index} expect.{legacy_field} is a legacy v1 field; migrate to eval v2: {path}"
                )

        for field in ("must_mention_tokens", "must_convey", "must_not_claim"):
            values = expect.get(field)
            if not _valid_string_list(values):
                errors.append(
                    f"eval scenario #{index} expect.{field} must be a list of nonempty strings: {path}"
                )

        mentioned_tokens = expect.get("must_mention_tokens")
        if isinstance(mentioned_tokens, list):
            for token in mentioned_tokens:
                if not isinstance(token, str) or not token.strip():
                    continue
                if EVAL_TOKEN_PATTERN.fullmatch(token) is None:
                    errors.append(
                        f"eval scenario #{index} expect.must_mention_tokens contains non-token prose '{token}': {path}"
                    )
                    continue
                if token not in registered_tokens:
                    errors.append(
                        f"eval scenario #{index} exact token '{token}' is absent from plugin exact-token registry: {path}"
                    )
                    continue
                if token not in vocabulary:
                    errors.append(
                        f"eval scenario #{index} exact token '{token}' is absent from plugin contract vocabulary: {path}"
                    )


def _tracked_repository_paths(path: Path) -> set[Path] | None:
    """Return lexical Git-tracked paths under path, or None when Git metadata is unavailable."""
    requested_root = path.resolve()
    try:
        root_result = subprocess.run(
            ["git", "-C", str(requested_root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        git_root = Path(root_result.stdout.strip()).resolve()
        tracked_result = subprocess.run(
            ["git", "-C", str(git_root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None

    tracked_paths = {
        git_root / relative_path.decode(sys.getfilesystemencoding(), errors="surrogateescape")
        for relative_path in tracked_result.stdout.split(b"\0")
        if relative_path
    }
    return {candidate for candidate in tracked_paths if candidate.is_relative_to(requested_root)}


def _tracked_plugin_paths(plugin_path: Path) -> set[Path] | None:
    """Return Git-tracked plugin paths, or None when Git metadata is unavailable."""
    return _tracked_repository_paths(plugin_path)


def _read_secret_scan_text(path: Path) -> str:
    """Read a worktree text entry without following symlinks or skipping undecodable bytes."""
    if path.is_symlink():
        return str(path.readlink())
    return path.read_bytes().decode("utf-8", errors="replace")


def _read_index_secret_scan_entry(root: Path, path: Path) -> tuple[str, str]:
    """Return the staged Git mode and text for a tracked repository entry."""
    relative = path.absolute().relative_to(root.resolve()).as_posix()
    stage_result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "--", relative],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    first_line = stage_result.stdout.splitlines()[0]
    mode = first_line.split(maxsplit=1)[0]
    blob_result = subprocess.run(
        ["git", "-C", str(root), "show", f":{relative}"],
        check=True,
        capture_output=True,
        timeout=5,
    )
    return mode, blob_result.stdout.decode("utf-8", errors="replace")


def _iter_repository_dotenv_files(root: Path):
    tracked_paths = _tracked_repository_paths(root)
    if tracked_paths is not None:
        candidates = tracked_paths
        require_worktree_entry = False
    else:
        candidates = {path for path in root.rglob("*") if path.is_file() or path.is_symlink()}
        require_worktree_entry = True
    for path in sorted(candidates):
        if path.name != ".env" and not path.name.startswith(".env."):
            continue
        if not require_worktree_entry or path.is_file() or path.is_symlink():
            yield path


def _validate_repository_dotenv(root: Path, errors: list[str]) -> None:
    tracked_paths = _tracked_repository_paths(root)
    for path in _iter_repository_dotenv_files(root):
        symlink_error = f"repository dotenv symlink is not allowed: {path}"
        texts: list[str] = []
        if tracked_paths is not None:
            try:
                mode, staged_text = _read_index_secret_scan_entry(root, path)
            except (OSError, subprocess.SubprocessError, IndexError, ValueError):
                errors.append(f"unable to read tracked repository dotenv index: {path}")
            else:
                if mode == "120000" and symlink_error not in errors:
                    errors.append(symlink_error)
                texts.append(staged_text)
        if path.is_symlink() and symlink_error not in errors:
            errors.append(symlink_error)
        if path.is_file() or path.is_symlink():
            try:
                texts.append(_read_secret_scan_text(path))
            except (OSError, UnicodeDecodeError):
                pass
        if any(pattern.search(text) for text in texts for pattern in SECRET_PATTERNS):
            errors.append(f"credential-like secret found in repository dotenv file: {path}")


def _iter_plugin_text_files(plugin_path: Path):
    tracked_paths = _tracked_plugin_paths(plugin_path)
    for path in plugin_path.rglob("*"):
        is_dotenv = path.name == ".env" or path.name.startswith(".env.")
        if is_dotenv:
            if not (path.is_file() or path.is_symlink()):
                continue
            if tracked_paths is not None and path.absolute() not in tracked_paths:
                continue
            yield path
        elif path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _validate_plugin_text(plugin_path: Path, errors: list[str]) -> None:
    for path in _iter_plugin_text_files(plugin_path):
        try:
            text = _read_secret_scan_text(path) if path.name == ".env" or path.name.startswith(".env.") else path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for forbidden in FORBIDDEN_RUNTIME_PATHS:
            if forbidden in text:
                errors.append(f"runtime-specific absolute path '{forbidden}' found in plugin file: {path}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"credential-like secret found in plugin file: {path}")
                break


def _is_forbidden_transport_module(module: str) -> bool:
    if module == "urllib.request" or module.startswith("urllib.request."):
        return True
    root = module.split(".", 1)[0]
    return root in FORBIDDEN_TRANSPORT_ROOTS


def python_transport_findings(path: Path, text: str) -> list[str]:
    """Return AST-backed transport-boundary findings for a Python source file."""
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []

    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if _is_forbidden_transport_module(module):
                    findings.append(f"forbidden transport import {module}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = {alias.name for alias in node.names}
            if module == "urllib" and "request" in imported_names:
                findings.append("forbidden transport import urllib.request")
            elif _is_forbidden_transport_module(module):
                findings.append(f"forbidden transport import {module}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            module = node.args[0].value
            if _is_forbidden_transport_module(module):
                findings.append(f"forbidden dynamic transport import {module}")
    return findings


def _validate_cross_service_transport(plugin_path: Path, errors: list[str]) -> None:
    if plugin_path.name not in CROSS_SERVICE_PLUGINS:
        return
    for path in plugin_path.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"unable to scan cross-service Python file: {path}: {exc}")
            continue
        if python_transport_findings(path, text) or YANDEX_API_ENDPOINT_PATTERN.search(text):
            errors.append(f"cross-service transport/API client found in {path}")


def _manifest_version(path: Path, errors: list[str]) -> tuple[dict[str, Any] | None, str | None]:
    manifest = _load_json(path, errors)
    if not isinstance(manifest, dict):
        return None, None
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"plugin manifest has invalid SemVer version: {path}")
        return manifest, None
    return manifest, version


def _validate_plugin(
    root: Path,
    plugin_path: Path,
    agent_entry: dict[str, Any],
    claude_entry: dict[str, Any] | None,
    errors: list[str],
) -> None:
    codex_path = plugin_path / ".codex-plugin/plugin.json"
    claude_path = plugin_path / ".claude-plugin/plugin.json"
    codex, codex_version = _manifest_version(codex_path, errors)
    claude, claude_version = _manifest_version(claude_path, errors)
    if not isinstance(codex, dict):
        return

    agent_version = agent_entry.get("version")
    if not isinstance(agent_version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", agent_version):
        errors.append(f"agent marketplace plugin version missing or invalid: {agent_entry.get('name')}")
    versions = {
        "agent marketplace": agent_version,
        "codex manifest": codex_version,
        "claude manifest": claude_version,
        "claude marketplace": claude_entry.get("version") if isinstance(claude_entry, dict) else None,
    }
    present_versions = {value for value in versions.values() if isinstance(value, str)}
    if len(present_versions) > 1:
        errors.append(f"version mismatch for {agent_entry.get('name')}: {versions}")

    plugin_name = agent_entry.get("name")
    policy = agent_entry.get("policy")
    authentication = policy.get("authentication") if isinstance(policy, dict) else None
    if authentication not in SUPPORTED_AUTHENTICATION_POLICIES:
        errors.append(f"unsupported or missing authentication policy for {plugin_name}: {authentication}")
    if plugin_name in CROSS_SERVICE_PLUGINS:
        if authentication != "ON_USE":
            errors.append(f"cross-service authentication policy must be ON_USE for {plugin_name}")
        if (plugin_path / ".env.example").exists():
            errors.append(f"cross-service plugin must not define .env.example: {plugin_name}")

    if codex.get("name") != plugin_name:
        errors.append(f"codex manifest name mismatch for {plugin_name}: {codex_path}")
    if isinstance(claude, dict) and claude.get("name") != plugin_name:
        errors.append(f"claude manifest name mismatch for {plugin_name}: {claude_path}")
    if not isinstance(claude_entry, dict):
        errors.append(f"plugin missing from .claude-plugin/marketplace.json: {plugin_name}")
    else:
        expected_source = f"./plugins/{plugin_path.name}"
        if claude_entry.get("source") != expected_source:
            errors.append(f"claude marketplace source mismatch for {plugin_name}")

    skills_value = codex.get("skills")
    if not isinstance(skills_value, str):
        errors.append(f"plugin manifest missing skills path: {codex_path}")
        return
    if isinstance(claude, dict) and claude.get("skills") != skills_value:
        errors.append(f"skills path mismatch between plugin manifests: {plugin_path}")
    skills_path = plugin_path / skills_value
    if not skills_path.is_dir():
        errors.append(f"plugin skills target does not exist: {skills_path}")
        return

    skill_files = sorted(skills_path.glob("*/SKILL.md"))
    if not skill_files:
        errors.append(f"plugin has no discoverable SKILL.md files: {skills_path}")
    for skill_path in skill_files:
        _validate_skill(skill_path, errors)

    _validate_evals(plugin_path, errors)
    _validate_plugin_text(plugin_path, errors)
    _validate_cross_service_transport(plugin_path, errors)

    readme_path = plugin_path / "README.md"
    try:
        plugin_readme = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing plugin README: {readme_path}")
        plugin_readme = ""
    if CAPABILITY_HEADER not in plugin_readme:
        errors.append(f"plugin README missing capability matrix: {readme_path}")

    if isinstance(codex_version, str):
        changelog_path = plugin_path / "CHANGELOG.md"
        try:
            changelog = changelog_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"missing plugin CHANGELOG: {changelog_path}")
            changelog = ""
        if not re.search(rf"^##\s+(?:\[)?{re.escape(codex_version)}(?:\])?(?:\s|$)", changelog, re.MULTILINE):
            errors.append(f"CHANGELOG version {codex_version} missing for {plugin_name}: {changelog_path}")

        root_readme_path = root / "README.md"
        try:
            root_readme = root_readme_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"missing root README: {root_readme_path}")
            root_readme = ""
        plugin_marker = f"plugins/{plugin_path.name}/"
        matching_rows = [line for line in root_readme.splitlines() if plugin_marker in line]
        if not any(re.search(rf"\|\s*{re.escape(codex_version)}\s*\|", line) for line in matching_rows):
            errors.append(f"root README version {codex_version} missing for {plugin_name}")


def validate_repository(
    root: Path,
    *,
    today: date | None = None,
    changed_paths: set[str] | None = None,
    strict_reference_freshness: bool = False,
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    _validate_repository_dotenv(root, errors)
    agent_marketplace_path = root / ".agents/plugins/marketplace.json"
    claude_marketplace_path = root / ".claude-plugin/marketplace.json"
    agent_marketplace = _load_json(agent_marketplace_path, errors)
    claude_marketplace = _load_json(claude_marketplace_path, errors)
    if not isinstance(agent_marketplace, dict) or not isinstance(claude_marketplace, dict):
        return errors

    plugins = agent_marketplace.get("plugins")
    claude_plugins = claude_marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append(f"marketplace has no plugins: {agent_marketplace_path}")
        return errors
    if not isinstance(claude_plugins, list):
        errors.append(f"marketplace has no plugins: {claude_marketplace_path}")
        claude_plugins = []
    claude_by_name = {
        item.get("name"): item
        for item in claude_plugins
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    known_plugin_dirs: set[str] = set()
    marketplace_skill_files: list[Path] = []
    for item in plugins:
        if not isinstance(item, dict):
            errors.append(f"marketplace plugin entry is not an object: {agent_marketplace_path}")
            continue
        source = item.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            errors.append(f"marketplace plugin must use local source object: {item.get('name')}")
            continue
        raw_path = source.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"marketplace plugin source path missing: {item.get('name')}")
            continue
        plugin_path = (root / raw_path).resolve()
        try:
            plugin_path.relative_to(root)
        except ValueError:
            errors.append(f"marketplace source escapes repository root: {raw_path}")
            continue
        if not plugin_path.is_dir():
            errors.append(f"marketplace source path does not exist: {raw_path}")
            continue
        known_plugin_dirs.add(plugin_path.name)
        marketplace_skill_files.extend(sorted((plugin_path / "skills").glob("*/SKILL.md")))
        _validate_plugin(root, plugin_path, item, claude_by_name.get(item.get("name")), errors)

    plugins_root = root / "plugins"
    if plugins_root.is_dir():
        repository_plugin_dirs = {
            path.name for path in plugins_root.iterdir() if path.is_dir()
        }
        for plugin_dir in sorted(repository_plugin_dirs - known_plugin_dirs):
            errors.append(f"plugin directory absent from marketplace: {plugins_root / plugin_dir}")

    _validate_marketplace_skill_names(marketplace_skill_files, errors)

    agent_names = {item.get("name") for item in plugins if isinstance(item, dict)}
    extra_claude = set(claude_by_name) - agent_names
    for name in sorted(extra_claude):
        errors.append(f"claude marketplace contains plugin absent from agent marketplace: {name}")

    errors.extend(validate_bilingual_docs(root, known_plugin_dirs))

    matrix_path = root / "docs/CONTRACT_MATRIX.json"
    matrix = _load_json(matrix_path, errors)
    if matrix is not None:
        errors.extend(
            validate_contract_matrix(
                root,
                matrix,
                known_plugins=known_plugin_dirs,
                today=today,
                changed_paths=changed_paths,
                strict_freshness=strict_reference_freshness,
            )
        )

    return errors


def _read_changed_paths(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    return {
        line.strip().replace("\\", "/").removeprefix("./")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repository contracts")
    parser.add_argument("--changed-files-file", type=Path)
    parser.add_argument("--strict-reference-freshness", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(
        root,
        changed_paths=_read_changed_paths(args.changed_files_file),
        strict_reference_freshness=args.strict_reference_freshness,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())