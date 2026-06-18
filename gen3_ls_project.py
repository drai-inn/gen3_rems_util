#!/usr/bin/env python3
# List GEN3 projects within a program.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='List GEN3 projects in a program.')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)', required=False)
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program
headers = gen3_headers(args.cred)

u = requests.get(URL, headers=headers)
if u.status_code != 200:
    print("Error:", u.status_code)
    print(u.text)
    exit(1)

o = u.json()
for l in sorted(o["links"]):
    print(l.replace('/v0/submission/' + args.program + '/', ''))
