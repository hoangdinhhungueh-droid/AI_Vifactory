@echo off
chcp 65001 > nul
cd /d "%~dp0"
title AI Video Factory - Dang Nhap Google AI Pro Profile 7 (acc_07)
echo ======================================================================
echo   DANG NHAP TAI KHOAN GOOGLE AI PRO CHO SLOT 7 (acc_07)
echo   Trinh duyet Chrome that se duoc mo ra tai C:\Users\hunghd2\.gemini\profiles\acc_07
echo   Vui long dang nhap va bam YES tren hop thoai de luu phien.
echo ======================================================================
"C:\Users\hunghd2\Downloads\SieuThiScraper_DesktopApp\supermarket_scraper\.venv\Scripts\python.exe" scripts\setup_6_profiles.py --slot 7
pause
