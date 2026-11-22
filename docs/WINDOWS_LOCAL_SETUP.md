# Run handEwork on Windows PowerShell

These commands assume the ZIP is extracted to `C:\handework`. Change that path if you use another folder.

## 1. Install once

Install:

- Git for Windows
- Node.js 22 LTS or the exact version in `.node-version`
- Python 3.13
- Docker Desktop with WSL 2
- Android Studio for an Android emulator
- VS Code if you want an editor

Confirm the tools:

```powershell
git --version
node --version
npm --version
py -3.13 --version
docker --version
```

## 2. Open the project

```powershell
Set-Location C:\handework
Get-ChildItem
```

You should see `app`, `backend`, `mobile`, `docs`, `package.json`, `docker-compose.yml` and `render.yaml`.

## 3. Create local environment files

Secrets are excluded from the ZIP. Copy the templates, then paste the values from the environment you already prepared.

```powershell
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
Copy-Item mobile\.env.example mobile\.env
notepad .env
notepad backend\.env
notepad mobile\.env
```

Use these local URLs:

```text
# root .env
NEXT_PUBLIC_API_URL=http://localhost:5000

# backend .env
DATABASE_URL=mysql+pymysql://handework:handework_local_password@127.0.0.1:3306/handework
REDIS_URL=redis://127.0.0.1:6379/0
WEB_ORIGINS=http://localhost:3000,http://localhost:4173

# mobile .env, Android emulator
EXPO_PUBLIC_API_URL=http://10.0.2.2:5000
```

Generate local secrets in PowerShell:

```powershell
[Convert]::ToBase64String((1..64 | ForEach-Object { Get-Random -Maximum 256 }))
```

Generate it twice. Use different values for `SECRET_KEY` and `JWT_SECRET_KEY`.

## 4. Start MySQL and Redis

Open Docker Desktop and wait until it says the engine is running. Then:

```powershell
Set-Location C:\handework
docker compose up -d mysql redis
docker compose ps
```

Both services must be healthy or running.

To view database logs:

```powershell
docker compose logs mysql
```

## 5. Start the Flask API

Open a second PowerShell window:

```powershell
Set-Location C:\handework\backend
py -3.13 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
flask --app wsgi:app db upgrade
flask --app wsgi:app run --debug --host 0.0.0.0 --port 5000
```

Check the API in another PowerShell window:

```powershell
Invoke-RestMethod http://localhost:5000/v1/health
```

Expected result: `status` and `database` are `ok`.

## 6. Start the web application

Open a third PowerShell window:

```powershell
Set-Location C:\handework
npm ci
npm run dev -- --host 0.0.0.0 --port 3000
```

Open `http://localhost:3000`.

### Web checks

1. Create a customer account.
2. Create an artisan account in a different private browser window.
3. Confirm the artisan is not public before verification.
4. Use the administrator process to approve verification.
5. Add availability and a portfolio item.
6. Search as the customer.
7. Create a booking and quote.
8. Use Paystack test mode before any live-money test.

## 7. Create the first administrator

Set temporary values only in the current PowerShell window:

```powershell
Set-Location C:\handework\backend
.\.venv\Scripts\Activate.ps1
$env:ADMIN_EMAIL="your-admin-email@example.com"
$env:ADMIN_PHONE="+233XXXXXXXXX"
$env:ADMIN_PASSWORD="use-a-long-unique-password"
$env:ADMIN_FIRST_NAME="handEwork"
$env:ADMIN_LAST_NAME="Operations"
python scripts\create_admin.py
Remove-Item Env:ADMIN_PASSWORD
```

Do not put the administrator password in Git or a screenshot.

## 8. Test Android from Windows

handEwork uses native Mapbox and push modules. Use a development build. Expo Go is not enough.

```powershell
Set-Location C:\handework\mobile
npm ci
npx eas-cli@latest login
npx eas-cli@latest init
```

Copy the project ID returned by EAS into `mobile\app.json` under `extra.eas.projectId`.

Build the Android development app:

```powershell
npx eas-cli@latest build --platform android --profile development
```

Install the returned APK on the emulator or Android phone. Then start the JavaScript server:

```powershell
npx expo start --dev-client
```

### Android emulator API address

Use:

```text
EXPO_PUBLIC_API_URL=http://10.0.2.2:5000
```

### Physical Android phone API address

Connect the phone and computer to the same Wi-Fi. Find the computer IPv4 address:

```powershell
ipconfig
```

If the computer address is `192.168.1.25`, use:

```text
EXPO_PUBLIC_API_URL=http://192.168.1.25:5000
```

Allow Python port 5000 through Windows Firewall only on the private network. Restart `npx expo start --dev-client` after changing `.env`.

## 9. Test iOS while using Windows

Windows cannot run Xcode or the iOS simulator. EAS can build iOS in the cloud.

```powershell
Set-Location C:\handework\mobile
npx eas-cli@latest build --platform ios --profile development
```

You need an Apple Developer account and a registered test device for an internal iOS build. For a wider test group, create a production build and use TestFlight.

## 10. Run all checks

```powershell
# Web
Set-Location C:\handework
npm run lint
npm run build

# API
Set-Location C:\handework\backend
.\.venv\Scripts\Activate.ps1
pytest

# Mobile
Set-Location C:\handework\mobile
npm run typecheck
```

Do not push until all three pass.

## 11. Stop local services

Press `Ctrl+C` in the API, web and Expo windows. Then:

```powershell
Set-Location C:\handework
docker compose stop
```

`docker compose stop` keeps local database data. `docker compose down -v` deletes it and should not be used on a database you need.
