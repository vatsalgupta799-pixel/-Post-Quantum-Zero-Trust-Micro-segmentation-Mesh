#!/usr/bin/env bash
set -euo pipefail

CERT="/tmp/pqc-cert.pem"
KEY="/tmp/pqc-key.pem"

openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
  -keyout "$KEY" \
  -out "$CERT" \
  -days 365 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$KEY"
chmod 644 "$CERT"

echo "Test certificate created: $CERT"
echo "Test private key created: $KEY"
echo "Do not upload the private key to GitHub."
