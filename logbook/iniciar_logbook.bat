@echo off
REM ============================================================================
REM  iniciar_logbook.bat - Arranca la captura automatica (cada 30 s)
REM  Deja esta ventana abierta. Para parar: cierra la ventana
REM  o crea el archivo  logbook\DETENER
REM ============================================================================
title Logbook - captura automatica
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bucle_captura.ps1"
pause
