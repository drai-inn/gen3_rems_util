#!/usr/bin/env python3
# List the node labels (dictionary entries) available in a GEN3 project.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='List GEN3 node labels for a project.')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)', required=False)
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project', '-j', dest='project', help='GEN3 project name', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
headers = gen3_headers(args.cred)

URL = GEN3_URL + "/api/v0/submission/" + args.program + "/" + args.project + "/_dictionary"
u = requests.get(URL, headers=headers)
if u.status_code != 200:
    print("Error:", u.status_code)
    print(u.text)
    exit(1)

o = u.json()
newl = []
for l in o["links"]:
    s = l.replace('/v0/submission/' + args.program + '/' + args.project + '/_dictionary/', '')
    newl.append(s)

reserved = ["_all", "data_release", "root", "program", "project"]
z = list(set(newl) - set(reserved))
for l in sorted(z):
    print(l)
