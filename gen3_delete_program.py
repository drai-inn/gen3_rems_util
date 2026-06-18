#!/usr/bin/env python3
# Delete a GEN3 program.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='Delete a GEN3 program.')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)')
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program
headers = gen3_headers(args.cred)

u = requests.delete(URL, headers=headers)
print(u.text)  # should display the API response
