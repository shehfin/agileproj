// Product Catalog CI/CD pipeline (Declarative).
//
// Branch -> image:  v1 -> shehfin/product-catalog:v1
//                   v2 -> shehfin/product-catalog:v2
//                   v3 -> shehfin/product-catalog:v3
//
// Stages run in order and stop at the first failure, so an image is only
// built after the tests pass, and only pushed after the built image starts.
//
// Runs on a Windows agent. The agent needs (Manage Jenkins > System >
// Global properties > Environment variables), see JENKINS.md:
//   PATH+PYTHON   folder containing python.exe (3.13)
//   PATH+DOCKER   folder containing docker.exe
//   DOCKER_HOST   Docker daemon address, e.g. tcp://localhost:2375
// and a "Username with password" credential with the ID below, whose
// password is a Docker Hub access token.

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        IMAGE_REPO = 'shehfin/product-catalog'
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub-credentials'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONDONTWRITEBYTECODE = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def scmVars = checkout scm
                    env.GIT_COMMIT = scmVars.GIT_COMMIT
                    env.GIT_SHORT = scmVars.GIT_COMMIT.substring(0, 7)
                }
                echo "Checked out branch ${env.BRANCH_NAME} at commit ${env.GIT_COMMIT}"
            }
        }

        stage('Resolve version') {
            steps {
                script {
                    def branch = env.BRANCH_NAME
                    if (!['v1', 'v2', 'v3'].contains(branch)) {
                        error("Branch '${branch}' is not a release branch. Only v1, v2 and v3 produce images.")
                    }
                    // The code on this branch must say it is this version, so a
                    // mis-merged branch can never publish under the wrong tag.
                    def marker = "APP_VERSION = \"${branch}\""
                    if (!readFile('app/__init__.py').contains(marker)) {
                        error("app/__init__.py on branch ${branch} does not contain ${marker}. Refusing to publish a mismatched image.")
                    }
                    env.IMAGE_TAG = branch
                    env.IMAGE = "${env.IMAGE_REPO}:${branch}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${branch} @ ${env.GIT_SHORT}"
                }
                echo "This build will test, build and publish ${env.IMAGE}"
            }
        }

        stage('Install dependencies') {
            steps {
                bat '''
                    @echo off
                    where python >nul 2>nul || (echo ERROR: python.exe is not on the agent PATH. Set PATH+PYTHON in Manage Jenkins - System - Global properties. & exit /b 1)
                    python --version
                    python -m venv .venv || (echo ERROR: could not create the virtual environment. & exit /b 1)
                    .venv\\Scripts\\python -m pip install --quiet -r requirements-dev.txt || (echo ERROR: pip install failed. Check the agent's internet access and requirements-dev.txt. & exit /b 1)
                    .venv\\Scripts\\python -m pip list --format=freeze | findstr /I /B "flask= gunicorn= pytest="
                '''
            }
        }

        stage('Test') {
            steps {
                bat '.venv\\Scripts\\python -m pytest -v --junitxml=test-results\\junit.xml'
            }
            post {
                always {
                    junit testResults: 'test-results/junit.xml', allowEmptyResults: true
                }
                failure {
                    echo 'Tests failed, so the Docker image will NOT be built or pushed. See "Test Result" for the failing tests.'
                }
            }
        }

        stage('Build image') {
            steps {
                bat '''
                    @echo off
                    where docker >nul 2>nul || (echo ERROR: docker.exe is not on the agent PATH. Set PATH+DOCKER in Manage Jenkins - System - Global properties. & exit /b 1)
                    docker version --format "Docker client {{.Client.Version}}, daemon {{.Server.Version}}" || (echo ERROR: cannot reach the Docker daemon at %DOCKER_HOST%. Is Docker Desktop running with "Expose daemon on tcp://localhost:2375 without TLS" enabled? & exit /b 1)
                    docker build --pull ^
                        --label org.opencontainers.image.revision=%GIT_COMMIT% ^
                        --label org.opencontainers.image.source=https://github.com/shehfin/agileproj ^
                        -t %IMAGE% . || (echo ERROR: docker build failed. & exit /b 1)
                    docker image inspect %IMAGE% --format "Built %IMAGE%  id={{.Id}}"
                '''
            }
        }

        stage('Smoke test image') {
            steps {
                powershell '''
                    # Start the new image, check it answers and reports the right version, then remove it.
                    $cid = docker run -d -P $env:IMAGE
                    if ($LASTEXITCODE -ne 0) { throw "Could not start a container from $env:IMAGE." }
                    try {
                        $port = ((docker port $cid 5000/tcp) | Select-Object -First 1).Split(':')[-1]
                        # 127.0.0.1, not localhost: localhost tries IPv6 (::1) first, which
                        # the published port doesn't answer, and costs ~2 s per request.
                        $page = $null
                        for ($i = 0; $i -lt 30 -and -not $page; $i++) {
                            try { $page = Invoke-WebRequest "http://127.0.0.1:$port/" -UseBasicParsing -TimeoutSec 5 }
                            catch { Start-Sleep -Seconds 1 }
                        }
                        if (-not $page) {
                            docker logs $cid
                            throw "The container did not answer on port $port within 30 seconds (logs above)."
                        }
                        if ($page.Content -notmatch "Product Catalog $env:IMAGE_TAG") {
                            throw "The running app does not report version $env:IMAGE_TAG."
                        }
                        Write-Output "Container answered HTTP $($page.StatusCode) and reports Product Catalog $env:IMAGE_TAG."
                    }
                    finally {
                        docker rm -f $cid | Out-Null
                    }
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID,
                                                  usernameVariable: 'DOCKERHUB_USER',
                                                  passwordVariable: 'DOCKERHUB_TOKEN')]) {
                    // cmd.exe, not PowerShell: Jenkins' PowerShell wrapper puts a UTF-8
                    // byte-order mark in front of text piped to programs, so docker
                    // received BOM + token and Docker Hub rejected it. "echo X|" sends
                    // exactly X plus CR LF, which docker trims. (Docker Hub access
                    // tokens only contain A-Z a-z 0-9 _ -, so echo needs no escaping.)
                    // A throwaway DOCKER_CONFIG keeps the login out of the service profile.
                    bat '''
                        @echo off
                        set "DOCKER_CONFIG=%WORKSPACE%\\.docker-config"
                        if not exist "%DOCKER_CONFIG%" mkdir "%DOCKER_CONFIG%"

                        echo %DOCKERHUB_TOKEN%| docker login --username %DOCKERHUB_USER% --password-stdin
                        if errorlevel 1 (
                            rmdir /s /q "%DOCKER_CONFIG%"
                            echo ERROR: Docker Hub login failed for %DOCKERHUB_USER%. Check the Jenkins credential %DOCKERHUB_CREDENTIALS_ID% - its password must be a Docker Hub access token with Read and Write scope.
                            exit /b 1
                        )

                        docker push %IMAGE%
                        set PUSH_EXIT=%ERRORLEVEL%
                        docker logout >nul
                        rmdir /s /q "%DOCKER_CONFIG%"
                        if not "%PUSH_EXIT%"=="0" (
                            echo ERROR: docker push %IMAGE% failed - see the output above.
                            exit /b 1
                        )
                        echo Published %IMAGE%
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "SUCCESS: tests passed and ${env.IMAGE} (commit ${env.GIT_SHORT}) was pushed to Docker Hub."
        }
        failure {
            echo 'FAILED: see the stage marked in red. Stages after it did not run, so nothing was pushed unless the failure was after "Push to Docker Hub".'
        }
        always {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
    }
}
