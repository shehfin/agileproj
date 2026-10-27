# Jenkins CI/CD

The `Jenkinsfile` in this repository is a Declarative Pipeline. Jenkins runs it once for each branch through a **Multibranch Pipeline** job.

| Branch | Image pushed |
|---|---|
| `v1` | `shehfin/product-catalog:v1` |
| `v2` | `shehfin/product-catalog:v2` |
| `v3` | `shehfin/product-catalog:v3` |

## Pipeline stages

| # | Stage | What it does | If it fails |
|---|---|---|---|
| 1 | Checkout | Checks out the branch being built | Nothing else runs |
| 2 | Resolve version | Allows only `v1`, `v2` and `v3`; checks that `app/__init__.py` says `APP_VERSION = "<branch>"`; sets the image tag | Nothing is built |
| 3 | Install dependencies | Creates `.venv` and installs `requirements-dev.txt` | Shows a clear error naming the missing tool |
| 4 | Test | `pytest -v` and publishes a JUnit report | **The image is not built or pushed** |
| 5 | Build image | `docker build` with the commit ID as a label | Nothing is pushed |
| 6 | Smoke test image | Starts the new image and checks the page reports the right version | Nothing is pushed |
| 7 | Push to Docker Hub | Logs in using the Jenkins credential, pushes `:<branch>` and prints the digest | The error message names the credential to check |

The workspace is always cleaned afterwards. Docker Hub login uses a temporary Docker config folder inside the workspace, which is deleted, so the token is never saved on the Jenkins machine.

## Requirements

### Plugins

All of these were already installed on this Jenkins:

| Plugin | Used for |
|---|---|
| Pipeline (`workflow-aggregator`) | Declarative Pipeline, `bat`, `powershell` |
| Multibranch Pipeline (`workflow-multibranch`), Branch API | One job per branch, `BRANCH_NAME` |
| Git (`git`, `git-client`) | Checking out the GitHub repository |
| Credentials, Credentials Binding, Plain Credentials | `withCredentials` for Docker Hub |
| JUnit | Test Result report |
| Timestamper | `timestamps()` |
| Workspace Cleanup (`ws-cleanup`) | `cleanWs()` |

The Docker Pipeline plugin is **not** needed. The pipeline calls the `docker` command directly.

### Agent environment (this machine)

Jenkins runs as a Windows service under **LocalSystem**. That account cannot see your user PATH or Docker Desktop's normal connection. Set these under **Manage Jenkins → System → Global properties → Environment variables**:

| Name | Value |
|---|---|
| `PATH+PYTHON` | `C:\Users\Shehfin Sheharas\AppData\Local\Programs\Python\Python313` |
| `PATH+DOCKER` | `C:\Users\Shehfin Sheharas\AppData\Local\Programs\DockerDesktop\resources\bin` |
| `DOCKER_HOST` | `tcp://localhost:2375` |

`PATH+NAME` adds the folder to the front of `PATH` for every build.

`DOCKER_HOST` only works when Docker Desktop has **Settings → General → "Expose daemon on tcp://localhost:2375 without TLS"** turned on. That endpoint accepts connections only from this computer, and it has no authentication: any program on this PC can control Docker through it. That's acceptable for a local learning setup, but not for a shared or production server.

### Credentials

| ID | Kind | Username | Password |
|---|---|---|---|
| `dockerhub-credentials` | Username with password (Global) | `shehfin` | A Docker Hub **access token** with Read & Write scope, not your account password |

To add it: **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**.

No GitHub credential is needed while the repository is public. If it becomes private, add a GitHub token as a "Username with password" credential and select it in the job's branch source.

## Job configuration

1. **New Item** → name `product-catalog` → **Multibranch Pipeline**.
2. **Branch Sources → Add source → Git**:
   - Project Repository: `https://github.com/shehfin/agileproj.git`
   - Credentials: none (public repository)
   - Behaviours: **Discover branches**, plus **Filter by name (with wildcards)** with Include `v1 v2 v3`
3. **Build Configuration**: by Jenkinsfile, Script Path `Jenkinsfile`.
4. **Scan Multibranch Pipeline Triggers**: periodically, every 15 minutes. GitHub can't reach a Jenkins running on localhost, so polling replaces webhooks.
5. Save. Jenkins scans the repository and builds `v1`, `v2` and `v3`.

To rebuild one version: open `product-catalog` → `v2` → **Build Now**.
