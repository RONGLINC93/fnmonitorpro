@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ============ 发布.bat ============
rem 用途：构建安装包 -> 打版本标签 -> 推送标签 -> 创建 GitHub Release 并上传 fpk
rem 用法：发布.bat            （版本号自动读取 manifest 的 version=）
rem       发布.bat 2.17.0      （指定版本号）
rem 依赖：gh（GitHub CLI，用于创建 Release / 上传资产；未安装则跳过并提示手动操作）
rem 仓库: RONGLINC93/fnmonitor

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

rem ---- 3. 检查工作区是否已提交（建议先推送）----
git diff --quiet
if errorlevel 1 (
  echo [提示] 存在未提交的改动，建议先运行「推送.bat」再发布
)

echo.
echo === 1/4 构建安装包 ===
powershell -NoProfile -ExecutionPolicy Bypass -File "build.ps1"
if errorlevel 1 (
  echo [错误] 构建失败
  goto :theend
)

if not exist "fnmonitorpro-%VER%-x86.fpk" (
  echo [错误] 未找到构建产物 fnmonitorpro-%VER%-x86.fpk
  goto :theend
)

rem ---- 4. 打标签并推送 ----
echo.
echo === 2/4 创建并推送版本标签 v%VER% ===
git tag -a "v%VER%" -m "v%VER%"
if errorlevel 1 (
  echo [提示] 标签 v%VER% 可能已存在，尝试继续推送该标签
) else (
  git push origin "v%VER%"
  if errorlevel 1 (
    echo [错误] 标签推送失败
    goto :theend
  )
  echo [完成] 标签 v%VER% 已推送
)

rem ---- 5. 创建 Release 并上传资产 ----
echo.
echo === 3/4 创建 GitHub Release 并上传安装包 ===
where gh >nul 2>&1
if errorlevel 1 (
  echo [警告] 未检测到 gh 命令行工具，自动创建 Release 已跳过
  echo        如需自动发布请安装：winget install GitHub.cli
  echo        或手动创建：https://github.com/RONGLINC93/fnmonitor/releases/new
) else (
  gh release view "v%VER%" --repo RONGLINC93/fnmonitor >nul 2>&1
  if errorlevel 1 (
    rem Release 不存在 -> 创建并上传
    gh release create "v%VER%" ^
      "fnmonitorpro-%VER%-x86.fpk" ^
      "fnmonitorpro-%VER%-arm.fpk" ^
      --repo RONGLINC93/fnmonitor ^
      --title "v%VER%" ^
      --notes "详见 manifest changelog / CHANGELOG"
    if errorlevel 1 (
      echo [警告] 创建 Release 失败（可手动到 Releases 页面创建）
    ) else (
      echo [完成] Release v%VER% 已创建并上传安装包
    )
  ) else (
    rem Release 已存在 -> 覆盖上传同名资产
    gh release upload "v%VER%" ^
      "fnmonitorpro-%VER%-x86.fpk" ^
      "fnmonitorpro-%VER%-arm.fpk" ^
      --clobber --repo RONGLINC93/fnmonitor
    if errorlevel 1 (
      echo [警告] 上传资产失败（可手动上传）
    ) else (
      echo [完成] Release v%VER% 资产已更新
    )
  )
)

echo.
echo === 4/4 收尾提示 ===
echo [完成] 发布流程结束：v%VER%
echo.
echo 后续可选：
echo   1) 把 fnpack.json 中该版本的 download_url / sha256 / size 更新为新资产
echo   2) 若要让应用内"发现新版本"提示生效，确认 Release 为正式版（非 pre-release）

rem ---- 统一收尾：5 秒倒计时后自动关闭窗口 ----
:theend
echo.
echo 窗口将在 5 秒后自动关闭...
timeout /t 5 >nul 2>&1
if errorlevel 1 ping -n 6 127.0.0.1 >nul
exit /b 0