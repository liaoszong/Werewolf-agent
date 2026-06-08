@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=src
if "%DEEPSEEK_API_KEY%"=="" (
  echo.
  echo !! 没检测到 DEEPSEEK_API_KEY。请在【同一个 cmd 窗口】先运行:
  echo        set DEEPSEEK_API_KEY=sk-你的key
  echo    然后再运行   live-check.bat
  echo.
  pause
  exit /b 1
)
echo === 真实 live 验证:6 座位全 DeepSeek（会真实调用 API、产生少量费用）===
python tools\live_check_deepseek.py
echo.
pause
