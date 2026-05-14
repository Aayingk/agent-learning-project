@echo off
echo ============================================
echo Agent Learning Project - Jupyter 启动器
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo.
echo [2/2] 启动 Jupyter Notebook...
echo.
echo 学习课程位置: docs/lessons/
echo.

jupyter notebook docs\lessons

pause
