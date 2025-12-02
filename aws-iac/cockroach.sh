#!/bin/bash
set -ex

# Log para debug
exec > /var/log/userdata.log 2>&1

echo "==> Obtendo IP privado da EC2..."
LOCAL_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
echo "IP privado detectado: $LOCAL_IP"

echo "==> Atualizando pacotes..."
apt-get update -y

echo "==> Instalando dependências..."
apt-get install -y wget tar

echo "==> Baixando CockroachDB..."
wget https://binaries.cockroachdb.com/cockroach-v24.1.1.linux-amd64.tgz -O cockroach.tgz
tar xzf cockroach.tgz
cp cockroach-v24.1.1.linux-amd64/cockroach /usr/local/bin/
chmod +x /usr/local/bin/cockroach

echo "==> Criando diretórios de dados..."
mkdir -p /var/lib/cockroach
chown -R ubuntu:ubuntu /var/lib/cockroach

echo "==> Criando serviço systemd..."
tee /etc/systemd/system/cockroach.service > /dev/null <<EOF
[Unit]
Description=CockroachDB Server
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
ExecStart=/usr/local/bin/cockroach start-single-node \
  --store=/var/lib/cockroach \
  --advertise-addr=${LOCAL_IP} \
  --listen-addr=${LOCAL_IP}:26257 \
  --http-addr=${LOCAL_IP}:8080 \
  --insecure \
  --background=false
Restart=always
LimitNOFILE=35000

[Install]
WantedBy=multi-user.target
EOF

echo "==> Recarregando systemd..."
systemctl daemon-reload

echo "==> Iniciando CockroachDB..."
systemctl start cockroach
systemctl enable cockroach

echo "==> CockroachDB instalado e rodando!"
echo "Acesse a UI em http://${LOCAL_IP}:8080"
