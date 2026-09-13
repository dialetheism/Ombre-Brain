from __future__ import annotations

import http.client
import json
import os
import re
import socket
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

import memory_library as memory_module


MemoryFormatError = memory_module.MemoryFormatError
MemoryLibrary = memory_module.MemoryLibrary
PathValidationError = memory_module.PathValidationError

_TIMESTAMP = "2026-01-02T03:04:05+00:00"
_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _isolated_root(tmp_path: Path, name: str = "memory-root") -> Path:
    root = (tmp_path / name).resolve()
    repo_root = Path(memory_module.__file__).resolve().parent
    assert not _is_relative_to(root, repo_root)
    assert not _is_relative_to(repo_root, root)
    return root


def _metadata(memory_id: str) -> dict[str, object]:
    return {
        "id": memory_id,
        "name": "Valid title",
        "tags": ["valid-tag"],
        "domain": ["未分类"],
        "valence": 0.5,
        "arousal": 0.3,
        "importance": 5,
        "type": "dynamic",
        "created": _TIMESTAMP,
        "last_active": _TIMESTAMP,
        "updated_at": _TIMESTAMP,
        "activation_count": 0,
        "source": "phase1_manual",
    }


def _frontmatter_prefix(metadata: dict[str, object]) -> str:
    lines = ["---"]
    lines.extend(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in metadata.items()
    )
    lines.append("---")
    return "\n".join(lines) + "\n"


def _write_record(
    root: Path,
    *,
    layer: str,
    memory_id: str,
    body: str = "Valid body",
    metadata_updates: dict[str, object] | None = None,
    remove_metadata: tuple[str, ...] = (),
) -> Path:
    metadata = _metadata(memory_id)
    if metadata_updates:
        metadata.update(metadata_updates)
    for key in remove_metadata:
        metadata.pop(key, None)
    directory = root / "buckets" / layer / "manual"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{memory_id}.md"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(_frontmatter_prefix(metadata) + body)
    return path


def _snapshot_files(root: Path) -> dict[str, tuple[bytes, int, int]]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in root.rglob("*")
        if path.is_file()
    }


def test_create_get_and_reconstruction_round_trip(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    library = MemoryLibrary(root)
    title = "常原与 Casper 的记忆"
    body = "第一行：一起整理记忆。\nSecond line: deterministic recall."
    tags = ["关系", "Phase 1", "关系"]

    record = library.create(title, body, tags)

    assert _ID_RE.fullmatch(record.id)
    assert record.title == title
    assert record.body == body
    assert record.tags == ("关系", "Phase 1")
    assert record.layer == "dynamic"
    assert record.archived is False
    assert record.provenance.source == "phase1_manual"
    created = datetime.fromisoformat(record.created_at)
    updated = datetime.fromisoformat(record.updated_at)
    assert created.tzinfo is not None and created.utcoffset() is not None
    assert updated.tzinfo is not None and updated.utcoffset() is not None

    expected_path = root / "buckets" / "dynamic" / "未分类" / f"{record.id}.md"
    assert expected_path.is_file()
    assert [path for path in root.rglob("*") if path.is_file()] == [expected_path]
    assert library.get(record.id) == record

    reconstructed = MemoryLibrary(root, allow_existing_nonempty=True)
    assert reconstructed.get(record.id) == record
    assert reconstructed.get(record.id).body == body
    assert not (root / "state").exists()
    assert not (root / "buckets" / "permanent").exists()
    assert not (root / "buckets" / "feel").exists()


def test_empty_tag_list_round_trip(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    record = MemoryLibrary(root).create("Empty tags", "Body", tags=[])

    assert record.tags == ()
    reloaded = MemoryLibrary(root, allow_existing_nonempty=True).get(record.id)
    assert reloaded is not None
    assert reloaded.tags == ()


def test_manually_written_valid_body_loads_unchanged(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    memory_id = "100000000001"
    body = "第一段\nSecond paragraph"
    _write_record(root, layer="dynamic", memory_id=memory_id, body=body)

    record = MemoryLibrary(root, allow_existing_nonempty=True).get(memory_id)

    assert record is not None
    assert record.body == body


@pytest.mark.parametrize("body", [" leading", "trailing ", "   ", "body\x01control"])
def test_noncanonical_or_invalid_stored_body_fails_closed(
    tmp_path: Path,
    body: str,
) -> None:
    root = _isolated_root(tmp_path)
    memory_id = "100000000002"
    _write_record(root, layer="dynamic", memory_id=memory_id, body=body)

    with pytest.raises(MemoryFormatError):
        MemoryLibrary(root, allow_existing_nonempty=True).get(memory_id)


def test_empty_stored_body_fails_closed(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    memory_id = "100000000003"
    _write_record(root, layer="dynamic", memory_id=memory_id, body="")

    with pytest.raises(MemoryFormatError):
        MemoryLibrary(root, allow_existing_nonempty=True).get(memory_id)


@pytest.mark.parametrize("separator", ["\r\n", "\r"])
def test_frontmatter_parser_normalizes_file_newlines(
    tmp_path: Path,
    separator: str,
) -> None:
    root = _isolated_root(tmp_path)
    memory_id = "100000000004"
    metadata = _metadata(memory_id)
    directory = root / "buckets" / "dynamic" / "manual"
    directory.mkdir(parents=True)
    path = directory / f"{memory_id}.md"
    prefix = _frontmatter_prefix(metadata).replace("\n", separator)
    path.write_bytes((prefix + f"first{separator}second").encode("utf-8"))

    record = MemoryLibrary(root, allow_existing_nonempty=True).get(memory_id)

    assert record is not None
    assert record.body == "first\nsecond"


@pytest.mark.parametrize(
    ("updates", "remove"),
    [
        ({"name": "x" * 81}, ()),
        ({"name": " title"}, ()),
        ({"name": "bad/name"}, ()),
        ({"name": "bad\x01name"}, ()),
        ({"name": "", "title": "Fallback must not win"}, ()),
        ({}, ("tags",)),
        ({"tags": "not-a-list"}, ()),
        ({"tags": [1]}, ()),
        ({"tags": [""]}, ()),
        ({"tags": ["   "]}, ()),
        ({"tags": ["duplicate", "duplicate"]}, ()),
        ({"tags": [" needs-trim"]}, ()),
        ({"tags": ["Ａ"]}, ()),
        ({"tags": ["bad\x01tag"]}, ()),
        ({"source": "unexpected"}, ()),
        ({"type": "permanent"}, ()),
        ({"created": "2026-01-02T03:04:05"}, ()),
    ],
)
def test_malformed_stored_metadata_fails_closed(
    tmp_path: Path,
    updates: dict[str, object],
    remove: tuple[str, ...],
) -> None:
    root = _isolated_root(tmp_path)
    memory_id = "200000000001"
    _write_record(
        root,
        layer="dynamic",
        memory_id=memory_id,
        metadata_updates=updates,
        remove_metadata=remove,
    )
    before = _snapshot_files(root)

    with pytest.raises(MemoryFormatError):
        MemoryLibrary(root, allow_existing_nonempty=True).get(memory_id)

    assert _snapshot_files(root) == before


def test_list_and_search_are_deterministic_and_read_only(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    library = MemoryLibrary(root)
    records = [
        library.create("Shared lexical title", "same lexical body", ["same-tag"]),
        library.create("Shared lexical title", "same lexical body", ["same-tag"]),
        library.create("Unrelated title", "different material", ["other-tag"]),
    ]

    expected_ids = sorted(record.id for record in records)
    assert [record.id for record in library.list()] == expected_ids
    assert [record.id for record in library.list(limit=2)] == expected_ids[:2]
    assert library.search("") == []
    assert library.search("   ") == []

    before = _snapshot_files(root)
    first = library.search("shared lexical")
    second = library.search("shared lexical")
    after = _snapshot_files(root)

    assert first == second
    assert len(first) == 2
    assert all(result.score > 0 for result in first)
    assert all(result.score == round(result.score, 6) for result in first)
    assert [result.score for result in first] == sorted(
        (result.score for result in first), reverse=True
    )
    for left, right in zip(first, first[1:]):
        if left.score == right.score:
            assert left.record.id < right.record.id
    assert before == after
    assert not (root / "state").exists()
    assert not any(path.suffix in {".db", ".jsonl"} for path in root.rglob("*"))


@pytest.mark.parametrize("invalid_limit", [True, 0, 101, "3"])
def test_list_and_search_reject_invalid_limits(
    tmp_path: Path,
    invalid_limit: object,
) -> None:
    library = MemoryLibrary(_isolated_root(tmp_path))

    with pytest.raises(ValueError):
        library.list(limit=invalid_limit)
    with pytest.raises(ValueError):
        library.search("query", limit=invalid_limit)


def test_facade_operations_make_zero_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _isolated_root(tmp_path)
    network_calls: list[str] = []

    def blocked(entrypoint: str):
        def fail(*_args: object, **_kwargs: object) -> None:
            network_calls.append(entrypoint)
            raise AssertionError(f"unexpected network call through {entrypoint}")

        return fail

    monkeypatch.setattr(socket, "socket", blocked("socket.socket"))
    monkeypatch.setattr(
        socket,
        "create_connection",
        blocked("socket.create_connection"),
    )
    monkeypatch.setattr(
        http.client.HTTPConnection,
        "connect",
        blocked("http.client.HTTPConnection.connect"),
    )
    monkeypatch.setattr(
        http.client.HTTPSConnection,
        "connect",
        blocked("http.client.HTTPSConnection.connect"),
    )
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        blocked("urllib.request.urlopen"),
    )

    library = MemoryLibrary(root)
    record = library.create("Offline memory", "networkless lexical body", ["offline"])

    assert library.get(record.id) == record
    assert [item.id for item in library.list()] == [record.id]
    assert [result.record.id for result in library.search("networkless")] == [record.id]
    assert network_calls == []


def test_dynamic_archive_and_ignored_layer_boundaries(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    dynamic_id = "300000000001"
    archive_id = "300000000002"
    permanent_id = "300000000003"
    feel_id = "300000000004"
    _write_record(
        root,
        layer="dynamic",
        memory_id=dynamic_id,
        body="dynamicneedle",
    )
    _write_record(
        root,
        layer="archive",
        memory_id=archive_id,
        body="archiveneedle",
        metadata_updates={"type": "archived"},
    )
    _write_record(
        root,
        layer="permanent",
        memory_id=permanent_id,
        body="permanentneedle",
        metadata_updates={"type": "permanent"},
    )
    _write_record(
        root,
        layer="feel",
        memory_id=feel_id,
        body="feelneedle",
        metadata_updates={"type": "feel"},
    )
    library = MemoryLibrary(root, allow_existing_nonempty=True)

    assert [record.id for record in library.list()] == [dynamic_id]
    assert [record.id for record in library.list(archived=True)] == [archive_id]
    assert [result.record.id for result in library.search("dynamicneedle")] == [dynamic_id]
    assert library.search("archiveneedle") == []
    assert [
        result.record.id for result in library.search("archiveneedle", archived=True)
    ] == [archive_id]
    assert library.get(dynamic_id) is not None
    assert library.get(archive_id) is not None
    assert library.get(permanent_id) is None
    assert library.get(feel_id) is None


def test_relative_and_empty_roots_are_rejected() -> None:
    with pytest.raises(PathValidationError):
        MemoryLibrary(Path("relative-memory-root"))
    with pytest.raises(PathValidationError):
        MemoryLibrary("")


def test_repo_overlap_roots_are_rejected() -> None:
    repo_root = Path(memory_module.__file__).resolve().parent

    with pytest.raises(PathValidationError):
        MemoryLibrary(repo_root)
    with pytest.raises(PathValidationError):
        MemoryLibrary(repo_root / "unused-isolated-root")
    with pytest.raises(PathValidationError):
        MemoryLibrary(repo_root.parent)


@pytest.mark.parametrize(
    "marker",
    ["production", "prod", "deploy", ".runtime", "old-ombre", "old_ombre", "oldombre"],
)
def test_prohibited_root_marker_is_rejected(tmp_path: Path, marker: str) -> None:
    root = _isolated_root(tmp_path, f"safe-{marker}-root")

    with pytest.raises(PathValidationError):
        MemoryLibrary(root)


def test_existing_nonempty_root_requires_explicit_opt_in(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path)
    root.mkdir()
    marker = root / "owned-marker.txt"
    marker.write_text("test-owned", encoding="utf-8")

    with pytest.raises(PathValidationError):
        MemoryLibrary(root)

    validation = MemoryLibrary(root, allow_existing_nonempty=True).validate_paths()
    assert validation.root_nonempty is True
    assert marker.read_text(encoding="utf-8") == "test-owned"


@pytest.mark.parametrize("title", ["../../sibling", r"C:\absolute\target"])
def test_title_path_text_cannot_escape_or_touch_sibling(
    tmp_path: Path,
    title: str,
) -> None:
    root = _isolated_root(tmp_path, "library")
    sibling = _isolated_root(tmp_path, "library-sibling")
    sibling.mkdir()
    sentinel = sibling / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")

    record = MemoryLibrary(root).create(title, "Body", [])

    record_path = root / "buckets" / "dynamic" / "未分类" / f"{record.id}.md"
    assert record_path.is_file()
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert [path for path in sibling.rglob("*") if path.is_file()] == [sentinel]


def test_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path, "library")
    outside = _isolated_root(tmp_path, "outside")
    buckets = root / "buckets"
    buckets.mkdir(parents=True)
    outside.mkdir()
    link = buckets / "dynamic"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlink unavailable: {type(error).__name__}")

    with pytest.raises(PathValidationError):
        MemoryLibrary(root, allow_existing_nonempty=True)


def test_windows_junction_requires_separate_supported_harness() -> None:
    if os.name != "nt":
        pytest.skip("Windows junction behavior applies only on Windows")
    pytest.skip(
        "stdlib provides no safe unprivileged junction-creation API; "
        "a separately authorized Windows harness is required"
    )
