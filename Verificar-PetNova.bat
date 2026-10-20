@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo O Python ainda precisa de ser preparado neste computador.
  echo Guarda esta janela para continuarmos a configuracao no PC.
  pause
  exit /b 1
)
python "%~dp0scripts\verificar_configuracao.py"
pause
