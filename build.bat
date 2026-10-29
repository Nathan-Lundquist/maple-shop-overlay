@echo off
echo ============================================
echo  Maple Shop Checker - Build Script
echo ============================================
echo.

pip install pyinstaller >nul 2>&1

REM Make sure the DB exists before bundling
if not exist "assets\items.db" (
    echo Item database not found. Running sync first...
    echo This will take a while.
    echo.
    python sync_db.py
    if errorlevel 1 (
        echo sync_db.py failed. Cannot build without item data.
        pause
        exit /b 1
    )
)

echo Building executable...
pyinstaller build.spec --clean --noconfirm

if exist "dist\MapleShopChecker\MapleShopChecker.exe" (
    echo.
    echo ============================================
    echo  Build successful!
    echo  Output: dist\MapleShopChecker\
    echo ============================================
    echo.
    echo Zip the entire dist\MapleShopChecker\ folder to distribute.
) else (
    echo.
    echo Build FAILED. Check output above for errors.
    pause
)
