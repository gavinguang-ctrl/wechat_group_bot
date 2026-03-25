@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   微信半自动扫码进群
echo ========================================
python scan_join.py
pause
