#!/bin/bash
# capture-screenshots.sh <client-dir>
#
# Reads <client-dir>/research/audit-pages.json and captures full-page
# screenshots for every audit page at desktop (1440x900) and mobile
# (390x844). Homepage gets an extra tablet (768x1024) pass.
#
# Then reads <client-dir>/research/competitors.json and captures each
# competitor at desktop + mobile. Drops competitors whose desktop shot
# is < 50KB (SPA blank-render guard, Learning #8).
#
# Idempotent: skips files > 10KB. The size check on every audit-page
# capture IS the Phase 2 hard gate — exits non-zero on any failure.

set -e

CLIENT_DIR="${1:?Usage: capture-screenshots.sh <client-dir>}"
ROOT="$(cd "$CLIENT_DIR" && pwd)"
PAGES="$ROOT/research/audit-pages.json"
COMPS="$ROOT/research/competitors.json"
OUT="$ROOT/research/screenshots"
COMP_OUT="$OUT/competitors"

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

if ! command -v jq >/dev/null; then echo "Error: jq required."; exit 1; fi
if [ ! -f "$PAGES" ]; then echo "Error: $PAGES not found. Run Phase 1 first."; exit 1; fi
if [ ! -x "$CHROME" ] && [ ! -f "$CHROME" ]; then
  echo "Error: Chrome not found at $CHROME (override with CHROME=...)"; exit 1
fi

mkdir -p "$OUT" "$COMP_OUT"

# capture <url> <out-path> <width> <height>
capture() {
  local url="$1" out="$2" w="$3" h="$4"
  if [ -f "$out" ] && [ "$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out")" -gt 10240 ]; then
    echo "  · skip $(basename "$out") (exists)"; return 0
  fi
  "$CHROME" --headless=new --hide-scrollbars --disable-gpu \
            --window-size="${w},${h}" \
            --screenshot="$out" "$url" >/dev/null 2>&1 || true
  if [ ! -f "$out" ]; then echo "  ✗ FAIL $(basename "$out")"; return 1; fi
  local sz; sz=$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out")
  if [ "$sz" -lt 10240 ]; then echo "  ✗ TOO SMALL $(basename "$out") (${sz}B)"; return 1; fi
  echo "  ✓ $(basename "$out") (${sz}B)"
}

echo "Audit-page screenshots → $OUT"
FAILED=0
while IFS=$'\t' read -r slug url role; do
  capture "$url" "$OUT/${slug}-desktop.png" 1440 900 || FAILED=$((FAILED+1))
  capture "$url" "$OUT/${slug}-mobile.png"  390  844 || FAILED=$((FAILED+1))
  if [ "$role" = "homepage" ]; then
    capture "$url" "$OUT/${slug}-tablet.png" 768 1024 || FAILED=$((FAILED+1))
  fi
done < <(jq -r '.pages[] | [.slug, .url, .role] | @tsv' "$PAGES")

if [ "$FAILED" -gt 0 ]; then
  echo ""; echo "✗ Phase 2 hard gate failed: $FAILED audit-page screenshot(s) missing or blank."
  exit 1
fi

# Competitors (optional)
if [ -f "$COMPS" ]; then
  COMP_URLS=$(jq -r '.urls[]?' "$COMPS")
  if [ -n "$COMP_URLS" ]; then
    echo ""
    echo "Competitor screenshots → $COMP_OUT"
    while IFS= read -r curl_; do
      [ -z "$curl_" ] && continue
      domain=$(echo "$curl_" | sed -E 's#^https?://##; s#/.*##')
      d_out="$COMP_OUT/${domain}-desktop.png"
      m_out="$COMP_OUT/${domain}-mobile.png"
      capture "$curl_" "$d_out" 1440 900 || true
      capture "$curl_" "$m_out" 390  844 || true
      # Quality gate: drop SPA blanks (< 50KB on desktop)
      if [ -f "$d_out" ]; then
        sz=$(stat -f%z "$d_out" 2>/dev/null || stat -c%s "$d_out")
        if [ "$sz" -lt 51200 ]; then
          echo "  ⚠ drop $domain (desktop ${sz}B < 50KB — likely SPA blank)"
          rm -f "$d_out" "$m_out"
        fi
      fi
    done <<< "$COMP_URLS"
  fi
fi

echo ""
echo "Done."
