@echo off
cd /d "%~dp0"
backend\.venv\Scripts\python.exe .document-tools\run_demo.py --port 8001 --uniform-trial-dir uniform-dataset\kv-demo
pause
