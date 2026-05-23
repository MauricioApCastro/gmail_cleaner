@echo off
setlocal
cd /d "%~dp0"

if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" "run.py"
    goto end
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run.py"
    goto end
)

echo Ambiente virtual nao encontrado.
echo Crie a venv e instale as dependencias antes de abrir o Gmail Cleaner.
pause
exit /b 1

:end
if errorlevel 1 (
    echo.
    echo O Gmail Cleaner foi encerrado com erro.
    pause
)