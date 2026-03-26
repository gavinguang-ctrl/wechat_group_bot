@echo off
chcp 65001 >/dev/null
cd /d "%~dp0"
title WeChat Group Bot - Control Panel

:menu
cls
echo.
echo  ¨X¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨[
echo  ¨U    WeChat Group Bot - Control Panel    ¨U
echo  ¨d¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨g
echo  ¨U                                        ¨U
echo  ¨U  [1] Full Run (Scan + Join + Send)     ¨U
echo  ¨U  [2] Scan Latest Folder & Join Groups  ¨U
echo  ¨U  [3] Send Messages (Auto Loop)         ¨U
echo  ¨U  [4] View Group Status (Database)      ¨U
echo  ¨U  [5] Open QR Code Folder               ¨U
echo  ¨U  [6] Edit Message Template             ¨U
echo  ¨U  [7] Manually Add Group to List        ¨U
echo  ¨U                                        ¨U
echo  ¨U  [0] Exit                              ¨U
echo  ¨U                                        ¨U
echo  ¨^¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨T¨a
echo.
set /p choice=  Select [0-7]: 

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto scan_join
if "%choice%"=="3" goto send_msg
if "%choice%"=="4" goto show_status
if "%choice%"=="5" goto open_qr
if "%choice%"=="6" goto edit_template
if "%choice%"=="7" goto add_manual
if "%choice%"=="0" goto quit
echo.
echo  Invalid choice.
timeout /t 2 >/dev/null
goto menu

:run_all
cls
echo.
echo  ========================================
echo    Full Run: Scan + Join + Send
echo  ========================================
echo.
python main.py
echo.
echo  ----------------------------------------
echo  Done. Press any key to return...
pause >/dev/null
goto menu

:scan_join
cls
echo.
echo  ========================================
echo    Scan Latest Folder & Join Groups
echo  ========================================
echo.
python scan_join.py
echo.
echo  ----------------------------------------
echo  Done. Press any key to return...
pause >/dev/null
goto menu

:send_msg
cls
echo.
echo  ========================================
echo    Send Messages (Auto Loop)
echo  ========================================
echo.
python send_loop.py
echo.
echo  ----------------------------------------
echo  Done. Press any key to return...
pause >/dev/null
goto menu

:show_status
cls
echo.
echo  ========================================
echo    Group Database Status
echo  ========================================
echo.
python status.py
echo.
echo  ----------------------------------------
echo  Press any key to return...
pause >/dev/null
goto menu

:add_manual
cls
echo.
echo  ========================================
echo    Manually Add Group to List
echo  ========================================
echo.
python add_group.py
echo.
echo  ----------------------------------------
echo  Press any key to return...
pause >/dev/null
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
