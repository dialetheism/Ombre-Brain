#!/usr/bin/env bash
set -uo pipefail
set +x

PROJECT_DIR="/srv/casper-ombre"
BUNDLE_DIR="${PROJECT_DIR}/casper-deploy"
CONFIG_FILE="${BUNDLE_DIR}/config/config.yaml"
COMPOSE_FILE="${BUNDLE_DIR}/compose.yaml"
MANIFEST_FILE="${BUNDLE_DIR}/manifest.yaml"
DATA_DIR="${PROJECT_DIR}/data"
STATE_DIR="${PROJECT_DIR}/state"
EXPECTED_SHA="284c9c7b0e51a0ba0032c7028f705d72458cb304"
EXPECTED_UID="10001"
EXPECTED_GID="10001"
GATEWAY_PORT="18202"
MIN_AVAILABLE_KIB=5242880
failures=0

pass() {
  printf '%s=True\n' "$1"
}

fail() {
  printf '%s=False\n' "$1"
  failures=$((failures + 1))
}

require_command() {
  if command -v "$2" >/dev/null 2>&1; then
    pass "$1"
  else
    fail "$1"
  fi
}

require_env() {
  local name="$1"
  if [[ -n "${!name-}" ]]; then
    printf 'ENV_%s=SET\n' "$name"
  else
    printf 'ENV_%s=MISSING\n' "$name"
    failures=$((failures + 1))
  fi
}

printf 'PREFLIGHT_MODE=READ_ONLY\n'
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  pass "RUNNING_AS_ROOT"
else
  fail "RUNNING_AS_ROOT"
fi

required_files=(
  "$COMPOSE_FILE"
  "$CONFIG_FILE"
  "$MANIFEST_FILE"
  "${BUNDLE_DIR}/Dockerfile.production"
  "${BUNDLE_DIR}/docs/DEPLOYMENT.md"
  "${BUNDLE_DIR}/docs/SECRET-INVENTORY.md"
  "${BUNDLE_DIR}/docs/ROLLBACK.md"
)
for path in "${required_files[@]}"; do
  if [[ -f "$path" && ! -L "$path" ]]; then
    pass "FILE_$(basename "$path" | tr '[:lower:].-' '[:upper:]__')_OK"
  else
    fail "FILE_$(basename "$path" | tr '[:lower:].-' '[:upper:]__')_OK"
  fi
done

require_command "DOCKER_AVAILABLE" docker
if docker compose version >/dev/null 2>&1; then
  pass "DOCKER_COMPOSE_AVAILABLE"
else
  fail "DOCKER_COMPOSE_AVAILABLE"
fi
if docker ps -aq >/dev/null 2>&1; then
  pass "DOCKER_DAEMON_READABLE"
else
  fail "DOCKER_DAEMON_READABLE"
fi
require_command "SS_AVAILABLE" ss
require_command "GIT_AVAILABLE" git

head_sha="$(GIT_OPTIONAL_LOCKS=0 git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || true)"
if [[ "$head_sha" == "$EXPECTED_SHA" ]]; then
  pass "SOURCE_SHA_OK"
else
  fail "SOURCE_SHA_OK"
fi

origin_url="$(GIT_OPTIONAL_LOCKS=0 git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || true)"
if [[ "$origin_url" == "https://github.com/Yinglianchun/Ombre-Brain.git" ]]; then
  pass "SOURCE_REMOTE_OK"
else
  fail "SOURCE_REMOTE_OK"
fi

tracked_status="$(GIT_OPTIONAL_LOCKS=0 git -C "$PROJECT_DIR" status --porcelain --untracked-files=no 2>/dev/null || true)"
if [[ -z "$tracked_status" ]]; then
  pass "TRACKED_SOURCE_CLEAN"
else
  fail "TRACKED_SOURCE_CLEAN"
fi

if grep -Fq 'upstream_model: "openai/gpt-5.4"' "$CONFIG_FILE" \
  && ! grep -Fq "CASPER_UPSTREAM_MODEL_REQUIRED" "$CONFIG_FILE"; then
  pass "UPSTREAM_MODEL_CONFIGURED"
else
  fail "UPSTREAM_MODEL_CONFIGURED"
fi

secret_env_file="${CASPER_SECRET_ENV_FILE:-/etc/casper-ombre/casper.env}"
if [[ -f "$secret_env_file" && ! -L "$secret_env_file" ]]; then
  secret_owner="$(stat -c '%u:%g' "$secret_env_file" 2>/dev/null || true)"
  secret_mode="$(stat -c '%a' "$secret_env_file" 2>/dev/null || true)"
  if [[ "$secret_owner" == "0:0" && "$secret_mode" == "600" ]]; then
    pass "SECRET_ENV_METADATA_OK"
  else
    fail "SECRET_ENV_METADATA_OK"
  fi
else
  fail "SECRET_ENV_METADATA_OK"
fi

required_env_names=(
  CASPER_OMBRE_GATEWAY_TOKEN
  CASPER_OPENROUTER_API_KEY
  CASPER_DEHYDRATION_API_KEY
  CASPER_DEHYDRATION_BASE_URL
  CASPER_DEHYDRATION_MODEL
  CASPER_EMBEDDING_API_KEY
  CASPER_EMBEDDING_BASE_URL
  CASPER_EMBEDDING_MODEL
  CASPER_PERSONA_API_KEY
  CASPER_PERSONA_BASE_URL
  CASPER_PERSONA_MODEL
)
for name in "${required_env_names[@]}"; do
  if [[ -n "${!name-}" ]]; then
    printf 'ENV_%s=SET\n' "$name"
  elif awk -v wanted="$name" '
    BEGIN { found = 0; seen = 0; invalid = 0 }
    /^[[:space:]]*($|#)/ { next }
    /^[A-Z][A-Z0-9_]*=[^\r\n]*$/ {
      pos = index($0, "=")
      key = substr($0, 1, pos - 1)
      value = substr($0, pos + 1)
      if (key == wanted) {
        seen += 1
        found = (length(value) > 0 && value !~ /[[:space:]]/) ? 1 : 0
      }
      next
    }
    { invalid = 1 }
    END { exit (found && seen == 1 && !invalid) ? 0 : 1 }
  ' "$secret_env_file" 2>/dev/null; then
    printf 'ENV_%s=SET\n' "$name"
  else
    printf 'ENV_%s=MISSING\n' "$name"
    failures=$((failures + 1))
  fi
done

untracked_outside_bundle=0
while IFS= read -r untracked_path; do
  [[ -z "$untracked_path" ]] && continue
  case "$untracked_path" in
    casper-deploy/*)
      ;;
    *)
      untracked_outside_bundle=1
      break
      ;;
  esac
done < <(GIT_OPTIONAL_LOCKS=0 git -C "$PROJECT_DIR" ls-files --others --exclude-standard 2>/dev/null || true)
if [[ "$untracked_outside_bundle" -eq 0 ]]; then
  pass "UNTRACKED_SOURCE_OUTSIDE_BUNDLE_ABSENT"
else
  fail "UNTRACKED_SOURCE_OUTSIDE_BUNDLE_ABSENT"
fi

untracked_build_input=0
build_input_patterns=(
  "*.py"
  "requirements.txt"
  "resources"
  "scripts"
  "dashboard.html"
  "dashboard_assets"
  "config.example.yaml"
)
for tracked_pattern in "${build_input_patterns[@]}"; do
  ignored_input="$(GIT_OPTIONAL_LOCKS=0 git -C "$PROJECT_DIR" ls-files --others --ignored --exclude-standard -- "$tracked_pattern" 2>/dev/null || true)"
  if [[ -n "$ignored_input" ]]; then
    untracked_build_input=1
    break
  fi
done
if [[ "$untracked_build_input" -eq 0 ]]; then
  pass "IGNORED_UNTRACKED_BUILD_INPUT_ABSENT"
else
  fail "IGNORED_UNTRACKED_BUILD_INPUT_ABSENT"
fi

for path in "$DATA_DIR" "$STATE_DIR"; do
  label="$(basename "$path" | tr '[:lower:]' '[:upper:]')"
  if [[ -d "$path" && ! -L "$path" ]]; then
    pass "${label}_DIR_EXISTS"
    owner_pair="$(stat -c '%u:%g' "$path" 2>/dev/null || true)"
    owner_mode="$(stat -c '%a' "$path" 2>/dev/null || true)"
    owner_digit="${owner_mode: -3:1}"
    if [[ "$owner_pair" == "${EXPECTED_UID}:${EXPECTED_GID}" ]]; then
      pass "${label}_DIR_OWNER_OK"
    else
      fail "${label}_DIR_OWNER_OK"
    fi
    if [[ "$owner_digit" =~ ^[2367]$ ]]; then
      pass "${label}_DIR_OWNER_WRITE_OK"
    else
      fail "${label}_DIR_OWNER_WRITE_OK"
    fi
  else
    fail "${label}_DIR_EXISTS"
    fail "${label}_DIR_OWNER_OK"
    fail "${label}_DIR_OWNER_WRITE_OK"
  fi
done

if [[ -e "${STATE_DIR}/config.runtime.yaml" ]]; then
  fail "FRESH_RUNTIME_OVERRIDE_ABSENT"
else
  pass "FRESH_RUNTIME_OVERRIDE_ABSENT"
fi

if ss -H -lnt 2>/dev/null | awk -v port=":${GATEWAY_PORT}" '$4 ~ port "$" {found=1} END {exit found ? 0 : 1}'; then
  fail "GATEWAY_PORT_FREE"
else
  pass "GATEWAY_PORT_FREE"
fi

docker_port_collision=0
docker_container_ids="$(docker ps -aq 2>/dev/null)"
docker_list_status=$?
if [[ "$docker_list_status" -eq 0 ]]; then
  while IFS= read -r container_id; do
    [[ -z "$container_id" ]] && continue
    bindings="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$container_id" 2>/dev/null || true)"
    if grep -Eq '"HostPort"[[:space:]]*:[[:space:]]*"18202"' <<<"$bindings"; then
      docker_port_collision=1
      break
    fi
  done <<<"$docker_container_ids"
else
  docker_port_collision=2
fi
if [[ "$docker_port_collision" -eq 0 ]]; then
  pass "GATEWAY_PORT_NOT_DOCKER_PUBLISHED"
else
  fail "GATEWAY_PORT_NOT_DOCKER_PUBLISHED"
fi

if grep -Rqs -- "18202" /etc/nginx /etc/systemd/system /lib/systemd/system /etc/cron.d 2>/dev/null; then
  fail "GATEWAY_PORT_NOT_REFERENCED"
else
  pass "GATEWAY_PORT_NOT_REFERENCED"
fi

if grep -Eq '(^|[^0-9])18080([^0-9]|$)|8000:8000|0\.0\.0\.0:18202' "$COMPOSE_FILE"; then
  fail "OLD_PORTS_UNTOUCHED_BY_COMPOSE"
else
  pass "OLD_PORTS_UNTOUCHED_BY_COMPOSE"
fi

if grep -Eiq 'p0luz/ombre-brain|ombre-brain:latest' "$COMPOSE_FILE" "${BUNDLE_DIR}/Dockerfile.production"; then
  fail "FORBIDDEN_OMBRE_IMAGE_ABSENT"
else
  pass "FORBIDDEN_OMBRE_IMAGE_ABSENT"
fi

mem_total_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || printf '0')"
if [[ "${mem_total_kib:-0}" -ge 1500000 ]]; then
  pass "RAM_BASELINE_OK"
else
  fail "RAM_BASELINE_OK"
fi

available_kib="$(df -Pk "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ "${available_kib:-0}" -ge "$MIN_AVAILABLE_KIB" ]]; then
  pass "DISK_BASELINE_OK"
else
  fail "DISK_BASELINE_OK"
fi

if find "$BUNDLE_DIR" -type f \( -name '.env' -o -name '*.token' -o -name '*.pem' -o -name '*.key' \) -print -quit | grep -q .; then
  fail "NO_SECRET_NAMED_FILE"
else
  pass "NO_SECRET_NAMED_FILE"
fi

secret_prefix_one='s''k-'
secret_prefix_two='ey''J'
if grep -ERq -- "BEGIN [A-Z ]*PRIVATE KEY|${secret_prefix_one}[A-Za-z0-9_-]{20,}|${secret_prefix_two}[A-Za-z0-9_-]{40,}" "$BUNDLE_DIR"; then
  fail "NO_SECRET_LIKE_CONTENT"
else
  pass "NO_SECRET_LIKE_CONTENT"
fi

if grep -Fq "$EXPECTED_SHA" "$COMPOSE_FILE"; then
  if grep -Fq "$EXPECTED_SHA" "$MANIFEST_FILE"; then
    if grep -Fq "$EXPECTED_SHA" "${BUNDLE_DIR}/Dockerfile.production"; then
      pass "SOURCE_SHA_CONSISTENT"
    else
      fail "SOURCE_SHA_CONSISTENT"
    fi
  else
    fail "SOURCE_SHA_CONSISTENT"
  fi
else
  fail "SOURCE_SHA_CONSISTENT"
fi

if [[ "$failures" -eq 0 ]]; then
  printf 'PREFLIGHT_RESULT=PASS\n'
  exit 0
fi

printf 'PREFLIGHT_RESULT=FAIL\n'
printf 'PREFLIGHT_FAILURE_COUNT=%d\n' "$failures"
exit 1
