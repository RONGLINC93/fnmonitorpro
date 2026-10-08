@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ============ 递增版本号.bat ============
rem 用途：递增 manifest 中的 version=（全项目唯一版本源；构建/发布/关于页均读这里）
rem 用法：
rem   递增版本号.bat             交互菜单：1=patch / 2=minor / 3=major / 4=自定义
rem   递增版本号.bat patch       补丁号 +1        （2.17.1 -^> 2.17.2）
rem   递增版本号.bat minor       次版本 +1        （2.17.1 -^> 2.18.0）
rem   递增版本号.bat major       主版本 +1        （2.17.1 -^> 3.0.0）
rem   递增版本号.bat 2.18.0      直接指定版本号
rem   递增版本号.bat /?          显示用法
rem 说明：仅替换 manifest 的 version= 一行，其余内容 UTF-8 无 BOM 原样保留。

rem ---- 帮助 ----
if /i "%~1"=="/?" goto :usage
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage

rem ---- 1. 读取当前版本 ----
set "CUR="
for /f "tokens=2 delims==" %%v in ('findstr.exe /b "version=" manifest 2^>nul') do set "CUR=%%v"
if not defined CUR (
  echo [错误] 无法从 manifest 读取 version=，请检查文件是否存在。
  goto :theend
)

rem ---- 2. 拆分 主.次.补丁（忽略 - 或 + 之后的预发布后缀）----
for /f "tokens=1 delims=-+" %%b in ("%CUR%") do set "CORE=%%b"
for /f "tokens=1,2,3 delims=." %%a in ("%CORE%") do (
  set "MA=%%a"
  set "MI=%%b"
  set "PA=%%c"
)
if not defined MI set "MI=0"
if not defined PA set "PA=0"

rem ---- 3. 计算各模式预览 ----
set /a NP=PA+1
set /a NM=MI+1
set /a NMA=MA+1
set "NEWP=%MA%.%MI%.%NP%"
set "NEWM=%MA%.%NM%.0"
set "NEWJ=%NMA%.0.0"

set "MODE=%~1"
set "NEW="
if defined MODE goto :byarg

:menu
echo.
echo 请选择递增模式（当前版本 %CUR%）：
echo   [1] patch  补丁号 +1  -^> %NEWP%
echo   [2] minor  次版本 +1  -^> %NEWM%
echo   [3] major  主版本 +1  -^> %NEWJ%
echo   [4] 自定义 手动输入版本号
choice.exe /c 1234 /n /m "请按 1 / 2 / 3 / 4 选择："
set "EC=%errorlevel%"
if "%EC%"=="4" goto :custom
if "%EC%"=="3" (set "NEW=%NEWJ%" & goto :confirm)
if "%EC%"=="2" (set "NEW=%NEWM%" & goto :confirm)
if "%EC%"=="1" (set "NEW=%NEWP%" & goto :confirm)
echo [取消] 未选择。
goto :theend

:custom
set "NEW="
set /p "NEW=请输入新版本号（如 2.18.0）："
for /f "tokens=1" %%c in ("%NEW%") do set "NEW=%%c"
if not defined NEW (
  echo [取消] 未输入版本号。
  goto :theend
)
echo %NEW%| findstr.exe /r "^[0-9][0-9]*\.[0-9][0-9]*$ ^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [错误] 版本号格式不正确：%NEW%（示例 2.18.0）
  goto :custom
)
goto :confirm

rem ---- 命令行参数模式：patch / minor / major / 显式版本号 ----
:byarg
if /i "%MODE%"=="patch" (set "NEW=%NEWP%" & goto :confirm)
if /i "%MODE%"=="minor" (set "NEW=%NEWM%" & goto :confirm)
if /i "%MODE%"=="major" (set "NEW=%NEWJ%" & goto :confirm)
echo %MODE%| findstr.exe /r "^[0-9][0-9]*\.[0-9][0-9]*$ ^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [错误] 无法识别的参数：%MODE%
  echo        可用：patch / minor / major / 显式版本号（如 2.18.0）
  goto :theend
)
set "NEW=%MODE%"

:confirm
echo.
echo [信息] 当前版本：%CUR%
echo [信息] 新版本号：%NEW%
if "%NEW%"=="%CUR%" (
  echo [提示] 新版本与当前版本相同，无需修改。
  goto :theend
)

set "ASK="
set /p "ASK=确认写入 manifest？(Y/n) "
for /f "tokens=1" %%c in ("%ASK%") do set "ASK=%%c"
if /i "%ASK%"=="n" (
  echo [取消] 未做任何修改。
  goto :theend
)

rem ---- 4. 写回 manifest（仅替换 version= 行，UTF-8 无 BOM 原样保留）----
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$enc=[System.Text.UTF8Encoding]::new($false); $p='%~dp0manifest'; if(-not [IO.File]::Exists($p)){exit 2}; $t=[IO.File]::ReadAllText($p,$enc); if(-not [regex]::IsMatch($t,'(?m)^version=')){exit 3}; $t2=[regex]::Replace($t,'(?m)^version=.*$','version=%NEW%'); [IO.File]::WriteAllText($p,$t2,$enc); exit 0"
if errorlevel 1 (
  echo [错误] 写入 manifest 失败（PowerShell 退出码 %errorlevel%）。
  goto :theend
)

rem ---- 5. 校验 ----
set "NOW="
for /f "tokens=2 delims==" %%v in ('findstr.exe /b "version=" manifest 2^>nul') do set "NOW=%%v"
if "%NOW%"=="%NEW%" goto :ok
echo [警告] 写入后读回的版本是 %NOW%，与预期 %NEW% 不一致，请手动检查 manifest。
goto :theend

:ok
echo [完成] manifest 版本号已更新：%CUR% -^> %NEW%
echo [提示] 记得补充 manifest 的 changelog（顶部加一行：v%NEW% (br) ...），然后运行「发布.bat」打包发布。
goto :theend

:usage
echo 用法：递增版本号.bat [patch^|minor^|major^|x.y.z]
echo   不带参数时进入选择菜单：1=patch / 2=minor / 3=major / 4=自定义
echo   patch（菜单默认） 补丁号 +1，如 2.17.1 -^> 2.17.2
echo   minor         次版本 +1，如 2.17.1 -^> 2.18.0
echo   major         主版本 +1，如 2.17.1 -^> 3.0.0
echo   x.y.z         直接指定版本号，如 2.18.0

:theend
echo.
pause
endlocal
