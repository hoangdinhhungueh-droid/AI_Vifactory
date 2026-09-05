#!/usr/bin/env python3
"""
vf_cf_access_validator.py — Validate Cloudflare Access JWT (Zero Trust, secretless origin).
Created 25/08/2026 for claude.vifactory.com MCP ingress (Access App 0925616a-7d4d-4090-becb-2b2341d83b65).

Library use: validate_token(token, expected_aud) -> (ok: bool, reason: str)
CLI use:     echo "$JWT" | python3 vf_cf_access_validator.py <expected_aud>   (exit 0 = valid)
"""
import sys, json, urllib.request

TEAM_DOMAIN = "late-frog-8b92.cloudflareaccess.com"
CERTS_URL = f"https://{TEAM_DOMAIN}/cdn-cgi/access/certs"

def validate_token(token: str, expected_aud: str):
    """Return (ok, reason). ok=True only if signature/aud/iss all pass."""
    if not token:
        return False, "INVALID: empty token"
    try:
        import jwt
        from jwt import PyJWKClient
        jwks_client = PyJWKClient(CERTS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=expected_aud,
            issuer=f"https://{TEAM_DOMAIN}",
        )
    except Exception as e:
        return False, f"INVALID: {type(e).__name__}: {e}"

    if claims.get("aud") != expected_aud:
        return False, "INVALID: aud mismatch"
    return True, "VALID " + json.dumps({
        "common_name": claims.get("common_name"),
        "expires": claims.get("exp"),
    })

def main():
    if len(sys.argv) != 2:
        print("usage: vf_cf_access_validator.py <expected_aud>", file=sys.stderr)
        sys.exit(1)
    token = sys.stdin.read().strip()
    ok, reason = validate_token(token, sys.argv[1])
    print(reason, file=sys.stderr if not ok else sys.stdout)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
