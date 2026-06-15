@echo off
chcp 65001 >nul
echo ========================================
echo   OBSERVATHON - DOCKER (Linux binary)
echo ========================================
echo.

:: Kiem tra Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop chua chay!
    echo Hay mo Docker Desktop roi chay lai file nay.
    pause
    exit /b 1
)
echo [OK] Docker dang chay!
echo.

set APIKEY=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
set LAB=c:\Users\Vrious\Desktop\Thư mục mới (2)\2A202600938-LamVanTai-Day13

echo [STEP 1] Pull python:3.12-slim image (lan dau mat 1-2 phut)...
docker pull python:3.12-slim
echo.

echo [STEP 2] Chay simulator...
echo.
docker run --rm ^
  -v "%LAB%:/lab" ^
  -e OPENAI_API_KEY=%APIKEY% ^
  python:3.12-slim ^
  bash -c "cd /lab && chmod +x bin/practice/observathon-sim && ./bin/practice/observathon-sim --config solution/config.json --wrapper solution/wrapper.py --out run_output.json --concurrency 2 --users 5 --turns 2"

echo.
echo ========================================
if exist "%LAB%\run_output.json" (
    echo [SUCCESS] Xong! run_output.json da duoc tao!
) else (
    echo [FAILED] Khong co output. Xem log tren.
)
echo ========================================
pause
