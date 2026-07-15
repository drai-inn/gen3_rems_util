#!/bin/bash
#
# gen3_purge_project.sh — remove a project from ALL of Gen3's stores, in order:
#   1. graph (sheepdog)  — delete every record leaf-first, then the project
#   2. MDS discovery      — delete the discovery_metadata record (guid = PROGRAM-PROJECT)
#   3. Elasticsearch      — trigger the ETL cronjob so /exploration reflects it
#
# Why: a Gen3 "delete" only lands in the graph. Neither the metadata-sync
# (upsert-only, never prunes) nor the ETL ("Nothing's new" on a pure delete)
# propagate a removal, so /discovery and /exploration keep showing a deleted
# project. This does steps 2 and 3 explicitly.
#
# Target is whatever your environment points at — like the other scripts, there
# is NO test/prod flag; source env.test or env.prod first.
#
# Required environment:
#   GEN3_URL          base commons URL              (also used by gen3_auth)
#   KUBECONFIG        cluster for the ETL trigger
#   GEN3_ETL_CRONJOB  name of the ETL cronjob       (installation-specific; e.g. etl-cronjob)
#   + gen3_auth creds: GEN3_CRED_FILE, or GEN3_CLIENT_ID/GEN3_CLIENT_SECRET
#
# Usage:
#   gen3_purge_project.sh <program> <project>              # DRY RUN (plan + current state)
#   gen3_purge_project.sh <program> <project> --yes        # purge
#   gen3_purge_project.sh <program> <project> --yes -w     # purge, then watch the ETL rebuild

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$HERE:${PYTHONPATH:-}"   # so the sibling *.py can import gen3_auth
die(){ echo "ERROR: $*" >&2; exit 1; }

# --- required environment (fail fast, like the other scripts) --------------
: "${GEN3_URL:?source env.test/env.prod first (GEN3_URL unset)}"
: "${KUBECONFIG:?source env.test/env.prod first (KUBECONFIG unset)}"
: "${GEN3_ETL_CRONJOB:?set GEN3_ETL_CRONJOB (the ETL cronjob name for this commons)}"

(( $# >= 2 )) || die "usage: $0 <program> <project> [--yes] [-w]"
PROGRAM="$1"; PROJECT="$2"; shift 2
YES=0; WATCH=0
while (( $# )); do
    case "$1" in
        --yes) YES=1 ;;
        -w)    WATCH=1 ;;   # with --yes: watch the ETL job to completion (dry run ignores it)
        *)     die "unknown option: $1 (expected --yes and/or -w)" ;;
    esac
    shift
done

BASE="${GEN3_URL%/}"                    # tolerate a trailing slash in GEN3_URL
GUID="${PROGRAM}-${PROJECT}"            # this commons keys each discovery_metadata record as PROGRAM-PROJECT
CTX="$(kubectl config current-context 2>/dev/null || echo '?')"

echo "Target:  $PROGRAM/$PROJECT"
echo "Commons: $BASE"
echo "Cluster: $CTX   (ETL cronjob: $GEN3_ETL_CRONJOB)"
echo "Plan:"
echo "  1. graph : delete all records + the project"
echo "  2. mds   : delete discovery_metadata record '$GUID'"
echo "  3. es    : trigger $GEN3_ETL_CRONJOB (rebuild /exploration)"
echo

if (( ! YES )); then
    echo "DRY RUN — re-run with --yes to execute."
    if projlist="$("$HERE/gen3_ls_project.py" -p "$PROGRAM" 2>/dev/null)"; then
        grep -qx "$PROJECT" <<<"$projlist" \
            && echo "  graph: PRESENT (would be deleted)" \
            || echo "  graph: absent (step 1 is a no-op)"
    else
        echo "  graph: could not list projects (auth/URL?)"
    fi
    printf '  mds:   '; curl -s "$BASE/mds/metadata/$GUID" -o /dev/null -w "GET %{http_code} (200=present, 404=already gone)\n"
    exit 0
fi

# --- 1. GRAPH --------------------------------------------------------------
echo "== [1/3] graph =="
"$HERE/gen3_delete_projects.py" -p "$PROGRAM" -j "$PROJECT" --yes

# --- 2. MDS ----------------------------------------------------------------
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

# --- 3. ES -----------------------------------------------------------------
# A pure delete doesn't move the ETL's watermark, so a normal run would log
# "Nothing's new" and skip. Force a full rebuild via tube's ETL_FORCED flag
# (run_etl.py --force) — rebuilds from the graph, so the deletion drops out.
echo "== [3/3] elasticsearch ETL (forced full rebuild) =="
echo
echo "Purge complete — /discovery is updated now; /exploration updates when the ETL finishes."
echo
"$HERE/gen3_cronjob_trigger" -e ETL_FORCED=true ${WATCH:+-w} "$GEN3_ETL_CRONJOB" >/dev/null
