#!/usr/bin/env python3
# First get your gen3 api credentials from the app into the file pointed to by
# the env variable GEN3_CRED_FILE
# (visit $GEN3_URL/identity)
# Make sure you're logged in as a user who can add data to the project in question (see URL)

import json

import argparse
import os
    
parser = argparse.ArgumentParser(description='Export all nodes of a given node_label')
parser.add_argument('--cred','-c', dest='cred', help='GEN3 api credentials file')
parser.add_argument('--program','-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project','-j', dest='project', help='GEN3 project name', required=True)
parser.add_argument('--node_label','-l', dest='node_label', help='node_label', required=True)
parser.add_argument('--format','-f', dest='format', help='format, json or tsv', default="json")

args = parser.parse_args()
cred=args.cred
program=args.program
project=args.project
node_label=args.node_label
format=args.format

if cred == None:
	cred = os.environ.get("GEN3_CRED_FILE")

GEN3_URL = os.environ.get("GEN3_URL")
if (GEN3_URL == None or len(GEN3_URL) == 0):
	print("Missing environment variable GEN3_URL. Eg:")
	print("export GEN3_URL=\"https://browse.rakeiora.ac.nz\"")
	exit(1)

#https://gen3.datacommons.io/api/v0/submission/GEO/GSE63878/export/?node_label=sample&format=tsv

URL=GEN3_URL + "/api/v0/submission/" + program + "/" + project 
URL=URL + "/export/?node_label=" + node_label + "&format=" + format
#URL=URL + "/entities/f6f240a9-e010-493c-bd62-afc8c1d8d827"

f = open(cred)
cred = json.load(f)
key = cred

# Import the "requests" Python module:
import requests

# Pass the API key to the Gen3 API using "requests.get" to receive the access token:
token = requests.post(GEN3_URL + "/user/credentials/cdis/access_token", json=key).json()
headers = {'Authorization': 'bearer '+ token['access_token']}

data = ''
# encode as utf-8 in case you're sending any text that's non-ascii
u = requests.get(URL, data=data.encode('utf-8'), headers=headers)
print(u.text) # should display the API response
