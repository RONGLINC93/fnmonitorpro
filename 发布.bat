@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "REPO=RONGLINC93/fnmonitor"
set "PREFIX=fnmonitorpro"

rem ============ 发布.bat ============
rem 用途：构建安装包 -> 打版本标签 -> 推送标签 -> 创建 GitHub Release 并上传 fpk
rem 用法：发布.bat            （版本号自动读取 manifest 的 version=）
rem       发布.bat 2.17.0      （指定版本号）
rem 依赖：gh（GitHub CLI，且需已 gh auth login）；未安装/未登录则只构建并提示手动发布
rem 仓库: RONGLINC93/fnmonitor
rem 结束：窗口 5 秒后自动关闭

rem ---- 1. 确定版本号 ----
set "VER=%~1"
if not defined VER (
  for /f "tokens=2 delims==" %%v in ('findstr /b "version=" manifest 2^>nul') do set "VER=%%v"
)
if not defined VER (
  echo [错误] 无法从 manifest 读取版本号，请显式指定：发布.bat 2.17.0
  goto :theend
)
echo [信息] 发布版本：%VER%
echo [信息] 目标仓库：RONGLINC93/fnmonitor

rem ---- 2. 检查 manifest 版本与参数是否一致 ----
for /f "tokens=2 delims==" %%m in ('findstr /b "version=" manifest 2^>nul') do set "MFVER=%%m"
if not "%MFVER%"=="%VER%" (
  echo [警告] manifest中的版本是 %MFVER%，与本次发布 %VER% 不一致！
)

rem ---- 3. 工作区检查（含未跟踪文件）----
set "DIRTY="
for /f "delims=" %%s in ('git status --porcelain 2^>nul') do set "DIRTY=1"
if defined DIRTY echo [提示] 存在未提交改动，建议先运行「推送.bat」再发布

rem ---- 4. 检查 gh 及登录状态 ----
set "HASGH=0"
where gh >nul 2>&1
if not errorlevel 1 (
  gh auth status >nul 2>&1
  if errorlevel 1 (
    echo [警告] gh 已安装但未登录，自动发布将跳过。请先执行：gh auth login
  ) else (
    set "HASGH=1"
  )
) else (
  echo [提示] 未安装 gh 命令行工具
)

echo.
echo === 1/3 构建安装包 ===
powershell -NoProfile -ExecutionPolicy Bypass -File "build.ps1"
if errorlevel 1 (
  echo [错误] 构建失败
  goto :theend
)

if not exist "fnmonitorpro-%VER%-x86.fpk" (
  echo [错误] 未找到构建产物 fnmonitorpro-%VER%-x86.fpk
  goto :theend
)

rem ---- 5. 打标签并推送（标签已存在时同样推送，可修补上次推送失败）----
echo.
echo === 2/3 创建并推送版本标签 v%VER% ===
set "TAGOK=1"
git tag -a "v%VER%" -m "v%VER%"
if errorlevel 1 echo [提示] 本地标签已存在，改为直接推送该标签
git push origin "v%VER%"
if errorlevel 1 (
  echo [警告] 标签推送失败（若远程已存在该标签可忽略）
  set "TAGOK=0"
) else (
  echo [完成] 标签 v%VER% 已在远程
)

rem ---- 6. 创建 Release 并上传资产 ----
echo.
echo === 3/3 创建 GitHub Release 并上传安装包 ===
set "RELOK=0"
if "%HASGH%"=="0" (
  echo [跳过] 未安装 gh 或未登录，无法自动创建 Release
  echo        安装：winget install GitHub.cli   然后：gh auth login
  echo        或手动创建：https://github.com/%REPO%/releases/new
  echo        需选择标签 v%VER% 并上传：
  echo          %PREFIX%-%VER%-x86.fpk
  echo          %PREFIX%-%VER%-arm.fpk
) else (
  gh release view "v%VER%" --repo %REPO% >nul 2>&1
  if errorlevel 1 (
    rem Release 不存在 -> 创建并上传两个资产
    gh release create "v%VER%" "%PREFIX%-%VER%-x86.fpk" "%PREFIX%-%VER%-arm.fpk" --repo %REPO% --title "v%VER%" --notes "详见 manifest changelog"
    if errorlevel 1 (
      echo [警告] 创建 Release 失败，可手动到 Releases 页面创建
    ) else (
      echo [完成] Release v%VER% 已创建并上传安装包
      set "RELOK=1"
    )
  ) else (
    rem Release 已存在 -> 覆盖上传同名资产
    gh release upload "v%VER%" "%PREFIX%-%VER%-x86.fpk" "%PREFIX%-%VER%-arm.fpk" --clobber --repo %REPO%
    if errorlevel 1 (
      echo [警告] 上传资产失败，可手动上传
    ) else (
      echo [完成] Release v%VER% 资产已更新
      set "RELOK=1"
    )
  )
)

rem ---- 7. 结果汇总 ----
echo.
echo ============== 发布结果 ==============
if "%HASGH%"=="1" (
  if "%RELOK%"=="1" (
    echo [成功] v%VER% 发布完成：标签 + Release + 安装包均已就绪
    echo        应用内「检查更新」现已可用
  ) else (
    echo [未完成] Release 未成功创建，请查看上方错误或手动创建
  )
) else (
  echo [未完成] 仅完成本地构建
  if "%TAGOK%"=="1" (echo        标签 v%VER% 已推送) else (echo        标签未推送成功)
  echo        Release 需 gh 工具或网页手动创建，见上方说明
)
echo =======================================
echo.
echo 提示：把 fnpack.json 中 %VER% 的 download_url / sha256 / size 更新为本次资产

rem ---- 统一收尾：5 秒倒计时后自动关闭窗口 ----
:theend
echo.
echo 窗口将在 5 秒后自动关闭...
timeout /t 5 >nul 2>&1
if errorlevel 1 ping -n 6 127.0.0.1 >nul
exit /b 0