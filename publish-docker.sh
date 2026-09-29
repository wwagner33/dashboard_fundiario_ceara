#!/bin/bash
# Builda e publica a imagem do dashboard_fundiario_ceara no Docker Hub.
#
# Uso: ./publish-docker.sh <versao>
# Ex.: ./publish-docker.sh 1.2.0
#
# Pré-requisito: estar logado no Docker Hub nesta máquina.
#   podman login docker.io -u wellingtonwfsarmento
# (este script nunca guarda usuário/senha/token — usa a sessão já autenticada)

set -euo pipefail

IMAGE="wellingtonwfsarmento/dashboard-fundiario-ceara"
VERSION="${1:?Uso: ./publish-docker.sh <versao, ex: 1.2.0>}"

cd "$(dirname "$0")"

# A imagem não leva mais o .streamlit/secrets.toml. Sem JWT_SECRET no ambiente
# do container, o dashboard não consegue autenticar no miniserver.
echo "A imagem não inclui o secrets.toml: o container precisa da variável JWT_SECRET."
read -r -p "O serviço dfundce no Portainer já tem JWT_SECRET definido (sem aspas)? [s/N] " resposta
if [[ ! "$resposta" =~ ^[sS]$ ]]; then
  echo "Defina JWT_SECRET no Portainer antes de publicar. Veja doc/rotacao_segredos.md." >&2
  exit 1
fi

if ! podman login --get-login docker.io >/dev/null 2>&1; then
  echo "Não logado no Docker Hub. Rode primeiro:" >&2
  echo "  podman login docker.io -u wellingtonwfsarmento" >&2
  exit 1
fi

echo "==> Build: $IMAGE:$VERSION"
podman build --format docker -f Dockerfile.dfundce -t "$IMAGE:$VERSION" -t "$IMAGE:latest" .

echo "==> Push: $IMAGE:$VERSION"
podman push "$IMAGE:$VERSION"

echo "==> Push: $IMAGE:latest"
podman push "$IMAGE:latest"

echo "==> Publicado: $IMAGE:$VERSION e $IMAGE:latest"
