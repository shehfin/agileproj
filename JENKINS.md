# Jenkins CI/CD

The `Jenkinsfile` in this repository is a Declarative Pipeline. Jenkins runs it once for each branch through a **Multibranch Pipeline** job.

**Jenkins URL on this machine: http://localhost:8090.** Jenkins was moved off 8081 so that port can serve Product Catalog v1 from Kubernetes (see `k8s/README.md`). Port 8080 is used by a local Oracle database.

| Branch | Image pushed |
|---|---|
| `v1` | `shehfin/product-catalog:v1` |
| `v2` | `shehfin/product-catalog:v2` |
| `v3` | `shehfin/product-catalog:v3` |

## Pipeline stages

| # | Stage | Step type | What it does | If it fails |
|---|---|---|---|---|
| 1 | Checkout | `checkout scm` | Checks out the branch being built | Nothing else runs |
| 2 | Resolve version | Groovy | Allows only `v1`, `v2` and `v3`; checks that `app/__init__.py` says `APP_VERSION = "<branch>"`; sets the image tag | Nothing is built |
| 3 | Install dependencies | `bat` | Creates `.venv` and installs `requirements-dev.txt` | Shows a clear error naming the missing tool |
| 4 | Test | `bat` | `pytest -v` and publishes a JUnit report | **The image is not built or pushed** |
| 5 | Build image | `bat` | `docker build` with the commit ID as a label | Nothing is pushed |
| 6 | Smoke test image | `powershell` | Starts the new image and checks the page reports the right version | Nothing is pushed |
| 7 | Push to Docker Hub | `bat` | Logs in using the Jenkins credential, pushes `:<branch>`, logs out | The error message names the credential to check |

The workspace is always cleaned afterwards. Docker Hub login uses a temporary Docker config folder inside the workspace, which is deleted, so the token is never saved on the Jenkins machine.

### Verified behaviour

- **All three branches:** builds passed every stage, including the push.
- **Docker Hub matches Jenkins:** each pushed digest matched the one Docker Hub reports, and the pulled image served its own version.
- **Failing tests stop the pipeline:** a replayed v1 build with one deliberately failing test failed at **Test**. Build image, Smoke test image and Push to Docker Hub were skipped, and the Docker Hub digest did not change.

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

## Changing the Jenkins port

The port is set in `C:\Program Files\Jenkins\jenkins.xml` (`--httpPort=8090`). Editing it needs an Administrator PowerShell:

```powershell
$f = "C:\Program Files\Jenkins\jenkins.xml"
(Get-Content $f) -replace '--httpPort=\d+', '--httpPort=8090' | Set-Content $f
Restart-Service Jenkins
```

Afterwards, update **Manage Jenkins → System → Jenkins URL** to match.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Push stage: `unauthorized: incorrect username or password`, although the token is valid | Text piped to a program from a Jenkins `powershell` step gets a UTF-8 byte-order mark (BOM) in front. `docker login` then receives BOM + token. Setting `$OutputEncoding` inside the step does **not** fix it. | Do the login in a `bat` step: `echo %DOCKERHUB_TOKEN%\| docker login --username %DOCKERHUB_USER% --password-stdin` (this is what the Jenkinsfile does) |
| `python.exe is not on the agent PATH` / `docker.exe is not on the agent PATH` | LocalSystem doesn't see your user PATH | Set `PATH+PYTHON` and `PATH+DOCKER` (above) |
| `cannot reach the Docker daemon` | Docker Desktop is stopped, or the 2375 setting is off | Start Docker Desktop and enable "Expose daemon on tcp://localhost:2375" |
| Smoke test times out although the container is running | `localhost` resolves to IPv6 `::1` first, which the published port does not answer | The Jenkinsfile uses `127.0.0.1` |
| `python -m venv` fails in `ensurepip` | Workspace path too long (Windows 260-character limit) | Keep job and folder names short |
| API calls to `localhost:8080` return 401 with `realm="XDB"` | That's Oracle, not Jenkins | Use http://localhost:8090 |
