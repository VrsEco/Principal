#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Generates a self-signed certificate when none is provided.
# This prevents the nginx container from restarting in a loop during local
# development while still allowing real certificates to be mounted in prod.
# To disable this behaviour set SSL_AUTOGEN=0 in the nginx service env vars.
# ---------------------------------------------------------------------------

CERT_PATH="${SSL_CERTIFICATE_PATH:-/etc/nginx/ssl/fullchain.pem}"
KEY_PATH="${SSL_CERTIFICATE_KEY_PATH:-/etc/nginx/ssl/privkey.pem}"

if [ "${SSL_AUTOGEN:-1}" != "1" ]; then
  echo "nginx entrypoint: SSL auto-generation disabled (SSL_AUTOGEN=${SSL_AUTOGEN})."
  exit 0
fi

if [ -f "${CERT_PATH}" ] && [ -f "${KEY_PATH}" ]; then
  echo "nginx entrypoint: existing SSL certificate detected, skipping auto-generation."
  exit 0
fi

echo "nginx entrypoint: SSL certificate not found, generating self-signed certificate for development."
mkdir -p "$(dirname "${CERT_PATH}")"

openssl req -x509 -nodes \
  -days "${SSL_AUTOGEN_DAYS:-365}" \
  -newkey rsa:2048 \
  -keyout "${KEY_PATH}" \
  -out "${CERT_PATH}" \
  -subj "${SSL_AUTOGEN_SUBJECT:-/CN=localhost}" \
  -addext "subjectAltName=DNS:localhost" >/dev/null 2>&1

chmod 600 "${KEY_PATH}"
chmod 644 "${CERT_PATH}"

echo "nginx entrypoint: self-signed certificate generated at ${CERT_PATH}."
