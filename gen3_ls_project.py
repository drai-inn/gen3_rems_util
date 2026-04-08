#!/usr/bin/env python3

# First get your gen3 api credentials from the app into the file
# pointed to by the -c argument, or env variable GEN3_CRED_FILE
# (visit $GEN3_URL/identity)
# Make sure you're logged in as a user who can add data to the project in question (see URL)

import json
import argparse
import os
import requests

parser = argparse.ArgumentParser(description='Delete GEN3 project.')
parser.add_argument('--cred','-c', dest='cred', help='GEN3 api credentials file', required=False)
parser.add_argument('--program','-p', dest='program', help='GEN3 program name', required=True)

args = parser.parse_args()
cred=args.cred
program=args.program

if cred == None:
	cred = os.environ.get("GEN3_CRED_FILE")

GEN3_URL = os.environ.get("GEN3_URL")
if (GEN3_URL == None or len(GEN3_URL) == 0):
	print("Missing environment variable GEN3_URL. Eg:")
	print("export GEN3_URL=\"https://browse.rakeiora.ac.nz\"")
	exit(1)

URL=GEN3_URL + "/api/v0/submission/" + program

f = open(cred)
cred = json.load(f)
key = cred

# Pass the API key to the Gen3 API using "requests.post" to receive the access token:
token = requests.post(GEN3_URL + '/user/credentials/cdis/access_token', json=key).json()

headers = {'Authorization': 'bearer '+ token['access_token']}

u = requests.get(URL, headers=headers)

if (u.status_code != 200):
	print("Error:", u.status_code)
	print(u.text)
	exit(1)

o=u.json()
for l in sorted(o["links"]):
	print(l.replace('/v0/submission/' + program + '/',''))
