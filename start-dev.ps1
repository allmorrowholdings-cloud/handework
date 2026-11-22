Set-Location $PSScriptRoot

Write-Host "Starting MySQL and Redis..."
docker compose up -d mysql redis

Write-Host "Waiting for MySQL to be healthy..."
do {
    Start-Sleep -Seconds 2
    $status = docker inspect --format='{{.State.Health.Status}}' handework-mysql-1
} until ($status -eq "healthy")

Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\.venv\Scripts\Activate.ps1; flask --app wsgi:app run --debug"

Write-Host "Starting frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; npm run dev"

Write-Host "Done. Backend: http://127.0.0.1:5000  Frontend: http://localhost:5173"