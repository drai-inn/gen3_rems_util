#!/usr/bin/env python3
"""Shared GEN3 authentication for the util/ scripts.

Auth selection:
  * If GEN3_CLIENT_ID and GEN3_CLIENT_SECRET are BOTH set, the OAuth2
    client_credentials grant is used EXCLUSIVELY. On failure this exits
    non-zero -- it never falls back to the API key.
  * Otherwise the legacy API key file is used (an explicit path if given,
    else GEN3_CRED_FILE) -- a 30-day refresh token.

Diagnostics are written to stderr so callers' stdout stays clean.
"""
import json
import os
import sys
import requests


def _log(*a):
    print("[gen3_auth]", *a, file=sys.stderr, flush=True)


def gen3_base_url():
    """Return GEN3_URL without a trailing slash, or exit if unset."""
    url = os.environ.get("GEN3_URL")
    if not url:
        _log("ERROR: missing environment variable GEN3_URL (eg https://test.agdr.org.nz)")
        sys.exit(1)
    return url.rstrip("/")


def get_access_token(cred_file=None):
    """Return a GEN3 access token string, or exit non-zero on failure."""
    base = gen3_base_url()
    client_id = os.environ.get("GEN3_CLIENT_ID")
    client_secret = os.environ.get("GEN3_CLIENT_SECRET")

    if client_id and client_secret:
        token_url = base + "/user/oauth2/token"
        _log("auth: client_credentials (exclusive; no API-key fallback) ->", token_url)
        _log("  GEN3_CLIENT_ID =", repr(client_id),
             "| secret:", "set, %d chars" % len(client_secret))
        resp = requests.post(
            token_url,
            data={"grant_type": "client_credentials", "scope": "openid user data"},
            auth=(client_id, client_secret),
        )
        how = "client_credentials"
    else:
        if cred_file is None:
            cred_file = os.environ.get("GEN3_CRED_FILE")
        token_url = base + "/user/credentials/cdis/access_token"
        _log("auth: legacy API key file", repr(cred_file), "->", token_url)
        if not cred_file or not os.path.exists(cred_file):
            _log("ERROR: API key file not found:", repr(cred_file))
            sys.exit(1)
        with open(cred_file) as f:
            key = json.load(f)
        resp = requests.post(token_url, json=key)
        how = "api-key"

    _log("%s token request -> HTTP %s" % (how, resp.status_code))
    try:
        token = resp.json()
    except ValueError:
        _log("ERROR: token endpoint returned non-JSON body:")
        _log(resp.text[:1000])
        sys.exit(1)
    if "access_token" not in token:
        _log("ERROR: %s auth failed; no access_token in response:" % how)
        _log(json.dumps(token, indent=2)[:1000])
        sys.exit(1)
    _log("got access token (%d chars)" % len(token["access_token"]))
    return token["access_token"]


def gen3_headers(cred_file=None):
    """Return an Authorization header dict for GEN3 API calls."""
    return {"Authorization": "bearer " + get_access_token(cred_file)}
