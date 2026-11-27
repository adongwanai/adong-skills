#!/usr/bin/env bash
# adong-ai-daily · 多源新闻采集入口（兼容旧版调用，已脱离 ~/Downloads/a.sh）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DATE="${1:-$(TZ=Asia/Shanghai date +%Y-%m-%d)}"

python3 "${SCRIPT_DIR}/collect_sources.py" --date "${TARGET_DATE}" --print-brief
