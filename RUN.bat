@echo off
chcp 65001 >nul

echo ========================================
echo   OBSERVATHON - LAB 13
echo ========================================
echo.

:: Set API Key
set OPENAI_API_KEY=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

:: Copy project ra duong dan khong dau
echo [1/3] Copying project to C:\lab13 ...
robocopy "c:\Users\Vrious\Desktop\Thư mục mới (2)\2A202600938-LamVanTai-Day13" "C:\lab13" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
echo Done!

:: Unblock tat ca files
echo [2/3] Unblocking files ...
powershell -Command "Get-ChildItem -Recurse 'C:\lab13' | Unblock-File -ErrorAction SilentlyContinue"
echo Done!

:: Chay simulator
echo [3/3] Running simulator ...
echo.
cd /d C:\lab13
observathon-sim\observathon-sim.exe --config solution\config.json --wrapper solution\wrapper.py --out run_output.json --concurrency 2 --users 5 --turns 2

echo.
echo ========================================
echo   DONE! Ket qua: C:\lab13\run_output.json
echo   Copy ket qua ve workspace...
echo ========================================

:: Copy ket qua ve workspace goc
copy /Y "C:\lab13\run_output.json" "c:\Users\Vrious\Desktop\Thư mục mới (2)\2A202600938-LamVanTai-Day13\run_output.json" >nul
echo Copied run_output.json back!

pause
