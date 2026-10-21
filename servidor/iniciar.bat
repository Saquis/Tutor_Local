@echo off
REM ============================================================
REM  Tutor Local — lanzador para WINDOWS
REM  Doble clic o:  iniciar.bat
REM ============================================================
cd /d "%~dp0.."

REM Token compartido con la extension (extension\background.js)
set TUTOR_TOKEN=-eIDzFPmtkHZYUzdd1jEzlfRDPF7ntwO

REM 0.0.0.0 para aceptar tambien conexiones desde WSL si hiciera falta
set TUTOR_HOST=127.0.0.1
set TUTOR_PUERTO=8765

REM Modelo local (Ollama en WSL, alcanzable en localhost)
set TUTOR_MODELO=phi3:3.8b
set TUTOR_OLLAMA=http://localhost:11434

REM Motor profundo por API (opcional). Vacio = usa el local.
set DEEPSEEK_API_KEY=

REM La BD de cache
set TUTOR_DB=servidor\study.db

echo.
echo   Iniciando Tutor Local...
echo.
python -m servidor.main

pause
