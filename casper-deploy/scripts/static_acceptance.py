#!/usr/bin/env python3
"""C2 secret-safe static validator with no third-party dependencies.

The YAML reader intentionally supports only the conservative subset used by
this bundle. Unsupported YAML syntax is rejected rather than guessed.
"""

from __future__ import annotations

import json
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_SHA = "284c9c7b0e51a0ba0032c7028f705d72458cb304"
EXPECTED_RIKKAHUB_SHA = "8dc3ebce3f422a422013097447234e4a97db4210"
ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "casper-deploy"


class YamlSubsetError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    indent: int
    text: str
    line: int


def _strip_comment(raw: str) -> str:
    quote = ""
    escaped = False
    depth = 0
    for index, char in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "[{":
            depth += 1
            continue
        if char in "]}":
            depth -= 1
            if depth < 0:
                raise YamlSubsetError("unbalanced inline collection")
            continue
        if char == "#" and depth == 0 and (index == 0 or raw[index - 1].isspace()):
            return raw[:index].rstrip()
    if quote or depth != 0:
        raise YamlSubsetError("unterminated quote or inline collection")
    return raw.rstrip()


def _split_key_value(text: str) -> tuple[str, str] | None:
    quote = ""
    escaped = False
    depth = 0
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char in "[{":
            depth += 1
            continue
        if char in "]}":
            depth -= 1
            continue
        if char == ":" and depth == 0:
            key = text[:index].strip()
            value = text[index + 1 :].strip()
            if not key:
                raise YamlSubsetError("empty mapping key")
            return key, value
    return None


def _parse_scalar(text: str) -> Any:
    if text == "":
        raise YamlSubsetError("missing scalar")
    if text.startswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError("invalid double-quoted scalar") from exc
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'"):
            raise YamlSubsetError("invalid single-quoted scalar")
        return text[1:-1].replace("''", "'")
    if text.startswith("[") or text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError("inline collections must be JSON-compatible") from exc
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?(0|[1-9][0-9]*)", text):
        return int(text)
    if re.fullmatch(r"-?(0|[1-9][0-9]*)\.[0-9]+", text):
        return float(text)
    if any(marker in text for marker in ("&", "*", "!", "|", ">")):
        raise YamlSubsetError("unsupported YAML feature")
    return text


class RestrictedYaml:
    def __init__(self, text: str) -> None:
        self.tokens: list[Token] = []
        for line_number, raw in enumerate(text.splitlines(), start=1):
            if "\t" in raw:
                raise YamlSubsetError("tabs are forbidden")
            cleaned = _strip_comment(raw)
            if not cleaned.strip():
                continue
            indent = len(cleaned) - len(cleaned.lstrip(" "))
            if indent % 2:
                raise YamlSubsetError("indentation must use two-space levels")
            self.tokens.append(Token(indent, cleaned.strip(), line_number))

    def parse(self) -> Any:
        if not self.tokens:
            raise YamlSubsetError("empty document")
        value, index = self._parse_block(0, self.tokens[0].indent)
        if index != len(self.tokens):
            raise YamlSubsetError("trailing unparsed content")
        return value

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        token = self.tokens[index]
        if token.indent != indent:
            raise YamlSubsetError("unexpected indentation")
        if token.text == "-" or token.text.startswith("- "):
            return self._parse_list(index, indent)
        return self._parse_mapping(index, indent)

    def _parse_value(self, value_text: str, index: int, indent: int) -> tuple[Any, int]:
        if value_text:
            return _parse_scalar(value_text), index
        if index >= len(self.tokens) or self.tokens[index].indent != indent + 2:
            raise YamlSubsetError("mapping value requires one nested block")
        return self._parse_block(index, indent + 2)

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(self.tokens):
            token = self.tokens[index]
            if token.indent < indent:
                break
            if token.indent > indent:
                raise YamlSubsetError("unexpected mapping indentation")
            if token.text == "-" or token.text.startswith("- "):
                break
            split = _split_key_value(token.text)
            if split is None:
                raise YamlSubsetError("mapping entry lacks colon")
            key, value_text = split
            if key in result:
                raise YamlSubsetError("duplicate mapping key")
            index += 1
            value, index = self._parse_value(value_text, index, indent)
            result[key] = value
        return result, index

    def _parse_list(self, index: int, indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(self.tokens):
            token = self.tokens[index]
            if token.indent < indent:
                break
            if token.indent != indent or not (
                token.text == "-" or token.text.startswith("- ")
            ):
                break
            body = token.text[1:].strip()
            index += 1
            if not body:
                if index >= len(self.tokens) or self.tokens[index].indent != indent + 2:
                    raise YamlSubsetError("list item requires one nested block")
                value, index = self._parse_block(index, indent + 2)
                result.append(value)
                continue
            first = _split_key_value(body)
            if first is None:
                result.append(_parse_scalar(body))
                continue
            item: dict[str, Any] = {}
            key, value_text = first
            value, index = self._parse_value(value_text, index, indent)
            item[key] = value
            while index < len(self.tokens):
                next_token = self.tokens[index]
                if next_token.indent <= indent:
                    break
                if next_token.indent != indent + 2:
                    raise YamlSubsetError("unexpected list mapping indentation")
                if next_token.text == "-" or next_token.text.startswith("- "):
                    raise YamlSubsetError("unexpected nested sequence")
                split = _split_key_value(next_token.text)
                if split is None:
                    raise YamlSubsetError("mapping entry lacks colon")
                child_key, child_value_text = split
                if child_key in item:
                    raise YamlSubsetError("duplicate list mapping key")
                index += 1
                child_value, index = self._parse_value(
                    child_value_text, index, indent + 2
                )
                item[child_key] = child_value
            result.append(item)
        return result, index


def load_yaml(path: Path) -> Any:
    return RestrictedYaml(path.read_text(encoding="utf-8")).parse()


def mount_map(service: dict[str, Any]) -> dict[str, str]:
    mounts: dict[str, str] = {}
    for item in service.get("volumes", []):
        if not isinstance(item, dict):
            raise AssertionError("non-mapping volume")
        mounts[str(item.get("target"))] = str(item.get("source"))
    return mounts


def all_files() -> list[Path]:
    return sorted(path for path in BUNDLE.rglob("*") if path.is_file())


def secret_scan_ok() -> bool:
    forbidden_names = {".env"}
    forbidden_suffixes = {".token", ".pem", ".key", ".p12", ".pfx"}
    secret_patterns = [
        re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
        re.compile(r"s" + r"k-[A-Za-z0-9_-]{20,}"),
        re.compile(r"ey" + r"J[A-Za-z0-9_-]{40,}"),
    ]
    for path in all_files():
        if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            return False
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in secret_patterns):
            return False
    example = (BUNDLE / "env" / "casper.env.example").read_text(encoding="utf-8")
    for raw in example.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line or line.split("=", 1)[1] != "":
            return False
    return True


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if "\x00" in text or "GIT binary patch" in text:
        raise AssertionError("unsupported patch content")
    headers = re.findall(
        r"^diff --git a/([^\s]+) b/([^\s]+)$", text, flags=re.MULTILINE
    )
    if not headers or "@@ " not in text:
        raise AssertionError("patch lacks unified diff structure")
    if any(left != right for left, right in headers):
        raise AssertionError("patch renames are not permitted")
    targets = [left for left, _ in headers]
    minus = re.findall(r"^--- (\S+)$", text, flags=re.MULTILINE)
    plus = re.findall(r"^\+\+\+ (\S+)$", text, flags=re.MULTILINE)
    header_pairs_valid = len(minus) == len(targets) == len(plus) and all(
        old in {"/dev/null", f"a/{target}"} and new == f"b/{target}"
        for target, old, new in zip(targets, minus, plus, strict=True)
    )
    if not header_pairs_valid or len(set(targets)) != len(targets):
        raise AssertionError("patch target headers are inconsistent")
    return targets


def validate() -> dict[str, bool]:
    compose = load_yaml(BUNDLE / "compose.yaml")
    config = load_yaml(BUNDLE / "config" / "config.yaml")
    manifest = load_yaml(BUNDLE / "manifest.yaml")
    patch_manifest = load_yaml(BUNDLE / "patches" / "PATCH-MANIFEST.yaml")
    services = compose["services"]
    brain = services["casper-ombre-brain"]
    gateway = services["casper-ombre-gateway"]
    brain_mounts = mount_map(brain)
    gateway_mounts = mount_map(gateway)

    env_names = {
        line.split("=", 1)[0]
        for line in (BUNDLE / "env" / "casper.env.example")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    compose_text = (BUNDLE / "compose.yaml").read_text(encoding="utf-8")
    referenced_env = set(
        re.findall(r"\$\{([A-Z][A-Z0-9_]*)(?::[^}]*)?\}", compose_text)
    )

    upstream = config["gateway"]["upstreams"][0]
    required_mounts = {
        "/data": "/srv/casper-ombre/data",
        "/state": "/srv/casper-ombre/state",
    }
    dockerfile = (BUNDLE / "Dockerfile.production").read_text(encoding="utf-8")
    preflight = (BUNDLE / "scripts" / "preflight.sh").read_text(encoding="utf-8")
    runtime_texts = "\n".join(
        [
            compose_text,
            (BUNDLE / "config" / "config.yaml").read_text(encoding="utf-8"),
        ]
    ).lower()
    patch_entries = {
        entry["name"]: entry for entry in patch_manifest.get("patches", [])
    }
    rikkahub_patch = patch_entries["rikkahub-conversation-session-header"]
    ombre_patch = patch_entries["ombre-disable-auto-resolve"]
    packaging_patch = patch_entries["rikkahub-casper-production-packaging"]
    reproducibility_patch = patch_entries["rikkahub-casper-build-reproducibility"]
    rikkahub_patch_path = BUNDLE / "patches" / rikkahub_patch["file"]
    ombre_patch_path = BUNDLE / "patches" / ombre_patch["file"]
    packaging_patch_path = BUNDLE / "patches" / packaging_patch["file"]
    reproducibility_patch_path = (
        BUNDLE / "patches" / reproducibility_patch["file"]
    )
    expected_rikkahub_targets = [
        "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt",
        "app/src/main/java/me/rerere/rikkahub/service/ChatService.kt",
    ]
    expected_ombre_targets = ["config.example.yaml", "decay_engine.py", "utils.py"]
    expected_packaging_targets = [
        "app/build.gradle.kts",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/java/me/rerere/rikkahub/data/ai/mcp/McpOAuthCallback.kt",
        "app/src/main/java/me/rerere/rikkahub/di/AppModule.kt",
        "app/src/main/java/me/rerere/rikkahub/di/ViewModelModule.kt",
        "app/src/main/java/me/rerere/rikkahub/ui/pages/chat/ChatVM.kt",
        "app/src/main/res/xml/shortcuts.xml",
    ]
    expected_reproducibility_targets = [
        "ai/gradle.lockfile",
        "app/gradle.lockfile",
        "build.gradle.kts",
        "common/gradle.lockfile",
        "document/gradle.lockfile",
        "gradle/libs.versions.toml",
        "gradle/verification-metadata.xml",
        "gradle/wrapper/gradle-wrapper.properties",
        "highlight/gradle.lockfile",
        "material3/gradle.lockfile",
        "search/gradle.lockfile",
        "settings-gradle.lockfile",
        "settings.gradle.kts",
        "speech/gradle.lockfile",
        "web-ui/.npmrc",
        "web-ui/package.json",
        "web-ui/pnpm-lock.yaml",
        "web/gradle.lockfile",
        "workspace/gradle.lockfile",
    ]

    checks = {
        "YAML_PARSE": True,
        "PROJECT_NAME": compose.get("name") == "casper-ombre",
        "SERVICE_SET": set(services) == {
            "casper-ombre-brain",
            "casper-ombre-gateway",
        },
        "CONTAINER_NAMES": brain.get("container_name") == "casper-ombre-brain"
        and gateway.get("container_name") == "casper-ombre-gateway",
        "NETWORK_NAME": compose["networks"]["casper-ombre-net"]["name"]
        == "casper-ombre-net",
        "SERVICE_NETWORK_ISOLATION": brain.get("networks") == ["casper-ombre-net"]
        and gateway.get("networks") == ["casper-ombre-net"],
        "SOURCE_BUILD_SHARED": brain.get("image") == gateway.get("image")
        and brain.get("build") == gateway.get("build"),
        "COMMANDS": brain.get("command") == ["python", "server.py"]
        and gateway.get("command") == ["python", "gateway.py"],
        "SHARED_DATA": all(
            mount_map(service).get("/data") == required_mounts["/data"]
            for service in (brain, gateway)
        ),
        "SHARED_STATE": all(
            mount_map(service).get("/state") == required_mounts["/state"]
            for service in (brain, gateway)
        ),
        "MOUNT_SETS_EQUAL": brain_mounts == gateway_mounts,
        "BRAIN_NOT_PUBLISHED": "ports" not in brain,
        "GATEWAY_LOOPBACK_BIND": gateway.get("ports")
        == ["127.0.0.1:18202:8010"],
        "NO_SWARM_RESOURCE_ILLUSION": all(
            "deploy" not in service for service in (brain, gateway)
        ),
        "SERVICE_RESOURCE_LIMITS": brain.get("mem_limit") == "384m"
        and gateway.get("mem_limit") == "512m"
        and brain.get("pids_limit") == 128
        and gateway.get("pids_limit") == 128,
        "HEALTHCHECKS": "'127.0.0.1', 8000"
        in " ".join(str(item) for item in brain["healthcheck"]["test"])
        and "'127.0.0.1', 8010"
        in " ".join(str(item) for item in gateway["healthcheck"]["test"])
        and "HTTPConnection" in " ".join(
            str(item)
            for service in (brain, gateway)
            for item in service["healthcheck"]["test"]
        )
        and "/mcp" not in " ".join(
            str(item)
            for service in (brain, gateway)
            for item in service["healthcheck"]["test"]
        ),
        "TRANSPORT": config.get("transport") == "streamable-http",
        "UPSTREAM_PROTOCOL": upstream.get("protocol") == "openai",
        "UPSTREAM_BASE_URL": upstream.get("base_url")
        == "https://openrouter.ai/api/v1",
        "MODEL_FROZEN": upstream["models"][0]["upstream_model"]
        == "openai/gpt-5.4"
        and manifest["upstream"]["actual_model"] == "openai/gpt-5.4"
        and manifest["upstream"]["model_status"] == "FROZEN"
        and manifest["upstream"]["model_frozen"] is True,
        "MODEL_ALIAS": upstream["models"][0]["id"] == "casper-gpt-5.4",
        "UPSTREAM_KEY_ENV": upstream.get("api_key_env")
        == "CASPER_OPENROUTER_API_KEY",
        "PROMPT_CACHE_POLICY": upstream.get("prompt_cache") == "openai"
        and "prompt_cache_retention" not in upstream
        and manifest["policy"]["prompt_cache_key_session_bound"] is True
        and manifest["policy"]["explicit_cache_breakpoints"] is False
        and manifest["policy"]["explicit_cache_ttl"] is False,
        "SESSION_SENTINEL": config["gateway"]["default_session_id"]
        == "__MISSING_X_OMBRE_SESSION_ID__",
        "SESSION_BLOCKER_FAIL_CLOSED": manifest["client_audit"]["repository"]
        == "https://github.com/rikkahub/rikkahub.git"
        and manifest["client_audit"]["sha"]
        == "8dc3ebce3f422a422013097447234e4a97db4210"
        and manifest["client_audit"]["static_custom_header_supported"] is True
        and manifest["client_audit"]["dynamic_ombre_session_header"]
        == "UNSUPPORTED"
        and manifest["client_audit"]["conversation_id_available_to_request_layer"]
        is False
        and manifest["client_audit"]["session_patch_designed"] is True
        and manifest["client_audit"]["session_patch_runtime_validated"] is True
        and manifest["client_audit"]["patch_exact_apply_validated"] is True
        and manifest["client_audit"]["patch_dataflow_validated"] is True
        and manifest["client_audit"]["patch_build_validated"] is True
        and manifest["client_audit"]["header_template_tests"]
        == "PASS_10_OF_10"
        and manifest["client_audit"]["kotlin_compile_validation"]
        == "PASS"
        and manifest["client_audit"]["debug_apk_build"]
        == "PASS"
        and manifest["client_audit"]["private_device_runtime_validation"]
        == "PASS_C2D2B"
        and manifest["client_audit"]["same_conversation_multiround_stable"] is True
        and manifest["client_audit"]["different_conversations_isolated"] is True
        and manifest["client_audit"]["app_restart_session_persistent"] is True
        and manifest["client_audit"]["fast_sequential_switch_isolated"] is True
        and manifest["client_audit"]["no_session_header_absent"] is True
        and manifest["client_audit"]["static_header_regression_pass"] is True
        and manifest["client_audit"]["build_toolchain_blocker"]
        == "NONE"
        and manifest["client_audit"]["portable_launcher_java_version"]
        == "17.0.20"
        and manifest["client_audit"]["gradle_daemon_java_version"]
        == "21.0.10"
        and manifest["client_audit"]["java_kotlin_bytecode_target"] == 17
        and manifest["client_audit"]["debug_apk_application_id"]
        == "me.rerere.rikkahub.debug"
        and manifest["client_audit"]["release_application_id"]
        == "me.rerere.rikkahub"
        and manifest["client_audit"]["debug_apk_parallel_install_expected"] is True
        and re.fullmatch(
            r"[0-9a-f]{64}", manifest["client_audit"]["debug_apk_sha256"]
        )
        and manifest["client_audit"]["production_client_ready"] is False
        and manifest["client_audit"]["production_packaging_blocked"] is False,
        "PRODUCTION_CLIENT_PACKAGING": manifest["client_audit"]
        ["official_application_id"]
        == "me.rerere.rikkahub"
        and manifest["client_audit"]["production_application_id"]
        == "me.rerere.rikkahub.casper"
        and manifest["client_audit"]["production_display_name"]
        == "RikkaHub Casper"
        and manifest["client_audit"]["production_private_uri_scheme"]
        == "rikkahub-casper"
        and manifest["client_audit"]["production_application_id_collision_free"]
        is True
        and manifest["client_audit"]
        ["parallel_install_with_official_supported_by_design"]
        is True
        and manifest["client_audit"]["packaging_strategy"]
        == "EXISTING_RELEASE_VARIANT_WITH_DEDICATED_BUILD_CONFIGURATION_PATCH"
        and manifest["client_audit"]["packaging_patch_required"] is True
        and manifest["client_audit"]["packaging_patch_created"] is True
        and manifest["client_audit"]["packaging_patch_sha256"]
        == "af02a95fe468ef592c63601964b98ca3dd11bb43c627d594b76e8c4828eedaf2"
        and manifest["client_audit"]["packaging_patch_exact_apply"] is True
        and manifest["client_audit"]["packaging_patch_offset_count"] == 0
        and manifest["client_audit"]["packaging_patch_fuzz_count"] == 0
        and manifest["client_audit"]["packaging_patch_changed_file_count"] == 7
        and manifest["client_audit"]["packaging_gradle_configuration_parsed"]
        is True
        and manifest["client_audit"]["packaging_release_compile"]
        == "PASS_STRICT_LOCKED_CLEAN_COPY"
        and manifest["client_audit"]["production_release_resource_merge"]
        == "PASS"
        and manifest["client_audit"]["production_release_manifest_merge"]
        == "PASS"
        and manifest["client_audit"]["unsigned_release_apk_created"] is True
        and re.fullmatch(
            r"[0-9a-f]{64}",
            manifest["client_audit"]["unsigned_release_arm64_apk_sha256"],
        )
        and manifest["client_audit"]["signing_gate_reached_cleanly"] is True
        and manifest["client_audit"]["production_build_and_signing_pending"]
        is True
        and manifest["client_audit"]["real_keystore_created"] is False
        and manifest["client_audit"]["signing_secret_in_git"] is False
        and manifest["client_audit"]["firebase_core_chat_required"] is False
        and manifest["client_audit"]["firebase_placeholder_production_acceptable"]
        is False
        and manifest["client_audit"]["firebase_blocker_resolved"] is True
        and manifest["client_audit"]["firebase_analytics_present_in_casper_build"]
        is False
        and manifest["client_audit"]["firebase_crashlytics_present_in_casper_build"]
        is False
        and manifest["client_audit"]["google_services_project_required"] is False
        and manifest["client_audit"]["official_private_db_copy_required"] is False
        and manifest["client_audit"]
        ["session_patch_production_variant_compatible_by_design"]
        is True
        and manifest["client_audit"]["patch_rebase_required_on_upstream_change"]
        is True
        and manifest["client_audit"]["silent_fuzzy_patch_allowed"] is False
        and manifest["client_audit"]["dependency_lock_status"] == "LOCKED_STRICT"
        and manifest["client_audit"]["dependency_lock_file_count"] == 11
        and manifest["client_audit"]["unlocked_production_configuration_count"]
        == 0
        and manifest["client_audit"]["dynamic_dependency_count_before"] == 46
        and manifest["client_audit"]["dynamic_dependency_count"] == 0
        and manifest["client_audit"]["reproducible_build_blocker_resolved"]
        is True,
        "SESSION_PATCH_DESIGNED": manifest["policy"]["rikkahub_session_patch_designed"]
        is True
        and manifest["policy"]["rikkahub_session_patch_runtime_validated"] is True
        and manifest["policy"]["rikkahub_session_blocker_resolved"] is True
        and manifest["policy"]["production_patched_rikkahub_client_ready"] is False
        and manifest["policy"]["rikkahub_patch_exact_apply_validated"] is True
        and manifest["policy"]["rikkahub_patch_dataflow_validated"] is True
        and manifest["policy"]["rikkahub_patch_build_validated"] is True
        and manifest["policy"]["rikkahub_dynamic_header_template"]
        == "{{conversation_id}}"
        and manifest["policy"]["just_now_cross_session"]
        == "KEEP_PROFILE_GLOBAL_RECENT_CONTINUITY"
        and manifest["policy"]["just_now_window_hours"]
        == config["gateway"]["just_now_context_hours"]
        and manifest["policy"]["just_now_max_candidates"]
        == config["gateway"]["just_now_context_max_turns"] * 4
        and manifest["policy"]["just_now_max_injected"]
        == config["gateway"]["just_now_context_max_turns"]
        and manifest["policy"]["just_now_budget"]
        == config["gateway"]["just_now_context_budget"],
        "AUTO_MEMORY_OFF": config["reflection"]["daily_chat_memory_mode"] == "off",
        "DERIVED_FEATURES_CONSERVATIVE": all(
            value is False
            for value in (
                config["reflection"]["enabled"],
                config["reflection"]["auto_enabled"],
                config["reflection"]["daily_enabled"],
                config["portrait"]["auto_enabled"],
                config["portrait"]["auto_initial_enabled"],
                config["portrait"]["daily_enabled"],
                config["dream"]["enabled"],
                config["dream"]["auto_enabled"],
            )
        )
        and config["portrait"]["enabled"] is True,
        "PERSONA_MINIMAL": config["persona"]["enabled"] is True
        and config["persona"]["event_recording_enabled"] is False
        and config["persona"]["conflict_nudge_enabled"] is False
        and config["gateway"]["date_persona_trace_enabled"] is False
        and config["gateway"]["portrait_memory_enabled"] is False,
        "HELPER_EXTRA_CALLS_OFF": config["gateway"]["domain_sentinel_enabled"]
        is False
        and config["gateway"]["query_planner_enabled"] is False,
        "RAW_EVENTS_PATH": config["raw_events"]["db_path"]
        == "/state/raw_events.sqlite",
        "DECAY_CONSERVATIVE_CONFIG": config["decay"]["lambda"] == 0.0
        and config["decay"]["threshold"] == 0.0
        and config["decay"]["auto_resolve_enabled"] is False
        and manifest["policy"]["decay_auto_resolve_enabled"] is False
        and manifest["policy"]["decay_auto_resolve_upstream_default"] is True
        and manifest["policy"]["decay_auto_resolve_patch_designed"] is True
        and manifest["policy"]["decay_auto_resolve_runtime_validated"] is True
        and manifest["policy"]["decay_auto_resolve_status"]
        == "AUTO_RESOLVE_RUNTIME_FIXTURE_VALIDATED"
        and manifest["policy"]["decay_auto_resolve_blocker_resolved"] is True
        and manifest["policy"]["decay_archive_disabled_by_threshold_zero"] is True
        and manifest["policy"]["decay_lambda_zero_age_invariant"] is False
        and manifest["policy"]["decay_scoring_semantics_unchanged"] is True
        and manifest["policy"]["decay_archive_semantics_unchanged"] is True
        and manifest["policy"]["decay_freshness_time_weight_age_sensitive"]
        is True
        and manifest["policy"]["freshness_policy"]
        == "ACCEPT_RECENCY_RANKING_WITH_NO_DESTRUCTIVE_MEMORY_MUTATION"
        and manifest["policy"]["freshness_policy_blocker_resolved"] is True
        and manifest["policy"]["automatic_decay_effectively_disabled"] is False,
        "PATCH_MANIFEST": patch_manifest["ombre_upstream_sha"] == EXPECTED_SHA
        and patch_manifest["rikkahub_upstream_sha"] == EXPECTED_RIKKAHUB_SHA
        and patch_manifest["application_strategy"]
        == "CLEAN_FROZEN_CHECKOUT_VERIFY_APPLY_INDEX_BUILD"
        and patch_manifest["apply_failure_policy"] == "HARD_FAIL"
        and patch_manifest["offset_or_fuzz_policy"] == "REJECT"
        and patch_manifest["rikkahub_build_validation"]["patch_unchanged"] is True
        and patch_manifest["rikkahub_build_validation"]["launcher_java_version"]
        == "17.0.20"
        and patch_manifest["rikkahub_build_validation"]["gradle_daemon_java_version"]
        == "21.0.10"
        and patch_manifest["rikkahub_build_validation"]["java_kotlin_bytecode_target"]
        == 17
        and patch_manifest["rikkahub_build_validation"]["header_template_tests"]
        == "PASS_10_OF_10"
        and patch_manifest["rikkahub_build_validation"]["kotlin_compile"] == "PASS"
        and patch_manifest["rikkahub_build_validation"]["debug_apk_build"] == "PASS"
        and patch_manifest["rikkahub_build_validation"]["device_runtime_validation"]
        == "PASS_C2D2B"
        and patch_manifest["rikkahub_production_packaging_validation"]
        ["production_application_id"]
        == "me.rerere.rikkahub.casper"
        and patch_manifest["rikkahub_production_packaging_validation"]
        ["patch_check"]
        == "PASS_EXACT"
        and patch_manifest["rikkahub_production_packaging_validation"]
        ["patch_offset_count"]
        == 0
        and patch_manifest["rikkahub_production_packaging_validation"]
        ["patch_fuzz_count"]
        == 0
        and patch_manifest["rikkahub_reproducibility_validation"]["patch_check"]
        == "PASS_EXACT"
        and patch_manifest["rikkahub_reproducibility_validation"]
        ["patch_offset_count"]
        == 0
        and patch_manifest["rikkahub_reproducibility_validation"]
        ["patch_fuzz_count"]
        == 0
        and patch_manifest["rikkahub_reproducibility_validation"]
        ["dependency_locking"]
        == "STRICT"
        and patch_manifest["rikkahub_reproducibility_validation"]
        ["dynamic_dependency_count_after"]
        == 0
        and patch_manifest["rikkahub_reproducibility_validation"]
        ["strict_release_package"]
        == "PASS"
        and set(patch_entries)
        == {
            "rikkahub-conversation-session-header",
            "ombre-disable-auto-resolve",
            "rikkahub-casper-production-packaging",
            "rikkahub-casper-build-reproducibility",
        },
        "PATCH_SHA256": sha256_file(rikkahub_patch_path)
        == rikkahub_patch["sha256"]
        and sha256_file(ombre_patch_path) == ombre_patch["sha256"]
        and sha256_file(packaging_patch_path) == packaging_patch["sha256"]
        and sha256_file(reproducibility_patch_path)
        == reproducibility_patch["sha256"],
        "PATCH_TARGETS": patch_targets(rikkahub_patch_path)
        == expected_rikkahub_targets
        and rikkahub_patch["expected_files"] == expected_rikkahub_targets
        and patch_targets(ombre_patch_path) == expected_ombre_targets
        and ombre_patch["expected_files"] == expected_ombre_targets
        and patch_targets(packaging_patch_path) == expected_packaging_targets
        and packaging_patch["expected_files"] == expected_packaging_targets
        and patch_targets(reproducibility_patch_path)
        == expected_reproducibility_targets
        and reproducibility_patch["expected_files"]
        == expected_reproducibility_targets,
        "PATCH_SOURCE_ASSOCIATION": rikkahub_patch["upstream_sha"]
        == EXPECTED_RIKKAHUB_SHA
        and rikkahub_patch["target"] == "rikkahub"
        and ombre_patch["upstream_sha"] == EXPECTED_SHA
        and ombre_patch["target"] == "ombre"
        and packaging_patch["upstream_sha"] == EXPECTED_RIKKAHUB_SHA
        and packaging_patch["target"] == "rikkahub"
        and reproducibility_patch["upstream_sha"] == EXPECTED_RIKKAHUB_SHA
        and reproducibility_patch["target"] == "rikkahub",
        "PATCH_POST_APPLY_DIGEST_SET": [
            item["path"] for item in rikkahub_patch["expected_post_apply"]
        ]
        == expected_rikkahub_targets
        and [item["path"] for item in ombre_patch["expected_post_apply"]]
        == expected_ombre_targets
        and [item["path"] for item in packaging_patch["expected_post_apply"]]
        == expected_packaging_targets
        and [
            item["path"]
            for item in reproducibility_patch["expected_post_apply"]
        ]
        == expected_reproducibility_targets
        and all(
            re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            for entry in (
                rikkahub_patch,
                ombre_patch,
                packaging_patch,
                reproducibility_patch,
            )
            for item in entry["expected_post_apply"]
        ),
        "C2C_RECORDED_RESULTS": manifest["c2c_validation"]
        ["temporary_sources_outside_main_repository"]
        is True
        and manifest["c2c_validation"]["rikkahub_patch_check"]
        == "PASS_EXACT"
        and manifest["c2c_validation"]["rikkahub_patch_offset_count"] == 0
        and manifest["c2c_validation"]["rikkahub_patch_fuzz_count"] == 0
        and manifest["c2c_validation"]["rikkahub_changed_file_count"] == 2
        and manifest["c2c_validation"]["rikkahub_header_template_tests"]
        == "PASS_10_OF_10"
        and manifest["c2c_validation"]["rikkahub_header_template_test_failures"]
        == 0
        and manifest["c2c_validation"]["rikkahub_kotlin_compile"]
        == "PASS"
        and manifest["c2c_validation"]["rikkahub_debug_apk_build"]
        == "PASS"
        and manifest["c2c_validation"]["ombre_patch_check"] == "PASS_EXACT"
        and manifest["c2c_validation"]["ombre_patch_offset_count"] == 0
        and manifest["c2c_validation"]["ombre_patch_fuzz_count"] == 0
        and manifest["c2c_validation"]["ombre_decay_fixture"] == "PASS"
        and all(
            manifest["c2c_validation"][key] is True
            for key in (
                "decay_case_d1_auto_resolve_disabled",
                "decay_case_d2_upstream_behavior_preserved",
                "decay_case_d3_importance5_protected",
                "decay_case_d4_permanent_protected",
                "decay_case_d5_pinned_protected",
                "decay_case_d6_manual_resolve_preserved",
                "decay_case_d7_raw_events_unaffected",
            )
        ),
        "PATCH_DESIGN_DOC": (
            BUNDLE / "docs" / "RIKKAHUB-SESSION-PATCH.md"
        ).is_file()
        and (BUNDLE / "docs" / "RIKKAHUB-PRODUCTION-CLIENT.md").is_file(),
        "ENV_REFERENCES_DECLARED": referenced_env <= env_names,
        "NO_FORBIDDEN_IMAGE": "p0luz/ombre-brain" not in runtime_texts
        and "ombre-brain:latest" not in runtime_texts,
        "NO_OLD_RUNTIME_NAMESPACE": "/opt/ombre-brain" not in runtime_texts
        and "xiaoyu-main" not in runtime_texts
        and "18080" not in runtime_texts,
        "SHA_CONSISTENCY": all(
            EXPECTED_SHA in path.read_text(encoding="utf-8")
            for path in (
                BUNDLE / "compose.yaml",
                BUNDLE / "manifest.yaml",
                BUNDLE / "Dockerfile.production",
            )
        )
        and manifest["source"]["sha"] == EXPECTED_SHA,
        "DOCKERFILE_STATIC": "VOLUME " not in dockerfile
        and "USER 10001:10001" in dockerfile
        and "curl " not in dockerfile
        and "wget " not in dockerfile,
        "PREFLIGHT_STRUCTURE": " +  " not in preflight
        and "required_files=(" in preflight
        and "required_env_names=(" in preflight
        and "UNTRACKED_SOURCE_OUTSIDE_BUNDLE_ABSENT" in preflight
        and "awk -v wanted=" in preflight
        and "DOCKER_DAEMON_READABLE" in preflight
        and "RUNNING_AS_ROOT" in preflight,
        "NO_LOCAL_LARGE_MODEL": config["embedding"]["model"]
        == "CASPER_EMBEDDING_MODEL_REQUIRED"
        and config["reranker"]["enabled"] is False
        and "transformers" not in dockerfile.lower()
        and "torch" not in dockerfile.lower(),
        "SECRET_SCAN": secret_scan_ok(),
    }
    return checks


def main() -> int:
    try:
        checks = validate()
    except (AssertionError, KeyError, OSError, YamlSubsetError, TypeError, ValueError):
        print("STATIC_ACCEPTANCE_RESULT=FAIL")
        print("STATIC_ACCEPTANCE_ERROR_CLASS=STRUCTURE_OR_PARSE_ERROR")
        return 1
    for name, passed in checks.items():
        print(f"{name}={'PASS' if passed else 'FAIL'}")
    failures = [name for name, passed in checks.items() if not passed]
    print(f"STATIC_ACCEPTANCE_FAILURE_COUNT={len(failures)}")
    print(f"STATIC_ACCEPTANCE_RESULT={'PASS' if not failures else 'FAIL'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
