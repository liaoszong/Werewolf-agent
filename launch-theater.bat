@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Werewolf Theater 一键启动 ===
python launch-theater.py
echo.
pause
