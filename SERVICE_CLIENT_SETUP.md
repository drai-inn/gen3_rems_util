# Setting up a non-expiring GEN3 service client

The Python utilities here authenticate to GEN3 one of two ways:

1. **Personal API key** (`GEN3_CRED_FILE`) — downloaded from `$GEN3_URL/identity`.
   Simple, but it's a personal refresh token that **GEN3 expires after ~30 days**,
   so it's a poor fit for anything unattended.
2. **OAuth2 `client_credentials` service client** (`GEN3_CLIENT_ID` +
   `GEN3_CLIENT_SECRET`) — a **non-expiring** credential intended for automation.
   When both env vars are set, the scripts use this and ignore `GEN3_CRED_FILE`.

This document covers setting up option 2.

> **Terminology:** the *client secret* does not expire (you rotate it on your own
> schedule). The scripts exchange it for a short-lived **access token** on each
> run, so there's no 30-day key to refresh.

---

## When you need this

Use a service client when these scripts run **without a human** — a cron job, a
scheduled sync, a pipeline step. For occasional interactive use, the personal API
key is fine.

## What you'll need

Creating the client requires **administrative access to your GEN3 commons** — the
`fence-create` command runs inside the Fence service. If you don't operate the
commons yourself, ask whoever does to perform steps 1–2 and hand you back the
`client_id` / `client_secret`.

Placeholders used below — substitute your own:

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `<COMMONS_URL>` | Your GEN3 base URL | `https://gen3.example.org` |
| `<FENCE_NAMESPACE>` | k8s namespace Fence runs in | `gen3` |
| `<PROGRAM>` | The program you submit under | `MYPROGRAM` |

---

## Step 1 — Create the client (in Fence)

`fence-create` lives in the Fence container and writes the client to Fence's
database, so it persists regardless of which pod you run it in:

```bash
FENCE_POD=$(kubectl get pod -n <FENCE_NAMESPACE> -l app=fence \
  -o jsonpath='{.items[0].metadata.name}')

kubectl exec -it "$FENCE_POD" -n <FENCE_NAMESPACE> -- \
  fence-create client-create \
    --client my-automation-client \
    --grant-types client_credentials \
    --allowed-scopes openid user data \
    --expires-in 3650
```

This prints a `(client_id, client_secret)` pair **once** — capture both
immediately; the secret can't be retrieved later (you'd have to rotate).

**On `--expires-in`:** recent Fence versions require a positive number of days and
will warn that `client_credentials` clients "should expire within 12 months." It's
only a warning — the client is still created. Pick a window that fits your rotation
policy (`3650` = ~10 years above). Older Fence builds accept `--expires-in 0` to
mean "never expires"; newer ones reject `0`, so use a long finite value.

## Step 2 — Authorize the client

A fresh `client_credentials` client has **no permissions** — every API call returns
`403` until you grant it some. A client is **not** a user, so it's authorized in the
`clients:` section of your `user.yaml` (not `users:`), by name:

```yaml
authz:
  policies:
    - id: my-automation-policy
      role_ids: [<roles your operations need>]   # e.g. a sheepdog create/update role
      resource_paths: [/programs/<PROGRAM>]      # parent path covers all projects beneath it

clients:
  my-automation-client:
    policies:
      - my-automation-policy
```

Grant **only** what the automation needs (principle of least privilege) — this is a
long-lived credential. For example, a job that only submits records needs
create/update on the submission service + your program, not delete or admin.

Then run `usersync` so Arborist picks up the change. The client from step 1 **must
already exist** when usersync runs, or it logs `client ... does not exist in fence:
skipping` and grants nothing.

> If your commons reads the user's project list on the portal `/identity` page from
> the legacy per-user `project_access`, note that a *client* doesn't populate that —
> clients are authorized purely through Arborist. This only matters for the portal's
> display, not for what the scripts can do.

## Step 3 — Point the scripts at the client

Set the two environment variables (e.g. in your `env.*` file), and **do not** set
`GEN3_CRED_FILE` (or leave it set — the client vars take precedence):

```bash
export GEN3_URL="<COMMONS_URL>"
export GEN3_CLIENT_ID="your-client-id"
export GEN3_CLIENT_SECRET="..."     # see security note below
```

> 🔒 **Never commit the client secret.** Pull it from a secret manager at runtime
> rather than hard-coding it, e.g.:
> ```bash
> export GEN3_CLIENT_SECRET=$(your-secret-tool get gen3_automation_client_secret)
> ```
> Treat the `client_id` as non-public too — keep it out of public repos.

## Step 4 — Test

```bash
# obtain a token directly (sanity check):
curl -s -u "$GEN3_CLIENT_ID:$GEN3_CLIENT_SECRET" \
  -d grant_type=client_credentials -d scope="openid user data" \
  "$GEN3_URL/user/oauth2/token" | jq .access_token

# or just run a read-only utility — it will report which auth path it used:
./gen3_ls_program.py
```

A `403` on an operation means the token worked but the client lacks that policy —
revisit step 2. A failure to get a token at all (`invalid_client`) means the
id/secret are wrong or the client doesn't exist in the commons behind `GEN3_URL`.

---

## Maintenance

- **Rotation.** The secret is long-lived but not eternal; rotate it on your own
  schedule, or immediately if it leaks: `fence-create client-rotate --client
  my-automation-client` (or delete + re-create), update wherever the secret is
  stored, then re-run `usersync`. Set a calendar reminder ahead of the
  `--expires-in` date.
- **Least privilege.** Because this credential is long-lived, keep its policy as
  narrow as the job allows. Read/write operations can use it; destructive ones
  (deletes) are best left to an interactive admin credential — `unset
  GEN3_CLIENT_ID GEN3_CLIENT_SECRET` to fall back to your personal key for those.
- **Revocation.** To disable it entirely: `fence-create client-delete --client
  my-automation-client`, then `usersync`.
