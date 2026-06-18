#!/usr/bin/env python3
# Delete a single GEN3 record (entity) by id.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='Delete a GEN3 record (entity).')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)')
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project', '-j', dest='project', help='GEN3 project name', required=True)
parser.add_argument('--entity', '-e', dest='eid', help='entity id to delete', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program + "/" + args.project + "/entities/" + args.eid
headers = gen3_headers(args.cred)

u = requests.delete(URL, headers=headers)
print(u.text)  # should display the API response
