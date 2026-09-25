@echo off
REM ============================================================
REM ʱ¼ͬ MySQLͨöҵ߰棬v5.5
REM ļ GBK  + CRLF Уschtasks  cmd.exe  936 ȡ
REM ҵɵ 1  %1 ȱʡĬϣǻۼ+Ӫϵͳ
REM   עʱ /tr ĩβӦҵߣ sync_task.bat Ч
REM   ֧ҵߣЧ / μ / Ч / С / ǻۼ+Ӫϵͳ / AI / ǻۼ
REM ============================================================
set "BIZ_LINE=%1"
if "%BIZ_LINE%"=="" set "BIZ_LINE=ǻۼ+Ӫϵͳ"
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

REM ̽ Python python ʧԳ·
set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY_CMD (
  echo ERROR: δҵ Python밲װ Python 3.6+  PATH >> "%~dp0sync_log.txt" 2>&1
  exit /b 9009
)

REM ͬ־׷ӵ
"%PY_CMD%" sync_to_mysql.py --biz-line %BIZ_LINE% >> "%~dp0sync_log.txt" 2>&1
exit /b %ERRORLEVEL%
