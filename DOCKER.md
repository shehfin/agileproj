# Docker images and Docker Hub

Images are published at **https://hub.docker.com/r/shehfin/product-catalog** (public).

| Tag | Git branch | App version |
|---|---|---|
| `shehfin/product-catalog:v1` | `v1` | Add, view, search |
| `shehfin/product-catalog:v2` | `v2` | + edit, delete, validation, UI |
| `shehfin/product-catalog:v3` | `v3` | + dashboard, sort/filter, low stock, `/health` |

Every image has these labels:

- `org.opencontainers.image.version`: the app version
- `org.opencontainers.image.revision`: the full Git commit it was built from

To see them:

```powershell
docker inspect -f "{{json .Config.Labels}}" shehfin/product-catalog:v3
```

## What is in the image

| Item | Value |
|---|---|
| Base image | `python:3.13-slim` |
| User | `appuser` (not root) |
| Server | gunicorn, 2 workers, `0.0.0.0:5000` |
| Port | `5000` |
| Database | SQLite at `/app/data/products.db`; mount a volume on `/app/data` to keep data |
| Contents | `app/` and `requirements.txt` only (see `.dockerignore`) |
| Health check | v3 only: `HEALTHCHECK` calls `GET /health`. v1 and v2 have no `/health`. |
| Secrets | None baked in. Pass `SECRET_KEY` at run time. |

Runtime settings (environment variables):

| Variable | Versions | Default |
|---|---|---|
| `SECRET_KEY` | all | `dev-only-change-me` (set a random value outside local use) |
| `DATABASE_PATH` | all | `/app/data/products.db` |
| `LOW_STOCK_THRESHOLD` | v3 | `10` |

## Build

Build each tag from its own branch. `git archive` exports exactly the committed files of that branch, so local changes or untracked files can't sneak in:

```bash
for b in v1 v2 v3; do
  rm -rf build/$b && mkdir -p build/$b
  git archive origin/$b | tar -x -C build/$b
  (cd build/$b && python -m pytest -q)            # test before building
  docker build \
    --label org.opencontainers.image.revision=$(git rev-parse origin/$b) \
    --label org.opencontainers.image.source=https://github.com/shehfin/agileproj \
    -t shehfin/product-catalog:$b build/$b
done
```

To build only the branch you have checked out:

```powershell
git checkout v3
docker build -t shehfin/product-catalog:v3 .
```

## Run

```powershell
docker run -d --name product-catalog-v3 -p 5000:5000 `
  -v product-catalog-v3-data:/app/data `
  -e SECRET_KEY=<random-string> `
  shehfin/product-catalog:v3
```

Open http://localhost:5000. To run all three versions side by side, use different host ports and volumes:

```powershell
docker run -d --name product-catalog-v1 -p 5001:5000 -v product-catalog-v1-data:/app/data shehfin/product-catalog:v1
docker run -d --name product-catalog-v2 -p 5002:5000 -v product-catalog-v2-data:/app/data shehfin/product-catalog:v2
docker run -d --name product-catalog-v3 -p 5003:5000 -v product-catalog-v3-data:/app/data shehfin/product-catalog:v3
```

Check, then clean up:

```powershell
docker ps --filter name=product-catalog
docker logs product-catalog-v3
docker inspect -f "{{.State.Health.Status}}" product-catalog-v3   # v3 only
docker rm -f product-catalog-v1 product-catalog-v2 product-catalog-v3
```

## Publish to Docker Hub

Log in with a Docker Hub **access token**, not your password. Create one at hub.docker.com → Account settings → Personal access tokens, with Read & Write access.

```powershell
docker login -u shehfin
# paste the token when prompted; it is stored by the Docker credential helper, not in a file
```

In scripts and CI, read the token from a secret and pass it on standard input, so it never appears in the command line or logs:

```bash
echo "$DOCKERHUB_TOKEN" | docker login -u shehfin --password-stdin
```

Push:

```powershell
docker push shehfin/product-catalog:v1
docker push shehfin/product-catalog:v2
docker push shehfin/product-catalog:v3
```

## Verify a published tag

```powershell
docker rmi shehfin/product-catalog:v3
docker pull shehfin/product-catalog:v3
docker inspect -f "{{index .RepoDigests 0}}" shehfin/product-catalog:v3
```

The digest printed by `docker push` and the one from `docker pull` must be the same.
