#!/usr/bin/env python3
# Submit (create/update) a dataset record to GEN3's submission API.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
# Diagnostics go to stderr; the GEN3 API response goes to stdout.
import sys
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers


def log(*a):
    print("[gen3_create_record]", *a, file=sys.stderr, flush=True)


parser = argparse.ArgumentParser(description='Submit new tertiary care dataset to GEN3.')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)')
parser.add_argument('--file', '-f', dest='file', help='json file to post to GEN3', required=True)
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project', '-j', dest='project', help='GEN3 project name', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program + "/" + args.project
headers = gen3_headers(args.cred)

data = ''
with open(args.file, 'r') as f:
    for line in f:
        data = data + line + "\r"

log("PUT", URL)
# encode as utf-8 in case you're sending any text that's non-ascii
u = requests.put(URL, data=data.encode('utf-8'), headers=headers)
log("submission -> HTTP", u.status_code)
print(u.text)  # API response on stdout
if not u.ok:
    log("ERROR: submission failed (HTTP %d)" % u.status_code)
    sys.exit(1)
log("submission OK")
