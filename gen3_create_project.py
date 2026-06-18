#!/usr/bin/env python3
# Create a GEN3 project under a program by submitting a project JSON.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='Create a GEN3 project.')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)')
parser.add_argument('--file', '-f', dest='file', help='json file to post to GEN3', required=True)
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program
headers = gen3_headers(args.cred)

data = ''
with open(args.file, 'r') as f:
    for line in f:
        data = data + line + "\r"
# encode as utf-8 in case you're sending any text that's non-ascii
u = requests.put(URL, data=data.encode('utf-8'), headers=headers)
print(u.text)  # should display the API response
