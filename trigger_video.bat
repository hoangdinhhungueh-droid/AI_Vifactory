@echo off
chcp 65001 >nul
echo ========================================================
echo  TRIGGER SINH VIDEO VEO 3.1 (7 TAI KHOAN GOOGLE FLOW)
echo ========================================================
set EPISODE=KR_EP0001_google_kr_tax_loss
if not "%~1"=="" set EPISODE=%~1

python scripts\trigger_video_generation.py --episode %EPISODE% %2 %3 %4
pause
