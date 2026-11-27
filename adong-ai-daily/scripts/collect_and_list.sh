#!/usr/bin/env bash
# adong-ai-daily · 采集并输出高信噪比候选清单（修复旧版单引号 heredoc ${DATE} 未展开 Bug）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DATE="${1:-$(TZ=Asia/Shanghai date +%Y-%m-%d)}"

python3 "${SCRIPT_DIR}/collect_sources.py" --date "${TARGET_DATE}" --dump-for-agent
