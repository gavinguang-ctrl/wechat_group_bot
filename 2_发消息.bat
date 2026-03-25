@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   定时轮换发消息
echo ========================================
python send_loop.py
pause
