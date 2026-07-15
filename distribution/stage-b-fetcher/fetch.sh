#!/bin/sh
set -eu

owner="${1:-}"
repository="${2:-}"
commit="${3:-}"
skill_path="${4:-}"

case "$owner" in
  ""|*[!A-Za-z0-9-]*|-*) exit 64 ;;
esac
case "$repository" in
  ""|*[!A-Za-z0-9._-]*|[._-]*) exit 64 ;;
esac
case "$commit" in
  *[!0-9a-f]*|"") exit 64 ;;
esac
[ "${#commit}" -eq 40 ] || exit 64
case "$skill_path" in
  ""|/*|*/|*\\*|*..*|*//*|*/./*|./*|*[!A-Za-z0-9._/-]*) exit 64 ;;
esac

export HOME=/scratch/home
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_TERMINAL_PROMPT=0
export GIT_OPTIONAL_LOCKS=0
export GIT_PAGER=cat
export GIT_EXTERNAL_DIFF=
export GIT_ALLOW_PROTOCOL=https
export GIT_PROTOCOL_FROM_USER=0
export LC_ALL=C

mkdir -p /scratch/home /scratch/repository
git -c core.hooksPath=/dev/null -c credential.helper= \
  -c protocol.file.allow=never -c protocol.ext.allow=never \
  -C /scratch/repository init -q
git -C /scratch/repository config core.autocrlf false
git -C /scratch/repository config core.eol lf
git -C /scratch/repository config http.followRedirects false
git -C /scratch/repository remote add origin "https://github.com/$owner/$repository.git"
git -c core.hooksPath=/dev/null -c credential.helper= \
  -c protocol.file.allow=never -c protocol.ext.allow=never \
  -C /scratch/repository fetch --depth=1 --no-tags --filter=tree:0 origin "$commit"

[ "$(git -C /scratch/repository rev-parse FETCH_HEAD)" = "$commit" ] || exit 65
[ "$(git -C /scratch/repository cat-file -t "FETCH_HEAD:$skill_path")" = "tree" ] || exit 66
# Force every tree/blob needed by the requested directory through the same
# kernel-capped tmpfs before the repository is exported to the host.
git -C /scratch/repository archive --format=tar FETCH_HEAD -- "$skill_path" >/dev/null
git -C /scratch/repository config remote.origin.promisor false
git -C /scratch/repository config --unset-all extensions.partialclone 2>/dev/null || true
git -C /scratch/repository remote remove origin

exec tar -C /scratch/repository -cf - .
