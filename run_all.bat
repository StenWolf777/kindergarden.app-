@echo off
chcp 65001 > nul
title Bog'chaOS — Aqlli Bog'cha SaaS Tizimi
echo ========================================================
echo       Bog'chaOS SaaS Tizimini Ishga Tushirish
echo ========================================================
echo.
echo 1. FastAPI Backend server ishga tushirilmoqda (Port 8000)...
start "BogchaOS-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo 2. Frontend Dashboard veb-server ishga tushirilmoqda (Port 4321)...
start "BogchaOS-Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 4321"

timeout /t 2 > nul

echo 3. Brauzerda sahifalar ochilmoqda...
start http://localhost:4321/login.html
start http://127.0.0.1:8000/docs

echo.
echo ========================================================
echo [OK] Tizim to'liq ishga tushdi!
echo - Login Sahifasi: http://localhost:4321/login.html
echo - Admin Dashboard: http://localhost:4321/
echo - Backend API Docs (Swagger): http://127.0.0.1:8000/docs
echo ========================================================
pause
