#!/usr/bin/env python3
# Export all nodes of a given node_label from a GEN3 project.
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
import argparse
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='Export all nodes of a given node_label')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)')
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project', '-j', dest='project', help='GEN3 project name', required=True)
parser.add_argument('--node_label', '-l', dest='node_label', help='node_label', required=True)
parser.add_argument('--format', '-f', dest='format', help='format, json or tsv', default="json")
args = parser.parse_args()

GEN3_URL = gen3_base_url()
URL = GEN3_URL + "/api/v0/submission/" + args.program + "/" + args.project
URL = URL + "/export/?node_label=" + args.node_label + "&format=" + args.format

headers = gen3_headers(args.cred)
u = requests.get(URL, headers=headers)
print(u.text)  # API response
