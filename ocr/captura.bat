@echo off
REM ============================================================================
REM  captura.bat - Doble clic para capturar la pantalla
REM  Guarda un PNG en la carpeta capturas\ y no envia nada a Internet.
REM ============================================================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0captura.ps1"
