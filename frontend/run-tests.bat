@echo off
echo.
echo ===========================================
echo   Raiya Recruitment - Frontend Test Runner
echo ===========================================
echo.

REM Check if Node.js is installed
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install it from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
call npm install --no-fund --no-audit

echo [2/3] Running Vitest Unit ^& UI Tests...
call npm run test

echo.
echo [3/3] Done! 
echo.
pause
