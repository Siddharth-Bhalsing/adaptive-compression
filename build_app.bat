@echo off
echo ===================================================
echo   ADAPTIVE ENGINE: 2026 PROFESSIONAL BUILDER
echo ===================================================

:: 1. Check for dependencies
echo [1/4] Checking Python libraries...
pip install psutil pyinstaller customtkinter

:: 2. Clean old builds to prevent "Ghost Files"
echo [2/4] Cleaning old workspace...
if exist build rd /s /q build
if exist dist rd /s /q dist

:: 3. Run PyInstaller
echo [3/4] Compiling Executable (This may take 1-2 minutes)...
:: Note: Replace 'app_icon.ico' with your actual icon filename
python -m PyInstaller --noconsole --onefile --clean --add-data "bin;bin" --icon=app_icon.ico app.py

:: 4. Finalizing
echo [4/4] Build Complete!
echo.
echo Your file is ready in the 'dist' folder.
pause