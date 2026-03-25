@echo off
chcp 65001 >/dev/null
cd /d "%~dp0"
title WeChat Group Bot

:menu
cls
echo.
echo  ======================================
echo        WeChat Group Bot - Control
echo  ======================================
echo.
echo   [1] Full Run (Scan + Join + Send)
echo   [2] Scan and Join Groups
echo   [3] Send Messages
echo   [4] View Group Status
echo   [5] Open QR Code Folder
echo   [6] Edit Message Template
echo   [0] Exit
echo.
set /p choice=  Select [0-6]: 

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto scan_join
if "%choice%"=="3" goto send_msg
if "%choice%"=="4" goto show_status
if "%choice%"=="5" goto open_qr
if "%choice%"=="6" goto edit_template
if "%choice%"=="0" goto quit
echo.
echo  Invalid choice.
timeout /t 2 >/dev/null
goto menu

:run_all
cls
echo.
python main.py
echo.
pause
goto menu

:scan_join
cls
echo.
python scan_join.py
echo.
pause
goto menu

:send_msg
cls
echo.
python send_loop.py
echo.
pause
goto menu

:show_status
cls
echo.
python status.py
echo.
pause
goto menu

:open_qr
start "" "C:\Users\gavin\xhs_qr_scraper\data\qr_codes"
goto menu

:edit_template
if exist "templates\default.txt" (
    notepad "templates\default.txt"
) else (
    if not exist "templates" mkdir "templates"
    echo Please edit your message template here> "templates\default.txt"
    notepad "templates\default.txt"
)
goto menu

:quit
exit
