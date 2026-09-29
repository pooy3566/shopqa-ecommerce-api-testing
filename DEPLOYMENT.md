# Deployment

The service runs on Azure Kubernetes Service. Infrastructure is Terraform
(`terraform/`), workloads are plain manifests (`k8s/`), and deploys run through
GitHub Actions (`.github/workflows/deploy.yml`).

## Architecture

    AKS            2 nodes, Standard_B2ps_v2 (Arm64), Free tier control plane
    Placement      nodes in separate availability zones
    App            2 replicas, one per node, RollingUpdate with maxUnavailable 0
    Database       Azure Database for PostgreSQL Flexible Server
    Registry       Azure Container Registry, admin user disabled; AKS pulls with
                   its kubelet managed identity, so no registry password exists
    Migrations     an alembic Job that must exit 0 before the app rolls
    Availability   PodDisruptionBudget with minAvailable 1

## Deploying

Pushing to `main` builds the image on a native Arm runner, pushes it tagged with
the commit sha, runs migrations to completion, rolls the Deployment, and then
verifies the result. The pipeline fails if migrations do not exit 0, if the
rollout stalls, if `/health` does not answer through the load balancer, or if the
two replicas are not on separate nodes.

`k8s/deploy.sh` performs the same sequence from a workstation.

## Design decisions

**Migrations are a Job, not part of app startup.** With two replicas, running
`alembic upgrade head` on boot means both pods start it against the same
database. Alembic locks, so the loser waits, and on a slow migration it fails its
readiness probe and is killed mid-migration. A Job is one pod, run once, that
must succeed before anything rolls.

**`maxUnavailable: 0` with `maxSurge: 1`.** A new pod reaches READY before an old
one is removed, so the desired replica count never drops during a deploy.

**`matchLabelKeys: [pod-template-hash]` on the topology spread constraint.**
Without it the constraint applies only at the instant of scheduling and stops
holding afterwards: during a rollout the outgoing ReplicaSet's pods still carry
`app=ecomapi`, so the scheduler balances new pods against pods that are about to
be deleted, and the survivors can end up on one node. Adding the pod template
hash scopes spreading to a single revision. The pipeline asserts the outcome on
every deploy rather than trusting the constraint.

**A PodDisruptionBudget, so node drains are safe.** Without one, draining a node
evicts its pods immediately. With `minAvailable: 1`, Kubernetes refuses an
eviction that would drop availability below one pod and waits instead.

**The application image is Arm64.** Every x64 2-vCPU VM family is unavailable in
this subscription, so the nodes are Arm and the image must match; an amd64 image
reaches the node and exits with `exec format error`. The CI job runs on
`ubuntu-24.04-arm` so the build is native rather than emulated.

**Region is constrained by policy.** An Azure Policy on the subscription limits
deployment to a fixed set of regions. `variables.tf` encodes that list in a
validation block, so an unsupported region fails immediately instead of returning
`403 RequestDisallowedByAzure` partway through an apply.

## Pipeline credentials

Workload identity federation would avoid storing a credential at all, and it
requires an Azure AD application registration that is not available in this
directory. Two credentials are therefore stored as repository secrets, each
scoped to the smallest useful permission:

| | Credential | What it can do |
|---|---|---|
| Registry | ACR repository-scoped token | push and pull one repository in one registry |
| Cluster | ServiceAccount bound by a namespaced Role (`k8s/ci-rbac.yaml`) | roll out this application in `default` |

The cluster identity is deliberately not the cluster-admin kubeconfig that
`az aks get-credentials` returns. It has no access to Secrets, so the pipeline
deploys the application without being able to read the database credentials it
deploys against. Verified with `kubectl auth can-i` in both directions:

```
patch deployments      yes        get secrets            no
create jobs            yes        list nodes             no
get pods               yes        create rolebindings    no
```

## Verified behaviour

A pod was deleted while 120 sequential requests ran against the public endpoint:

```
$ kubectl delete pod ecomapi-554764f767-bdspj
$ sort results | uniq -c
    120 200
```

No request failed. `maxUnavailable: 0` keeps a READY replica serving throughout,
and the Service routes only to READY pods.

## Setting it up

```
cd terraform
cp terraform.tfvars.example terraform.tfvars   # add your subscription id
terraform init && terraform apply
```

The application Secret is created once, out of band, so that no credential passes
through the repository or the pipeline:

```
kubectl create secret generic ecomapi-secrets \
  --from-literal=DATABASE_URL="$(terraform -chdir=terraform output -raw database_url)" \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)"
```

Then push to `main`, or run `k8s/deploy.sh`.

`terraform destroy` removes everything. The provider lock file is committed, so a
later rebuild resolves the same versions.
