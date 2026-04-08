Utility scripts for dealing with REMS and GEN3.
There may be lots of stuff here that is specific to the task I wrote these
for - use at your own risk.

Developed over 2024-2025-2026

matt.pestle@auckland.ac.nz

The k8s related scripts may make some assumptions about namespace names.
Adjust as per your helm/deployments and its namespaces.

Most utilities presume you have some environment variables set up in
the calling environmment. See the variables defined in:
- env.prod
- env.test

Prerequisites:
- users and api keys must be set up in both GEN3 and REMS (see env)
- you must have k8s/kubectl installed to use the k8s related ones
- these utilise jq quite a bit, so make sure that's installed and in your $PATH
- these call each other, so put the directory holding these in your $PATH
- read in your environment (. ./env.test or . ./env.prod - adjust accordingly)
- To use rems_db_k8s you also need the password to the postgres DB.
  This script uses the gsecret utility. You can make your own version if you don't use this.


REMS related utilities:

rems_adjust - enable/disable and archive/unarchive resources and items using REMS api (call for usage)
rems_db_k8s - go directly into the postgres DB (see note about the secret above)
rems_db_shell_k8s - shell into the postgres pod
rems_form_out2in - retrieve a form and prepare it for pushing back in
rems_get - retrieve stuff using the REMS api (call for usage)
rems_license_out2in - retrieve a license and prepare it for pushing back in
rems_logs_k8s - tail the rems logs (support the -f[follow] option)
rems_org_out2in - retrieve an org and prepare it for pushing back in
rems_push - post data to the REMS api (call it to get usage)
rems_res_and_item - create a resource and item in tandem
rems_restart_k8s - restart rems gracefully by scaling the deployment to 0 and 1
rems_setup_admin_and_key - initial creation of REMS admin user and setting up the $REMS_API_KEY
rems_shell_k8s - shell into the rems-app pod
rems_users_k8s - list users in REMS


There are also various utilities here for examining/modifying
GEN3 programs, projects, and data nodes via the GEN3 api.

gen3_create_program.py - Create a program
gen3_create_project.py - Create a project in a given program
gen3_create_record.py  - Submit a json record in a given program and project. So this can
    be used to create or modify any record in the GEN3 database.

gen3_delete_program.py - Delete a program, which must be empty, so delete projects first
gen3_delete_project.py - Delete a project, which must be empty, so delete children first
gen3_delete_record.py - Delete a record in a given program/project. You must know the
    entity ID, so use gen3_export_node_label.py to find the entity you want to delete.
gen3_delete_node_label - Delete all records of a given node label (uses gen3_delete_record.py)

gen3_ls_program.py - ls all the programs your api key has access to
gen3_ls_project.py - ls all the projects in a program
gen3_ls_node_labels.py - ls the node_labels of a given program/project
gen3_export_node_label.py - export (json) all records of a given node_label in a program/project

gen3_cronjob_trigger - manually trigger a k8s cronjob

gen3_projects_with_multiple_datasets - ls all projects that have more than 1 dataset

gen3_refresh_api_key.py - Nice try, but doesn't work. You don't seem to be able to do this in GEN3.
    Will need to figure out admin users so we don't have to refresh an api key every month.

# These next 3 are specific to our GEN3 data dictionary, which has an "application_url" field
# that the user clicks on in order to apply for access - these scripts adjust this field. As
# someone else's data dictionary will be different, you'll need to adjust this accordingly.
gen3_set_application_url_dataset - Set the application_form datapoint for a dataset to a REMs application
    or an explicit URL
gen3_set_application_url_all - Set all application_form datapoints to the corresponding REMS application
gen3_set_application_url_project - Set all application_form datapoints for datasets in a given project

gen3_sync - For any new resource IDs in GEN3 that aren't already in REMS, create a resource and
    an application item. Optionally, go back to GEN3 and set the application_form datapoint to
    the REMS application URL for that dataset.
    This really needs to be adjusted to get information (REMS_ORG_ID, REMS_LICENSE_ID, REMS_WORKFLOW_ID,
    REMS_URN_PREFIX) that each item in GEN3 should be associated with in REMS from the GEN3
    data dictionary. Currently we've got a one-size-fits-all approach. But that means more adjustment
    required to the GEN3 data dictionary. Will resolve when we need it.

k8s_configmap_refresh - Refresh the configmap in the same fashion as happens in the .gitlab-ci.yml pipelines
