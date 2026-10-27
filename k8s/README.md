# Kubernetes deployment

Runs Product Catalog v1, v2 and v3 side by side on the local **Docker Desktop Kubernetes** cluster (context `docker-desktop`, a kind-based single-node cluster).

| Version | Deployment | Service | URL | Image | Volume (PVC) |
|---|---|---|---|---|---|
| v1 | `product-catalog-v1` | `product-catalog-v1-service` | http://localhost:8081 | `shehfin/product-catalog:v1` | `product-catalog-v1-data` |
| v2 | `product-catalog-v2` | `product-catalog-v2-service` | http://localhost:8082 | `shehfin/product-catalog:v2` | `product-catalog-v2-data` |
| v3 | `product-catalog-v3` | `product-catalog-v3-service` | http://localhost:8083 | `shehfin/product-catalog:v3` | `product-catalog-v3-data` |

Everything is in the `product-catalog` namespace.

## Files

| File | Contents |
|---|---|
| `namespace.yaml` | The `product-catalog` namespace |
| `product-catalog-v1.yaml` | v1 PersistentVolumeClaim, Deployment and Service |
| `product-catalog-v2.yaml` | Same for v2 |
| `product-catalog-v3.yaml` | Same for v3 (probes use `/health`, sets `LOW_STOCK_THRESHOLD`) |
| `kustomization.yaml` | Lists the files above so `kubectl apply -k k8s/` applies them all |

## How localhost access works

The Services are `type: LoadBalancer`. On Docker Desktop's kind-based cluster, each LoadBalancer Service gets a small Envoy proxy container (`cloud-provider-kind`). That container publishes the Service port on the Windows host, so port 8081 of the Service becomes `http://localhost:8081`.

- **Why not NodePort?** Tested: NodePorts are not reachable from Windows `localhost` on this cluster type, and they would be in the 30000–32767 range anyway.
- **Why not `kubectl port-forward`?** It only works while a terminal keeps running it. The LoadBalancer mapping survives restarts.
- **The port must be free on Windows.** If another program already uses it, the Service shows `EXTERNAL-IP <pending>` and the namespace events show `SyncLoadBalancerFailed`. Jenkins was moved from 8081 to 8090 for this reason.
- **The proxy binds `0.0.0.0`.** Other devices on your network can reach these ports unless Windows Firewall blocks them.

## Design choices

| Setting | Value | Why |
|---|---|---|
| Storage | One 256Mi `ReadWriteOnce` PVC per version, mounted at `/app/data` (`DATABASE_PATH=/app/data/products.db`) | Each version has its own SQLite file, and data survives pod restarts. Default StorageClass `standard` (`rancher.io/local-path`). |
| Replicas and strategy | `replicas: 1`, `strategy: Recreate` | SQLite on a single-writer volume: the old pod stops before the new one starts, so two pods never write the same file |
| `imagePullPolicy` | `Always` | Jenkins republishes the same tag (`v1`, `v2`, `v3`) on every build, so a new pod should fetch the latest image. Layers already present are not downloaded again. |
| Readiness and liveness probes | v1, v2: `GET /`. v3: `GET /health` | v1 and v2 have no `/health`; their `/` page reads the database. v3's `/health` returns 503 if the database is unreadable. |
| Resources | requests `50m` CPU / `96Mi` memory; limits `500m` CPU / `256Mi` memory | Each pod runs gunicorn with 2 workers and uses well under 100Mi when idle |
| Security | `runAsNonRoot`, uid/gid 1000 (`appuser`), `fsGroup: 1000`, no privilege escalation, all Linux capabilities dropped | The container cannot gain root, and the volume is writable by the app user |
| `SECRET_KEY` | Read from Secret `product-catalog-secret` | Created with `kubectl` (below), never written into these files |

## Deploy

```powershell
# 1. Namespace
kubectl apply -f k8s/namespace.yaml

# 2. Secret with a random SECRET_KEY (run once; the value is never printed or saved to a file)
kubectl -n product-catalog create secret generic product-catalog-secret `
  --from-literal=SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 3. PVCs, Deployments and Services for v1, v2 and v3
kubectl apply -k k8s/

# 4. Wait until all three are ready
kubectl -n product-catalog rollout status deploy/product-catalog-v1
kubectl -n product-catalog rollout status deploy/product-catalog-v2
kubectl -n product-catalog rollout status deploy/product-catalog-v3
```

## Check

```powershell
kubectl -n product-catalog get deploy,svc,pvc,pods -o wide
kubectl -n product-catalog logs deploy/product-catalog-v3
kubectl -n product-catalog get events --field-selector type=Warning

# The image digest each pod is running
kubectl -n product-catalog get pods -o custom-columns=POD:.metadata.name,IMAGE:.status.containerStatuses[0].imageID

curl http://localhost:8081/
curl http://localhost:8082/
curl http://localhost:8083/health
```

## Update to the latest images

After Jenkins pushes a new image, restart the Deployment to pull it:

```powershell
kubectl -n product-catalog rollout restart deploy/product-catalog-v2
kubectl -n product-catalog rollout status deploy/product-catalog-v2
```

## Cleanup

These commands remove things. Run only what you mean to.

```powershell
# Stop the apps but KEEP the data (Deployments and Services only):
kubectl -n product-catalog delete deploy product-catalog-v1 product-catalog-v2 product-catalog-v3
kubectl -n product-catalog delete svc product-catalog-v1-service product-catalog-v2-service product-catalog-v3-service

# Remove ONE version including its database:
kubectl -n product-catalog delete deploy/product-catalog-v1 svc/product-catalog-v1-service pvc/product-catalog-v1-data

# Remove EVERYTHING, including all three databases and the Secret (cannot be undone):
kubectl delete namespace product-catalog
```

The StorageClass reclaim policy is `Delete`, so deleting a PVC permanently deletes that version's database.
