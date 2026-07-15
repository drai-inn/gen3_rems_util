#!/bin/bash
#
# gen3_purge_project.sh — remove a project from ALL of Gen3's stores, in order:
#   1. graph (sheepdog)  — delete every record leaf-first, then the project
#   2. MDS discovery      — delete the discovery_metadata record (guid = PROGRAM-PROJECT)
#   3. Elasticsearch      — trigger the tube ETL so /exploration reflects it
#
# Why this exists: a Gen3 "delete" only lands in the graph. Neither the
# metadata-sync (upsert-only, never prunes) nor the ETL ("Nothing's new" on a
# pure delete) propagate a removal — so /discovery and /exploration keep showing
# a deleted project forever. This does steps 2 and 3 explicitly.
#
# Usage:
#   gen3_purge_project.sh <test|prod> <program> <project>          # DRY RUN (shows plan+state)
#   gen3_purge_project.sh <test|prod> <program> <project> --yes    # actually purge
#
# Env (source env.test / env.prod first): GEN3_URL, KUBECONFIG, gen3_auth vars.
# Needs on PATH / alongside this script: gen3_delete_projects.py, gen3_ls_project.py,
# gen3_cronjob_trigger, gen3_auth.py; plus kubectl, jq, python3, curl.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$HERE:${PYTHONPATH:-}"   # so the sibling *.py can import gen3_auth
die(){ echo "ERROR: $*" >&2; exit 1; }

(( $# >= 3 )) || die "usage: $0 <test|prod> <program> <project> [--yes]"
CLUSTER="$1"; PROGRAM="$2"; PROJECT="$3"; shift 3
YES=0; [[ "${1:-}" == "--yes" ]] && YES=1

case "$CLUSTER" in test|prod) ;; *) die "cluster must be 'test' or 'prod'";; esac
: "${GEN3_URL:?set GEN3_URL (source env.$CLUSTER)}"
: "${KUBECONFIG:?set KUBECONFIG}"

# Guard: the live kube context must match the named cluster, so 'test' can't hit prod.
CTX="$(kubectl config current-context 2>/dev/null || true)"
[[ "$CTX" == *"$CLUSTER"* ]] || die "kube context '$CTX' doesn't match cluster '$CLUSTER' — refusing"

GUID="${PROGRAM}-${PROJECT}"

echo "Target: $PROGRAM/$PROJECT   cluster: $CLUSTER   context: $CTX"
echo "Plan:"
echo "  1. graph : delete all records + the project"
echo "  2. mds   : delete discovery_metadata record '$GUID'"
echo "  3. es    : trigger etl-cronjob (rebuild /exploration)"
echo

# ---- current state (read-only) -------------------------------------------
if (( ! YES )); then
    echo "DRY RUN — re-run with --yes to execute."
    if projlist="$("$HERE/gen3_ls_project.py" -p "$PROGRAM" 2>/dev/null)"; then
        grep -qx "$PROJECT" <<<"$projlist" \
            && echo "  graph: PRESENT (would be deleted)" \
            || echo "  graph: absent (step 1 is a no-op)"
    else
        echo "  graph: could not list projects (auth/URL?)"
    fi
    printf '  mds:   '; curl -s "$GEN3_URL/mds/metadata/$GUID" -o /dev/null -w "GET %{http_code} (200=present, 404=already gone)\n"
    exit 0
fi

# ---- 1. GRAPH ------------------------------------------------------------
echo "== [1/3] graph =="
"$HERE/gen3_delete_projects.py" -p "$PROGRAM" -j "$PROJECT" --yes

# ---- 2. MDS --------------------------------------------------------------
echo "== [2/3] mds discovery =="
# Safety: only delete the discovery record once the project is truly gone from
# the graph — never strip discovery for a project that still exists.
if projlist="$("$HERE/gen3_ls_project.py" -p "$PROGRAM")"; then
    grep -qx "$PROJECT" <<<"$projlist" \
        && die "project $PROGRAM/$PROJECT still in the graph — refusing to delete its discovery record"
else
    die "couldn't verify graph state — refusing MDS delete"
fi
python3 - "$GUID" <<'PY'
import sys, requests
from gen3_auth import gen3_base_url, gen3_headers
guid = sys.argv[1]
r = requests.delete(gen3_base_url() + "/mds/metadata/" + guid, headers=gen3_headers())
print("   DELETE /mds/metadata/%s -> %s %s" % (guid, r.status_code, r.text[:300]))
# 404 = already absent (fine); 200/204 = deleted; anything else is a real failure.
sys.exit(0 if r.status_code in (200, 204, 404) else 1)
PY

# ---- 3. ES ---------------------------------------------------------------
echo "== [3/3] elasticsearch ETL =="
echo "   (a pure delete won't move tube's watermark; triggering a rebuild)"
"$HERE/gen3_cronjob_trigger" etl-cronjob >/dev/null
echo "   etl-cronjob triggered. If /exploration still shows it after the job completes,"
echo "   re-submit any surviving record to bump the watermark, then trigger etl-cronjob again."

echo
echo "Done. Verify: /discovery (gone immediately) and /exploration (once ETL finishes)."
