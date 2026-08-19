#!/usr/bin/env bash
# Commit dos artefactos CalVer na branch staging (job Deploy).
set -euo pipefail

if [ "${GITHUB_REF:-}" != "refs/heads/staging" ]; then
  echo "Skip persist (ref ${GITHUB_REF:-} != refs/heads/staging)."
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add VERSION CHANGELOG.md docs/releases/manifest.json \
  backend/app/data/release_notes.json frontend/public/release-notes.json
if git diff --staged --quiet; then
  echo "Nenhum artefato de release para commitar."
  exit 0
fi
VER="$(tr -d '\n\r' < VERSION)"
git commit -m "chore(release): publica v${VER} [skip ci]"
git push origin HEAD:staging
