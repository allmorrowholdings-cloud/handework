$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$backendPath = Join-Path $PSScriptRoot "backend"
$python = Join-Path $backendPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "The backend Python environment is missing. See docs/WINDOWS_LOCAL_SETUP.md."
}
if (-not (Test-Path -LiteralPath "node_modules\.bin\vite.cmd")) {
    throw "The web dependencies are missing. Run npm ci."
}

Write-Host "Starting MySQL and Redis..."
docker compose up -d --wait --wait-timeout 120 mysql redis
if ($LASTEXITCODE -ne 0) {
    throw "MySQL or Redis could not start. Check Docker Desktop and docker compose logs."
}

Push-Location -LiteralPath $backendPath
try {
    & $python -m flask --app 'handework:create_app(seed_development_admin=False)' db upgrade
    if ($LASTEXITCODE -ne 0) { throw "The database migration failed." }
} finally {
    Pop-Location
}

Start-Process -FilePath $python -WorkingDirectory $backendPath -ArgumentList "-m", "flask", "--app", "wsgi:app", "run" -WindowStyle Hidden
Write-Host "API launching at http://127.0.0.1:5000"
npm.cmd run dev -- --strictPort
if ($LASTEXITCODE -ne 0) { throw "The web development server failed to start." }
