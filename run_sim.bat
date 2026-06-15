@echo off
set OPENAI_API_KEY=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

echo Starting Observathon Simulator...
echo Config: solution\config.json
echo Wrapper: solution\wrapper.py
echo.

observathon-sim.exe --config solution\config.json --wrapper solution\wrapper.py --out run_output.json --concurrency 2 --users 5 --turns 2

echo.
echo Done! Check run_output.json for results.
pause
