#!/usr/bin/env python3
# First get your gen3 api credentials from the app into the file pointed to by
# the env variable GEN3_CRED_FILE
# (visit $GEN3_URL/identity)
# Make sure you're logged in as a user who can add data to the project in question (see URL)
import json
import argparse
import os
import requests

parser = argparse.ArgumentParser(description='Submit new tertiary care dataset to GEN3.')
parser.add_argument('--cred','-c', dest='cred', help='GEN3 api credentials file')
parser.add_argument('--file','-f', dest='file', help='json file to post to GEN3', required=True)
args = parser.parse_args()
cred=args.cred

if cred == None:
	cred = os.environ.get("GEN3_CRED_FILE")

GEN3_URL = os.environ.get("GEN3_URL")
if (GEN3_URL == None or len(GEN3_URL) == 0):
	print("Missing environment variable GEN3_URL. Eg:")
	print("export GEN3_URL=\"https://browse.rakeiora.ac.nz\"")
	exit(1)

URL=GEN3_URL + "/api/v0/submission/"
myfile=args.file
f = open(cred)
cred = json.load(f)
key = cred
# Pass the API key to the Gen3 API using "requests.post" to receive the access token:
token = requests.post(GEN3_URL + '/user/credentials/cdis/access_token', json=key).json()
headers = {'Authorization': 'bearer '+ token['access_token']}
data = ''
with open(myfile, 'r') as file:
    for line in file:
        data = data + line + "\r"
# encode as utf-8 in case you're sending any text that's non-ascii
u = requests.put(URL, data=data.encode('utf-8'), headers=headers)
print(u.text) # should display the API response
