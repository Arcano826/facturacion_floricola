@echo off
setlocal

:: Ir al directorio del script
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Ejecutar el script
python .\app.py

endlocal
pause