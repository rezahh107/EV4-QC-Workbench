@echo off
setlocal
cd /d "%~dp0"
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
echo Setup complete. Run launch_windows.bat.
