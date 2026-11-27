#!/usr/bin/env bash
# adong-ai-daily · 自包含一键流水线入口
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET_DATE="$(TZ=Asia/Shanghai date +%Y-%m-%d)"
OUT_DIR=""
AUTO_RENDER=0
EXPORT_CARDS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) TARGET_DATE="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --auto) AUTO_RENDER=1; shift ;;
    --export-cards) EXPORT_CARDS=1; shift ;;
    *) shift ;;
  esac
done

CANDIDATES_JSON="${SKILL_ROOT}/cache/${TARGET_DATE}_candidates.json"

echo "🤖 阿东 AI 日报流水线 (${TARGET_DATE})"
echo "========================================"

python3 "${SCRIPT_DIR}/collect_sources.py" --date "${TARGET_DATE}" --out "${CANDIDATES_JSON}"

if [[ "${AUTO_RENDER}" -eq 1 ]]; then
  RENDER_ARGS=(--candidates "${CANDIDATES_JSON}" --auto)
  if [[ -n "${OUT_DIR}" ]]; then
    RENDER_ARGS+=(--out-dir "${OUT_DIR}")
  fi
  python3 "${SCRIPT_DIR}/render_report.py" "${RENDER_ARGS[@]}"
  if [[ "${EXPORT_CARDS}" -eq 1 ]]; then
    HTML_OUT="$(python3 -c 'import json, pathlib; idx=json.loads(pathlib.Path(r"'"${SKILL_ROOT}"'/cache/ledger_index.json").read_text()); print(idx["days"][0]["html_path"])')"
    python3 "${SCRIPT_DIR}/export_cards.py" --html "${HTML_OUT}"
  fi
else
  echo "✅ 候选事件池已就绪: ${CANDIDATES_JSON}"
  echo "👉 下一步：由 Agent 按 references/ledger_schema.md 生成 curated.json 后调用 render_report.py 产出 HTML 与社群转发版。"
fi
