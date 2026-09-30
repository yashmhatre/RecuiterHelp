@echo off
REM Launch the prototype web app. Open http://127.0.0.1:8000
cd /d "%~dp0"
".venv\Scripts\python.exe" -m prototype.app
