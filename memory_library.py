"""Offline Phase 1 facade for manually managed Markdown memories."""

from __future__ import annotations

import math
import os
import re
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import frontmatter


__all__ = [
    "MemoryFormatError",
    "MemoryLibrary",
    "MemoryProvenance",
    "MemoryRecord",
    "PathValidation",
    "PathValidationError",
    "SearchResult",
]


_MEMORY_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_MEMORY_FILENAME_RE = re.compile(r"^(?P<id>[0-9a-f]{12})\.md$")
_LATIN_OR_NUMBER_RE = re.compile(r"[a-z0-9]+(?:[_.:-][a-z0-9]+)*")
_CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
_UNSAFE_TITLE_RE = re.compile(r"[<>:\"/\\|?*]")
_PROHIBITED_PATH_MARKERS = (
    "production",
    "prod",
    "deploy",
    ".runtime",
    "old-ombre",
    "old_ombre",
    "oldombre",
)
_DYNAMIC = "dynamic"
_ARCHIVE = "archive"
_UNCATEGORIZED = "未分类"
_SOURCE = "phase1_manual"
_BM25_K1 = 1.4
_BM25_B = 0.72
_MAX_ID_ATTEMPTS = 128


class PathValidationError(ValueError):
    """Raised when the explicit library root fails a safety check."""


class MemoryFormatError(ValueError):
    """Raised when a discovered Phase 1 Markdown record is malformed."""


@dataclass(frozen=True, slots=True)
class MemoryProvenance:
    source: Literal["phase1_manual"] = _SOURCE
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: str
    layer: Literal["dynamic", "archive"]
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: str
    updated_at: str
    provenance: MemoryProvenance
    archived: bool


@dataclass(frozen=True, slots=True)
class SearchResult:
    record: MemoryRecord
    score: float


@dataclass(frozen=True, slots=True)
class PathValidation:
    root: Path
    buckets_dir: Path
    state_dir: Path
    dynamic_dir: Path
    permanent_dir: Path
    archive_dir: Path
    feel_dir: Path
    root_exists: bool
    root_nonempty: bool


class MemoryLibrary:
    """Small offline facade whose only source of truth is Markdown."""

    def __init__(
        self,
        root: Path,
        *,
        allow_existing_nonempty: bool = False,
    ) -> None:
        if not isinstance(allow_existing_nonempty, bool):
            raise PathValidationError("allow_existing_nonempty must be a boolean")
        self._requested_root = _coerce_explicit_root(root)
        self._allow_existing_nonempty = allow_existing_nonempty
        initial = self._build_path_validation(enforce_existing_policy=True)
        self._root = initial.root

    def validate_paths(self) -> PathValidation:
        """Revalidate all derived paths without creating or changing anything."""

        return self._build_path_validation(enforce_existing_policy=False)

    def create(
        self,
        title: str,
        body: str,
        tags: list[str] | None = None,
    ) -> MemoryRecord:
        """Create one new dynamic Markdown record using an exclusive write."""

        clean_title = _normalize_title(title)
        clean_body = _normalize_body(body)
        clean_tags = _normalize_tags(tags)
        paths = self.validate_paths()

        target_dir = _safe_child(paths.dynamic_dir, _UNCATEGORIZED)
        target_dir.mkdir(parents=True, exist_ok=True)
        _assert_no_symlink_components(target_dir)
        target_dir = target_dir.resolve(strict=True)
        _assert_contained(target_dir, paths.root)
        _assert_contained(target_dir, paths.dynamic_dir)

        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata_base = {
            "name": clean_title,
            "tags": list(clean_tags),
            "domain": [_UNCATEGORIZED],
            "valence": 0.5,
            "arousal": 0.3,
            "importance": 5,
            "type": _DYNAMIC,
            "created": timestamp,
            "last_active": timestamp,
            "updated_at": timestamp,
            "activation_count": 0,
            "source": _SOURCE,
        }

        for _attempt in range(_MAX_ID_ATTEMPTS):
            memory_id = uuid.uuid4().hex[:12]
            if self._find_record_paths(memory_id, paths):
                continue

            target = _safe_child(target_dir, f"{memory_id}.md")
            metadata = {"id": memory_id, **metadata_base}
            payload = frontmatter.dumps(frontmatter.Post(clean_body, **metadata))
            if not payload.endswith("\n"):
                payload += "\n"

            try:
                with target.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                continue

            return self._load_record_path(target, archived=False, root=paths.root)

        raise FileExistsError("unable to allocate a unique Phase 1 memory ID")

    def get(self, memory_id: str) -> MemoryRecord | None:
        """Get one exact record from dynamic or archive storage only."""

        clean_id = _validate_memory_id(memory_id)
        paths = self.validate_paths()
        matches = self._find_record_paths(clean_id, paths)
        if not matches:
            return None
        if len(matches) != 1:
            raise MemoryFormatError("duplicate Phase 1 memory ID")
        path, archived = matches[0]
        return self._load_record_path(path, archived=archived, root=paths.root)

    def list(
        self,
        *,
        archived: bool = False,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        """List records from exactly one selected layer in ID order."""

        clean_limit = _validate_limit(limit)
        records = self._records_for_layer(archived=archived)
        records.sort(key=lambda record: record.id)
        return records[:clean_limit]

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        archived: bool = False,
    ) -> list[SearchResult]:
        """Run deterministic, in-memory BM25-style lexical search."""

        clean_limit = _validate_limit(limit)
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query.strip():
            return []

        query_terms = tuple(dict.fromkeys(_tokenize_lexical(query)))
        if not query_terms:
            return []

        records = self._records_for_layer(archived=archived)
        if not records:
            return []

        profiles = [_weighted_term_profile(record) for record in records]
        document_frequency: Counter[str] = Counter()
        for term_frequency, _length in profiles:
            present = set(term_frequency)
            for term in query_terms:
                if term in present:
                    document_frequency[term] += 1

        document_count = len(records)
        average_length = sum(length for _terms, length in profiles) / document_count
        average_length = max(average_length, 1.0)
        results: list[SearchResult] = []

        for record, (term_frequency, document_length) in zip(records, profiles):
            raw_score = 0.0
            for term in query_terms:
                frequency = float(term_frequency.get(term, 0.0))
                if frequency <= 0:
                    continue
                frequency_in_documents = int(document_frequency.get(term, 0))
                inverse_document_frequency = math.log(
                    1.0
                    + (document_count - frequency_in_documents + 0.5)
                    / (frequency_in_documents + 0.5)
                )
                denominator = frequency + _BM25_K1 * (
                    1.0
                    - _BM25_B
                    + _BM25_B * (document_length / average_length)
                )
                raw_score += inverse_document_frequency * (
                    frequency * (_BM25_K1 + 1.0)
                ) / denominator

            score = round(raw_score, 6)
            if score > 0:
                results.append(SearchResult(record=record, score=score))

        results.sort(key=lambda result: (-result.score, result.record.id))
        return results[:clean_limit]

    def _build_path_validation(self, *, enforce_existing_policy: bool) -> PathValidation:
        requested = self._requested_root
        _assert_no_symlink_components(requested)
        root = requested.resolve(strict=False)
        _assert_not_prohibited_path(requested)
        _assert_not_prohibited_path(root)

        stored_root = getattr(self, "_root", None)
        if stored_root is not None and root != stored_root:
            raise PathValidationError("resolved library root changed after construction")

        repo_root = Path(__file__).resolve().parent
        repo_buckets = _safe_child(repo_root, "buckets")
        repo_state = _safe_child(repo_root, "state")
        for prohibited in (repo_root, repo_buckets, repo_state):
            if _paths_overlap(root, prohibited):
                raise PathValidationError("library root overlaps the repository")

        buckets_dir = _safe_child(root, "buckets")
        state_dir = _safe_child(root, "state")
        dynamic_dir = _safe_child(buckets_dir, _DYNAMIC)
        permanent_dir = _safe_child(buckets_dir, "permanent")
        archive_dir = _safe_child(buckets_dir, _ARCHIVE)
        feel_dir = _safe_child(buckets_dir, "feel")

        root_exists = root.exists()
        if root_exists and not root.is_dir():
            raise PathValidationError("library root exists but is not a directory")
        try:
            root_nonempty = root_exists and any(root.iterdir())
        except OSError:
            raise PathValidationError("library root cannot be inspected safely") from None
        if (
            enforce_existing_policy
            and root_nonempty
            and not self._allow_existing_nonempty
        ):
            raise PathValidationError(
                "existing nonempty root requires allow_existing_nonempty=True"
            )

        return PathValidation(
            root=root,
            buckets_dir=buckets_dir,
            state_dir=state_dir,
            dynamic_dir=dynamic_dir,
            permanent_dir=permanent_dir,
            archive_dir=archive_dir,
            feel_dir=feel_dir,
            root_exists=root_exists,
            root_nonempty=bool(root_nonempty),
        )

    def _records_for_layer(self, *, archived: bool) -> list[MemoryRecord]:
        paths = self.validate_paths()
        layer_dir = paths.archive_dir if archived else paths.dynamic_dir
        return [
            self._load_record_path(path, archived=archived, root=paths.root)
            for path in _iter_record_paths(layer_dir, paths.root)
        ]

    def _find_record_paths(
        self,
        memory_id: str,
        paths: PathValidation,
    ) -> list[tuple[Path, bool]]:
        matches: list[tuple[Path, bool]] = []
        for layer_dir, archived in (
            (paths.dynamic_dir, False),
            (paths.archive_dir, True),
        ):
            for path in _iter_record_paths(layer_dir, paths.root):
                if path.stem == memory_id:
                    matches.append((path, archived))
        matches.sort(key=lambda item: (item[1], item[0].as_posix()))
        return matches

    @staticmethod
    def _load_record_path(
        path: Path,
        *,
        archived: bool,
        root: Path,
    ) -> MemoryRecord:
        layer_dir = _safe_child(_safe_child(root, "buckets"), _ARCHIVE if archived else _DYNAMIC)
        _assert_no_symlink_components(path)
        resolved = path.resolve(strict=True)
        _assert_contained(resolved, root)
        _assert_contained(resolved, layer_dir)
        if resolved.is_symlink():
            raise PathValidationError("symlink memory files are not allowed")

        filename_match = _MEMORY_FILENAME_RE.fullmatch(resolved.name)
        if filename_match is None:
            raise MemoryFormatError("invalid Phase 1 memory filename")

        try:
            raw_text = resolved.read_text(encoding="utf-8")
            post = frontmatter.loads(raw_text)
        except Exception:
            raise MemoryFormatError("malformed Phase 1 memory frontmatter") from None

        metadata = dict(post.metadata)
        memory_id = metadata.get("id")
        if not isinstance(memory_id, str) or not _MEMORY_ID_RE.fullmatch(memory_id):
            raise MemoryFormatError("invalid Phase 1 memory ID")
        if memory_id != filename_match.group("id"):
            raise MemoryFormatError("memory ID does not match its filename")

        raw_title = metadata["name"] if "name" in metadata else metadata.get("title")
        title = _validate_stored_title(raw_title)
        body = _validate_stored_body(post.content, raw_text=raw_text)
        tags = _validate_stored_tags(metadata.get("tags"))

        source = metadata.get("source")
        if source != _SOURCE:
            raise MemoryFormatError("invalid Phase 1 memory provenance")
        source_id = _normalize_source_id(metadata.get("source_id"))

        created_value = metadata.get("created_at") or metadata.get("created")
        updated_value = (
            metadata.get("updated_at")
            or metadata.get("last_active")
            or created_value
        )
        created_at = _validated_timestamp(created_value, "created timestamp")
        updated_at = _validated_timestamp(updated_value, "updated timestamp")

        record_type = metadata.get("type")
        if not archived and record_type != _DYNAMIC:
            raise MemoryFormatError("dynamic record has an invalid type")
        if archived and record_type not in {_DYNAMIC, _ARCHIVE, "archived"}:
            raise MemoryFormatError("archive record has an invalid type")

        return MemoryRecord(
            id=memory_id,
            layer=_ARCHIVE if archived else _DYNAMIC,
            title=title,
            body=body,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
            provenance=MemoryProvenance(source=_SOURCE, source_id=source_id),
            archived=archived,
        )


def _coerce_explicit_root(root: Path) -> Path:
    if root is None:
        raise PathValidationError("an explicit absolute root is required")
    if isinstance(root, str) and not root.strip():
        raise PathValidationError("an explicit absolute root is required")
    if not isinstance(root, (str, os.PathLike)):
        raise PathValidationError("root must be a path")
    candidate = Path(root)
    if not candidate.is_absolute():
        raise PathValidationError("library root must be absolute")
    if candidate.anchor[:2] == "\\\\":
        raise PathValidationError("UNC library roots are not allowed")
    return candidate


def _safe_child(parent: Path, *components: str) -> Path:
    target = Path(parent)
    for component in components:
        if not isinstance(component, str) or component in {"", ".", ".."}:
            raise PathValidationError("invalid child path component")
        child = Path(component)
        if (
            child.is_absolute()
            or child.drive
            or len(child.parts) != 1
            or "/" in component
            or "\\" in component
        ):
            raise PathValidationError("absolute or traversing child path is not allowed")
        target = target / child
    resolved_parent = Path(parent).resolve(strict=False)
    resolved_target = target.resolve(strict=False)
    _assert_contained(resolved_target, resolved_parent)
    _assert_no_symlink_components(target)
    return resolved_target


def _assert_contained(path: Path, parent: Path) -> None:
    try:
        relative = Path(path).relative_to(Path(parent))
    except ValueError:
        raise PathValidationError("resolved path escapes its allowed root") from None
    if relative == Path("."):
        raise PathValidationError("child path must not equal its allowed root")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        Path(path).relative_to(Path(parent))
    except ValueError:
        return False
    return True


def _paths_overlap(left: Path, right: Path) -> bool:
    return _is_relative_to(left, right) or _is_relative_to(right, left)


def _assert_not_prohibited_path(path: Path) -> None:
    for component in Path(path).parts:
        normalized = unicodedata.normalize("NFKC", component).casefold()
        if any(marker in normalized for marker in _PROHIBITED_PATH_MARKERS):
            raise PathValidationError("library root contains a prohibited path marker")


def _assert_no_symlink_components(path: Path) -> None:
    candidate = Path(path)
    current = Path(candidate.anchor)
    parts = candidate.parts[1:] if candidate.anchor else candidate.parts
    for part in parts:
        current = current / part
        try:
            is_junction = getattr(current, "is_junction", None)
            junction = bool(is_junction()) if callable(is_junction) else False
            if current.is_symlink() or junction:
                raise PathValidationError("symlink or junction paths are not allowed")
        except OSError:
            raise PathValidationError("path components cannot be inspected safely") from None


def _iter_record_paths(layer_dir: Path, root: Path) -> list[Path]:
    _assert_no_symlink_components(layer_dir)
    resolved_layer = Path(layer_dir).resolve(strict=False)
    _assert_contained(resolved_layer, root)
    if not resolved_layer.exists():
        return []
    if not resolved_layer.is_dir():
        raise PathValidationError("memory layer path is not a directory")

    paths: list[Path] = []

    def fail_walk(_error: OSError) -> None:
        raise PathValidationError("memory layer cannot be enumerated safely")

    for current_text, directory_names, filenames in os.walk(
        resolved_layer,
        topdown=True,
        onerror=fail_walk,
        followlinks=False,
    ):
        current = Path(current_text)
        _assert_no_symlink_components(current)
        resolved_current = current.resolve(strict=True)
        _assert_contained(resolved_current, root)
        if resolved_current != resolved_layer:
            _assert_contained(resolved_current, resolved_layer)

        safe_directories: list[str] = []
        for name in sorted(directory_names):
            directory = current / name
            _assert_no_symlink_components(directory)
            resolved_directory = directory.resolve(strict=True)
            _assert_contained(resolved_directory, root)
            _assert_contained(resolved_directory, resolved_layer)
            safe_directories.append(name)
        directory_names[:] = safe_directories

        for filename in sorted(filenames):
            candidate = current / filename
            _assert_no_symlink_components(candidate)
            resolved_candidate = candidate.resolve(strict=True)
            _assert_contained(resolved_candidate, root)
            _assert_contained(resolved_candidate, resolved_layer)
            if resolved_candidate.is_symlink():
                raise PathValidationError("symlink memory files are not allowed")
            if _MEMORY_FILENAME_RE.fullmatch(resolved_candidate.name):
                paths.append(resolved_candidate)

    paths.sort(key=lambda path: (path.name, path.as_posix()))
    return paths


def _validate_memory_id(memory_id: str) -> str:
    if not isinstance(memory_id, str) or not _MEMORY_ID_RE.fullmatch(memory_id):
        raise ValueError("memory_id must be exactly 12 lowercase hexadecimal characters")
    return memory_id


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be a non-boolean integer from 1 through 100")
    return limit


def _normalize_title(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("title must be a string")
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.category(character)[:1] == "C"
    )
    normalized = _UNSAFE_TITLE_RE.sub("", normalized)
    normalized = " ".join(normalized.split()).strip()[:80]
    if not normalized:
        raise ValueError("title must not be empty")
    return normalized


def _normalize_body(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("body must be a string")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError("body must not be empty")
    for character in normalized:
        if character not in {"\n", "\t"} and unicodedata.category(character)[:1] == "C":
            raise ValueError("body contains a control character")
    return normalized


def _normalize_tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TypeError("tags must be a list of strings")
    tags: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise TypeError("tags must contain strings only")
        tag = unicodedata.normalize("NFKC", item).strip()
        if not tag:
            continue
        if any(unicodedata.category(character)[:1] == "C" for character in tag):
            raise ValueError("tag contains a control character")
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tuple(tags)


def _validate_stored_title(value: object) -> str:
    """Accept a persisted title only when creation would leave it unchanged."""

    try:
        normalized = _normalize_title(value)
    except (TypeError, ValueError):
        raise MemoryFormatError("invalid Phase 1 stored title") from None
    if normalized != value:
        raise MemoryFormatError("stored Phase 1 title is not canonical")
    return value


def _validate_stored_tags(value: object) -> tuple[str, ...]:
    """Validate persisted tag order and values without cleaning or deduplication."""

    if not isinstance(value, list):
        raise MemoryFormatError("stored Phase 1 tags must be a list")
    try:
        normalized = _normalize_tags(value)
    except (TypeError, ValueError):
        raise MemoryFormatError("invalid Phase 1 stored tags") from None
    if list(normalized) != value:
        raise MemoryFormatError("stored Phase 1 tags are not canonical")
    return tuple(value)


def _validate_stored_body(value: object, *, raw_text: str) -> str:
    """Validate parser-provided body text without changing the returned value."""

    # The frontmatter parser has already removed the frontmatter delimiters. The
    # facade performs no further framing or newline cleanup here: the parsed
    # body must already equal the form accepted and written by ``create()``.
    try:
        normalized = _normalize_body(value)
    except (TypeError, ValueError):
        raise MemoryFormatError("invalid Phase 1 stored body") from None
    if normalized != value:
        raise MemoryFormatError("stored Phase 1 body is not canonical")

    lines = raw_text.splitlines(keepends=True)
    if not lines or re.fullmatch(r"---[ \t]*(?:\n)?", lines[0]) is None:
        raise MemoryFormatError("malformed Phase 1 memory frontmatter")
    for index, line in enumerate(lines[1:], start=1):
        if re.fullmatch(r"---[ \t]*(?:\n)?", line) is not None:
            raw_body = "".join(lines[index + 1 :])
            break
    else:
        raise MemoryFormatError("malformed Phase 1 memory frontmatter")

    # ``frontmatter.dumps()`` inserts one separator newline before the body,
    # and ``create()`` ensures one terminal file newline. Exclude only those
    # framing newlines; all other outer whitespace remains body content.
    if raw_body.startswith("\n"):
        raw_body = raw_body[1:]
    stored_body = raw_body[:-1] if raw_body.endswith("\n") else raw_body
    try:
        normalized_stored_body = _normalize_body(stored_body)
    except (TypeError, ValueError):
        raise MemoryFormatError("invalid Phase 1 stored body") from None
    if normalized_stored_body != stored_body or stored_body != value:
        raise MemoryFormatError("stored Phase 1 body is not canonical")
    return value


def _normalize_source_id(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise MemoryFormatError("invalid Phase 1 source_id")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or len(normalized) > 80
        or ".." in normalized
        or re.fullmatch(r"[A-Za-z0-9_.:-]+", normalized) is None
    ):
        raise MemoryFormatError("invalid Phase 1 source_id")
    return normalized


def _validated_timestamp(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryFormatError(f"invalid Phase 1 {field_name}")
    text = value.strip()
    parse_value = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parse_value)
    except ValueError:
        raise MemoryFormatError(f"invalid Phase 1 {field_name}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MemoryFormatError(f"Phase 1 {field_name} must be timezone-aware")
    return text


def _tokenize_lexical(value: object) -> list[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    tokens = _LATIN_OR_NUMBER_RE.findall(text)
    for run in _CJK_RUN_RE.findall(text):
        for size in (2, 3):
            if len(run) < size:
                continue
            tokens.extend(run[index : index + size] for index in range(len(run) - size + 1))
    return tokens


def _weighted_term_profile(record: MemoryRecord) -> tuple[Counter[str], float]:
    fields = (
        (record.title, 3.0),
        (" ".join(record.tags), 2.0),
        (record.body, 1.0),
    )
    term_frequency: Counter[str] = Counter()
    weighted_length = 0.0
    for text, weight in fields:
        tokens = _tokenize_lexical(text)
        for token in tokens:
            term_frequency[token] += weight
        weighted_length += len(tokens) * weight
    return term_frequency, max(weighted_length, 1.0)
