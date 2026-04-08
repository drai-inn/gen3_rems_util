#!/usr/bin/env python3
#
# This is an attempt to refresh the api key.
# But it doesn't work, I'm pretty sure because it's not
# allowed by the GEN3 system. So ignore this.
#

import os
import json
import requests
import sys
from kubernetes import client, config

def rotate_gen3_key():
    # 1. Setup K8s Client
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    v1 = client.CoreV1Api()
    
    # Environment Setup
    ns = os.environ.get("REMS_NS", "default")
    secret_name = "gen3-api-key"
    gen3_url = os.environ.get("GEN3_URL", "").rstrip('/')
    cred_file = os.environ.get('GEN3_CRED_FILE')

    if not gen3_url or not cred_file:
        print("Error: GEN3_URL or GEN3_CRED_FILE not set.")
        sys.exit(1)

    # 2. Load CURRENT API Key from file
    with open(cred_file, 'r') as f:
        current_key_data = json.load(f)
    
    # 3. Exchange API Key for a short-lived Access Token
    token_url = f"{gen3_url}/user/credentials/cdis/access_token"

    # Update this section in your script
    token_payload = {
        "api_key": current_key_data.get('api_key'),
        "scope": "openid user fence credentials"
    }

    try:
        print(f"Requesting access token from {token_url}...")
        token_response = requests.post(token_url, json=token_payload)
        token_response.raise_for_status()
        access_token = token_response.json().get('access_token')
    except Exception as e:
        print(f"Failed to fetch access token: {e}")
        if 'token_response' in locals(): print(token_response.text)
        sys.exit(1)

    # 4. Use Access Token to request a brand NEW API Key
    print("Requesting new long-lived API Key...")
    headers = {'Authorization': f'bearer {access_token}'}
    new_key_url = f"{gen3_url}/user/credentials/cdis"

    # Instead of /user/credentials/cdis, try this:
    test_url = f"{gen3_url}/user/user"
    test_resp = requests.get(test_url, headers=headers)

    if test_resp.status_code == 200:
        print("✅ Your token is VALID for reading your profile.")
        print("❌ CONCLUSION: The Gen3 instance has BLOCKED programmatic key creation.")
    else:
        print(f"❌ Your token is INVALID even for basic reading. Status: {test_resp.status_code}")

    
    try:
        new_key_response = requests.post(new_key_url, headers=headers)
        new_key_response.raise_for_status()
        new_key_json_str = new_key_response.text # This is the full JSON blob
    except Exception as e:
        print(f"Failed to create new API key: {e}")
        if 'new_key_response' in locals(): print(new_key_response.text)
        sys.exit(1)

    # 5. Update the Kubernetes Secret
    try:
        # We use patch_namespaced_secret with string_data for easy updating
        secret_body = {
            "stringData": {
                "credentials.json": new_key_json_str
            }
        }
        v1.patch_namespaced_secret(secret_name, ns, secret_body)
        print(f"✅ Successfully rotated Gen3 key and updated K8s Secret: {secret_name}")
    except Exception as e:
        print(f"❌ Failed to update K8s Secret: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("This programme doesn't work - GEN3 doesn't allow this without much effort.")
    print("But the code/process is informative, so by all means, have a look.")
    sys.exit(1)
    rotate_gen3_key()
