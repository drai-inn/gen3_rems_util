# gen3_rems_util

Utility scripts for dealing with **REMS** and **GEN3**.

> ⚠️ There may be lots of stuff here that is specific to the task these were
> written for — use at your own risk.

Developed over 2024–2025–2026 by matt.pestle@auckland.ac.nz

The k8s related scripts may make some assumptions about namespace names.
Adjust as per your helm/deployments and its namespaces.

## Prerequisites

Most utilities presume you have some environment variables set up in the
calling environment. See the variables defined in [`env.prod`](env.prod) and
[`env.test`](env.test).

- Users and API keys must be set up in both GEN3 and REMS (see env).
- You must have `kubectl` installed to use the k8s related scripts.
- These utilise `jq` quite a bit, so make sure that's installed and on your `$PATH`.
- These call each other, so put the directory holding these on your `$PATH`.
- Read in your environment before running: `. ./env.test` or `. ./env.prod` (adjust accordingly).
- To use `rems_db_k8s` you also need the password to the postgres DB. This
  script uses the `gsecret` utility — you can make your own version if you
  don't use it.

The Python scripts read your GEN3 API credentials from the file pointed to by
the `GEN3_CRED_FILE` environment variable (or the `-c`/`--cred` argument), and
the target instance from `GEN3_URL`. Download credentials from
`$GEN3_URL/identity`, logged in as a user permitted to perform the operation.

> ⚠️ **The personal API key expires after ~30 days.** The credentials you
> download from `$GEN3_URL/identity` are a *personal refresh token* that GEN3
> expires after about a month. That's fine for occasional manual use, but it
> means any **unattended** use — cron jobs, scheduled syncs — will stop working
> every 30 days until you log in and download a fresh key.
>
> For automation, set up a **non-expiring OAuth2 `client_credentials` service
> client** instead, and point the scripts at it with the `GEN3_CLIENT_ID` and
> `GEN3_CLIENT_SECRET` environment variables. When both are set, the scripts
> authenticate as that service client and ignore `GEN3_CRED_FILE`; when they're
> not, they fall back to the personal API key as above — so existing usage keeps
> working unchanged. See **[SERVICE_CLIENT_SETUP.md](SERVICE_CLIENT_SETUP.md)**
> for how to create and authorize one.

## Conventions

These scripts assume a working convention that **REMS resources and catalogue
(application) items are kept in one-to-one correspondence** — each dataset is one
resource paired with one catalogue item. They are created together with
[`rems_res_and_item`](rems_res_and_item) and retired together with
[`rems_archive_res_and_item`](rems_archive_res_and_item).

REMS does not require this — a single resource can back several catalogue items,
items can be reused across workflows/forms, and so on. The pairing is simply how
this project manages the GEN3↔REMS dataset sync. If you reuse these scripts in a
setup that doesn't follow the convention, bear that in mind.

## REMS utilities

| Script | Purpose |
| --- | --- |
| `rems_adjust` | Enable/disable and archive/unarchive resources and items via the REMS API (call for usage) |
| `rems_archive_res_and_item` | Disable and archive a resource together with its catalogue item(s) — the inverse of `rems_res_and_item`. Takes one or more resource ids or resids (call for usage) |
| `rems_db_k8s` | Go directly into the postgres DB (see note about the secret above) |
| `rems_db_shell_k8s` | Shell into the postgres pod |
| `rems_form_out2in` | Retrieve a form and prepare it for pushing back in |
| `rems_get` | Retrieve stuff using the REMS API (call for usage) |
| `rems_license_out2in` | Retrieve a license and prepare it for pushing back in |
| `rems_logs_k8s` | Tail the REMS logs (supports the `-f`/follow option) |
| `rems_org_out2in` | Retrieve an org and prepare it for pushing back in |
| `rems_push` | POST data to the REMS API (call it to get usage) |
| `rems_res_and_item` | Create a resource and item in tandem |
| `rems_restart_k8s` | Restart REMS gracefully by scaling the deployment to 0 and 1 |
| `rems_setup_admin_and_key` | Initial creation of REMS admin user and setting up `$REMS_API_KEY` |
| `rems_shell_k8s` | Shell into the rems-app pod |
| `rems_users_k8s` | List users in REMS |

## GEN3 utilities

Various utilities for examining/modifying GEN3 programs, projects, and data
nodes via the GEN3 API.

### Create

| Script | Purpose |
| --- | --- |
| `gen3_create_program.py` | Create a program |
| `gen3_create_project.py` | Create a project in a given program |
| `gen3_create_record.py` | Submit a JSON record in a given program and project (can create or modify any record) |

### Delete

| Script | Purpose |
| --- | --- |
| `gen3_delete_program.py` | Delete a program, which must be empty (delete its projects first) |
| `gen3_delete_project.py` | Delete a *single* project, which must be empty (delete its children first) |
| `gen3_delete_projects.py` | Delete one or more named projects, **emptying each first** — see below |
| `gen3_delete_record.py` | Delete a record in a given program/project (you must know the entity ID — use `gen3_export_node_label.py` to find it) |
| `gen3_delete_node_label` | Delete all records of a given node label (uses `gen3_delete_record.py`) |

#### `gen3_delete_projects.py`

A higher-level, convenience wrapper for bulk-deleting whole projects. A GEN3
project must be **empty** before it can be deleted, so unlike
`gen3_delete_project.py` (which fails if the project still has records), this
script does the whole job for you:

1. For each named project it deletes **every record**, in repeated passes, so
   leaf nodes are removed before their parents.
2. Once a project is empty, it deletes the now-empty project itself.

It is **dry-run safe by default**: it prints what it *would* delete and asks for
confirmation. Type `yes` at the prompt (or pass `--yes`/`-y`) to actually
perform the deletions.

**Usage:**

```bash
# Read your environment first (sets GEN3_URL, GEN3_CRED_FILE, etc.)
. ./env.test

# Delete a single project (prompts for confirmation):
python ./gen3_delete_projects.py -p NZ -j 99999

# Delete several projects at once (comma-separated):
python ./gen3_delete_projects.py -p NZ -j proj1,proj2,proj3

# Skip the confirmation prompt:
python ./gen3_delete_projects.py -p NZ -j 99999 --yes
```

**Arguments:**

| Flag | Required | Description |
| --- | --- | --- |
| `-p`, `--program` | yes | GEN3 program name |
| `-j`, `--project` | yes | Comma-separated list of projects to delete, e.g. `-j proj1,proj2,proj3` |
| `-c`, `--cred` | no | GEN3 API credentials file (defaults to `$GEN3_CRED_FILE`) |
| `-y`, `--yes` | no | Skip the confirmation prompt and delete immediately |

**Notes:**

- Projects you name that don't exist in the program are reported and skipped.
- If a project can't be fully emptied (e.g. a record won't delete), the script
  reports which records are stuck and skips deleting that project.
- The GEN3 API returns HTTP `200` or `204 No Content` on a successful delete —
  both are treated as success.

### List / export

| Script | Purpose |
| --- | --- |
| `gen3_ls_program.py` | List all programs your API key has access to |
| `gen3_ls_project.py` | List all projects in a program |
| `gen3_ls_node_labels.py` | List the node labels of a given program/project |
| `gen3_export_node_label.py` | Export (JSON) all records of a given node label in a program/project |
| `gen3_projects_with_multiple_datasets` | List all projects that have more than 1 dataset |

### Other

| Script | Purpose |
| --- | --- |
| `gen3_cronjob_trigger` | Manually trigger a k8s cronjob |

### Site-specific: `application_url` scripts

These are specific to our GEN3 data dictionary, which has an `application_url`
field that the user clicks on in order to apply for access. Someone else's data
dictionary will be different, so you'll need to adjust these accordingly.

| Script | Purpose |
| --- | --- |
| `gen3_set_application_url_dataset` | Set the `application_form` datapoint for a dataset to a REMS application or an explicit URL |
| `gen3_set_application_url_all` | Set all `application_form` datapoints to the corresponding REMS application |
| `gen3_set_application_url_project` | Set all `application_form` datapoints for datasets in a given project |

### Site-specific: `gen3_sync`

Doubly specific to our situation and will need adjusting for any other. Note in
particular it doesn't "adjust" anything that might have changed in GEN3 — just
new stuff.

For any new resource IDs in GEN3 that aren't already in REMS, create a resource
and an application item. Optionally, go back to GEN3 and set the
`application_form` datapoint to the REMS application URL for that dataset.

This really needs to be adjusted to get the information (`REMS_ORG_ID`,
`REMS_LICENSE_ID`, `REMS_WORKFLOW_ID`, `REMS_URN_PREFIX`) that each item in GEN3
should be associated with in REMS from the GEN3 data dictionary. Currently we've
got a one-size-fits-all approach, but that means more adjustment required to the
GEN3 data dictionary. Will resolve when we need it.

## Kubernetes

| Script | Purpose |
| --- | --- |
| `k8s_configmap_refresh` | Refresh the configmap in the same fashion as happens in the `.gitlab-ci.yml` pipelines |
