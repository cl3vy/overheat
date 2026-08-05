#!/usr/bin/env bash
# Assemble the exact ACP upload staging from the canonical sources:
#   acp-upload/math/      <- math-out/publish_files/* + math-out/configs/config*.json
#   acp-upload/frontend/  <- web-sdk/apps/overheat-rig/build/*
#
# Run from anywhere; regenerates acp-upload/ from scratch so it can never
# drift out of date. Verifies the math and checks the frontend build exists
# before staging anything.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
python="$root/env/bin/python"
[ -x "$python" ] || python="python3"

echo "== verifying math package (v4) =="
(cd "$root/math" && "$python" validate_books.py)

frontend_build="$root/web-sdk/apps/overheat-rig/build"
if [ ! -f "$frontend_build/index.html" ]; then
	echo "ERROR: no frontend build at $frontend_build" >&2
	echo "       run: cd web-sdk/apps/overheat-rig && pnpm run build" >&2
	exit 1
fi

echo "== staging acp-upload/ =="
rm -rf "$root/acp-upload"
mkdir -p "$root/acp-upload/math" "$root/acp-upload/frontend"
cp "$root"/math-out/publish_files/* "$root/acp-upload/math/"
cp "$root"/math-out/configs/config*.json "$root/acp-upload/math/"
cp -R "$frontend_build"/. "$root/acp-upload/frontend/"
find "$root/acp-upload" -name '.DS_Store' -delete

echo
echo "Staged for upload:"
echo "  math:     $(ls "$root/acp-upload/math" | wc -l | tr -d ' ') files -> acp-upload/math/"
echo "  frontend: $(ls "$root/acp-upload/frontend" | wc -l | tr -d ' ') entries -> acp-upload/frontend/"
echo "  Tip: run 'cd math && ../env/bin/python emit_stake.py' before this if books changed."
