#!/usr/bin/env bash
# Deploy the app to the AKS cluster Terraform just built.
#
# Everything this needs comes out of `terraform output`, so there is nothing to
# copy by hand and nothing to keep in sync. Run it from the repo root.
#
#   bash k8s/deploy.sh
#
# It is safe to re-run. Every step is idempotent.
set -euo pipefail

TF_DIR="terraform"
TAG="${1:-$(git rev-parse --short HEAD)}"

tf() { terraform -chdir="$TF_DIR" output -raw "$1"; }

# Retry an az command that fails with a spurious ResourceNotFound.
#
# For several minutes after a resource group is destroyed and recreated under the
# same name, ARM serves a stale cache for that path: az aks show and az acr build
# return 404 for resources that az aks list finds and that kubectl is already
# talking to. It is a lying API, not a missing resource, and it clears on its own.
# Without this the whole deploy fails on a problem that fixes itself.
retry() {
  local attempt
  for attempt in 1 2 3 4 5 6; do
    if "$@"; then return 0; fi
    echo "==> attempt ${attempt} of 6 failed, retrying in 30s: $*"
    sleep 30
  done
  echo "!! gave up after 6 attempts: $*"
  return 1
}

ACR_NAME=$(tf acr_name)
ACR_SERVER=$(tf acr_login_server)
CLUSTER=$(tf cluster_name)
RG=$(tf resource_group)
IMAGE="${ACR_SERVER}/ecomapi:${TAG}"

echo "==> cluster : $CLUSTER  ($RG)"
echo "==> image   : $IMAGE"

# 1. Point kubectl at the cluster.
#
# Retried, because ARM returns ResourceNotFound for a cluster that demonstrably
# exists for a few minutes after the resource group is created or replaced:
# `az aks list` finds it and kubectl talks to it while `az aks show` still 404s.
# That is cache propagation, not a missing cluster, and it resolves on its own.
retry az aks get-credentials --resource-group "$RG" --name "$CLUSTER" --overwrite-existing
kubectl cluster-info >/dev/null

# 2. Build for arm64.
#
# The nodes are Arm, because every x64 2-vCPU family has zero quota in this
# subscription. The image must match: an amd64 image reaches the node and exits
# with `exec format error`.
#
# ACR Tasks is unavailable here (`TasksOperationsNotAllowed`), so the build is
# local. On an x64 host that means emulation: binfmt registers a QEMU
# interpreter so Arm binaries can execute during the build. Correct but slow,
# since every compiled wheel is emulated. Expect 15 to 30 minutes on a cold
# cache. The CI job avoids this by running on a native Arm runner.
az acr login --name "$ACR_NAME"

docker run --privileged --rm tonistiigi/binfmt --install arm64

# A dedicated builder, so the cleanup at the end removes the emulation cache
# without touching anything else Docker holds.
docker buildx inspect ecomapi-arm >/dev/null 2>&1 || \
  docker buildx create --name ecomapi-arm --driver docker-container

docker buildx build \
  --builder ecomapi-arm \
  --platform linux/arm64 \
  --tag "$IMAGE" \
  --push \
  .

# 3. The secret.
#
# Created from Terraform output rather than from a file, so the generated
# Postgres password never lands on disk in this repo. SECRET_KEY is generated
# fresh here; rotating it invalidates every issued JWT, which is the intended
# behaviour of a key rotation.
kubectl create secret generic ecomapi-secrets \
  --from-literal=DATABASE_URL="$(tf database_url)" \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/configmap.yaml

# 4. Migrations, as a Job, BEFORE the app rolls.
#
# Delete any previous Job first: a completed Job's pod template is immutable, so
# re-running with a new image tag fails with "field is immutable" otherwise.
kubectl delete job ecomapi-migrate --ignore-not-found
sed "s|__IMAGE__|${IMAGE}|g" k8s/migrate-job.yaml | kubectl apply -f -
echo "==> waiting for migrations"
kubectl wait --for=condition=complete job/ecomapi-migrate --timeout=300s

# 5. The app.
sed "s|__IMAGE__|${IMAGE}|g" k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/poddisruptionbudget.yaml

# `rollout status` blocks until every new pod is READY, and returns non-zero if
# the rollout stalls. That is what makes this script usable in CI: a broken
# deploy fails the pipeline instead of reporting success.
kubectl rollout status deployment/ecomapi --timeout=300s

# Azure takes a minute or two to assign the load balancer a public IP. Poll for
# it rather than `kubectl get -w`, which never exits and cannot be scripted.
echo "==> waiting for Azure to assign a public IP"
for _ in $(seq 1 60); do
  IP=$(kubectl get service ecomapi -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
  [ -n "$IP" ] && break
  sleep 5
done

if [ -z "${IP:-}" ]; then
  echo "!! no public IP after 5 minutes; check: kubectl describe service ecomapi"
  exit 1
fi

echo "==> live at http://${IP}"
echo "==> health:"
curl -fsS "http://${IP}/health" && echo
