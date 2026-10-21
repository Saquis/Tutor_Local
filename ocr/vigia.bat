@echo off
REM Lanzador del vigia: mira la pantalla cada 12s y manda a Telegram.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\RYZEN 5 GAMER\Tutor_Local\ocr\vigia.ps1" -Repetir 99999 -Intervalo 12
