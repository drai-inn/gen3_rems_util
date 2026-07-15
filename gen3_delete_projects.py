#!/usr/bin/env python3
# Bulk-delete one or more named GEN3 projects in a program.
#
# A GEN3 project must be EMPTY before it can be deleted, so for each project this
# script first deletes every record (in repeated passes, so leaf nodes are removed
# before their parents) and then deletes the now-empty project itself.
#
# By default it only prints what it WOULD do. Pass --yes (or type "yes" at the
# prompt) to actually perform the deletions.
#
# Auth: see gen3_auth.py (client_credentials preferred, API key fallback).
# Make sure you're authenticated as a principal that can delete data in the program.

import argparse
import sys
import requests
from gen3_auth import gen3_base_url, gen3_headers

parser = argparse.ArgumentParser(description='Bulk delete named GEN3 projects in a program (empties each first).')
parser.add_argument('--cred', '-c', dest='cred', help='GEN3 api credentials file (legacy API key)', required=False)
parser.add_argument('--program', '-p', dest='program', help='GEN3 program name', required=True)
parser.add_argument('--project', '-j', dest='projects', required=True,
                    help='comma-separated list of projects to delete, eg: -j proj1,proj2,proj3')
parser.add_argument('--yes', '-y', dest='yes', action='store_true',
                    help='skip the confirmation prompt and delete immediately')

args = parser.parse_args()

# Accept comma-separated projects with optional surrounding whitespace.
requested_projects = [p.strip() for p in args.projects.split(',') if p.strip()]
if not requested_projects:
	print("No projects given. Use -j proj1,proj2,proj3")
	sys.exit(1)

program = args.program
GEN3_URL = gen3_base_url()

SUBMISSION = GEN3_URL + "/api/v0/submission/"
# GEN3 dictionary entries that are not deletable project records.
RESERVED = {"_all", "data_release", "root", "program", "project"}


def get_token():
	"""Fetch a fresh access token (via gen3_auth — client_credentials or API key)."""
	return gen3_headers(args.cred)


def list_projects(headers):
	r = requests.get(SUBMISSION + program, headers=headers)
	if r.status_code != 200:
		print("Error listing projects:", r.status_code, r.text)
		sys.exit(1)
	prefix = '/v0/submission/' + program + '/'
	return sorted(l.replace(prefix, '') for l in r.json().get("links", []))


def list_node_labels(headers, project):
	url = SUBMISSION + program + "/" + project + "/_dictionary"
	r = requests.get(url, headers=headers)
	if r.status_code != 200:
		print("  Error listing node labels:", r.status_code, r.text)
		return []
	prefix = '/v0/submission/' + program + '/' + project + '/_dictionary/'
	labels = {l.replace(prefix, '') for l in r.json().get("links", [])}
	return sorted(labels - RESERVED)


def list_ids(headers, project, node_label):
	url = SUBMISSION + program + "/" + project + "/export/?node_label=" + node_label + "&format=json"
	r = requests.get(url, headers=headers)
	if r.status_code != 200:
		print("  Error exporting node '%s': %d %s" % (node_label, r.status_code, r.text))
		return []
	return [rec["id"] for rec in r.json().get("data", []) if "id" in rec]


def delete_entity(headers, project, eid):
	url = SUBMISSION + program + "/" + project + "/entities/" + eid
	r = requests.delete(url, headers=headers)
	# Gen3 returns 200 or 204 (No Content) on a successful delete.
	return r.status_code in (200, 204), r.status_code, r.text


def delete_project(headers, project):
	url = SUBMISSION + program + "/" + project
	r = requests.delete(url, headers=headers)
	# Gen3 returns 200 or 204 (No Content) on a successful delete.
	return r.status_code in (200, 204), r.status_code, r.text


def count_records(headers, project):
	return sum(len(list_ids(headers, project, lbl)) for lbl in list_node_labels(headers, project))


def empty_project(headers, project):
	"""Delete every record in the project. Repeated passes remove leaf nodes
	first (parent deletes fail while children exist). Returns True if emptied."""
	while True:
		deleted = 0
		errors = []  # (label, eid, status, text) for this pass
		for label in list_node_labels(headers, project):
			for eid in list_ids(headers, project, label):
				ok, status, text = delete_entity(headers, project, eid)
				if ok:
					deleted += 1
				else:
					errors.append((label, eid, status, text))
		if not errors:
			return True
		if deleted == 0:
			# A full pass deleted nothing yet records remain -> stuck. Show why.
			print("  STALLED: %d record(s) could not be deleted:" % len(errors))
			for label, eid, status, text in errors:
				print("    %s %s -> %d %s" % (label, eid, status, text))
			return False
		print("  ... deleted %d record(s), %d remaining, retrying pass" % (deleted, len(errors)))


def main():
	headers = get_token()
	existing = list_projects(headers)

	# Only delete the explicitly named projects, warning about any that don't exist.
	missing = [p for p in requested_projects if p not in existing]
	if missing:
		print("Warning: not found in program '%s' (skipping): %s" % (program, ", ".join(missing)))
	projects = [p for p in requested_projects if p in existing]

	if not projects:
		print("No matching projects to delete in program '%s'." % program)
		return

	print("Program: %s" % program)
	print("URL:     %s" % GEN3_URL)
	print("The following %d project(s) (and ALL their records) will be DELETED:" % len(projects))
	for p in projects:
		print("  - %s/%s  (%d record(s))" % (program, p, count_records(headers, p)))

	if not args.yes:
		print()
		print("This is IRREVERSIBLE. Type 'yes' to proceed, anything else to abort:")
		try:
			answer = input("> ").strip()
		except EOFError:
			answer = ""
		if answer != "yes":
			print("Aborted. Nothing deleted.")
			return

	for p in projects:
		print("\n=== Deleting %s/%s ===" % (program, p))
		headers = get_token()  # refresh: tokens are short-lived
		if not empty_project(headers, p):
			print("  Skipping project delete (could not empty %s/%s)." % (program, p))
			continue
		ok, status, text = delete_project(headers, p)
		if ok:
			print("  Deleted project %s/%s." % (program, p))
		else:
			print("  FAILED to delete project %s/%s: %d %s" % (program, p, status, text))

	print("\nDone.")


if __name__ == "__main__":
	main()
