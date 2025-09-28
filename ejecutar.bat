@echo off
echo.
echo ========================================
echo   GRABADOR DE AUDIO CON DETECCION 
echo        DE VOLUMEN - v1.0
echo ========================================
echo.
echo Iniciando aplicacion...
echo.

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Ejecutar la aplicacion
python audio_recorder.py

echo.
echo Aplicacion cerrada.
pause