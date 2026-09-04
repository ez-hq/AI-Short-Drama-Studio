#!/usr/bin/env bash
set -e
SK="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$SK/dist/shortdrama-upload.zip}"
S="$(mktemp -d)"; P="$S/shortdrama-skillbot"; mkdir -p "$P/scripts" "$P/tools"
cp "$SK/SKILL.md" "$P/SKILL.md"
cp "$SK/pricing.json" "$P/pricing.json"
cp "$SK/AGENT-UX.md" "$P/AGENT-UX.md"
cp "$SK/config.example.json" "$P/config.example.json" 2>/dev/null || true
cp "$SK/scripts"/*.py "$P/scripts/" 2>/dev/null
cp "$SK/tools"/*.py "$P/tools/" 2>/dev/null
mkdir -p "$(dirname "$OUT")"; rm -f "$OUT"
(cd "$S" && zip -qr "$OUT" shortdrama-skillbot)
echo "发布包: $OUT"; unzip -l "$OUT" | grep -E 'SKILL|run_one|config.example|qc_report|finish|editor' | head
