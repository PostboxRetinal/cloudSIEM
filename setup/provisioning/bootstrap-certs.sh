#!/usr/bin/env sh
set -eu
set -o pipefail 2>/dev/null || true

CERT_DIR="config/certs"
INSTANCES_FILE="/setup/provisioning/cert-instances.yml"

cd /usr/share/elasticsearch
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/ca.zip" ]; then
  echo "Generando CA..."
  bin/elasticsearch-certutil ca --silent --pem -out "$CERT_DIR/ca.zip"
  unzip "$CERT_DIR/ca.zip" -d "$CERT_DIR"
fi

if [ ! -f "$CERT_DIR/certs.zip" ]; then
  echo "Generando certificados de nodos..."
  cp "$INSTANCES_FILE" "$CERT_DIR/instances.yml"
  bin/elasticsearch-certutil cert --silent --pem \
    -out "$CERT_DIR/certs.zip" \
    --in "$CERT_DIR/instances.yml" \
    --ca-cert "$CERT_DIR/ca/ca.crt" \
    --ca-key "$CERT_DIR/ca/ca.key"
  unzip "$CERT_DIR/certs.zip" -d "$CERT_DIR"
fi

echo "Ajustando permisos de certificados..."
chown -R root:root "$CERT_DIR"
chmod -R 644 "$CERT_DIR"
find "$CERT_DIR" -type d -exec chmod 755 {} \;
echo "Setup completado."
