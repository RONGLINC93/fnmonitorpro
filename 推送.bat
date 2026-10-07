@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ============ 推送.bat ============
rem 用途：提交本地改动 -> 变基到远程最新 -> 推送到 origin/main
rem 用法：双击运行；或命令行传入提交信息：推送.bat "自定义提交信息"
rem 注意：git rebase 要求工作区干净，故必须「先提交、再变基、后推送」

rem ---- 校验是否为 git 仓库 ----
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [错误] 当前目录不是 git 仓库
  exit /b 1
)

rem ---- 提交信息：优先用命令行参数，否则自动生成（带 manifest 版本号）----
set "MSG=%~1"
if not defined MSG (
  set "VER=unknown"
  for /f "tokens=2 delims==" %%v in ('findstr /b "version=" manifest 2^>nul') do set "VER=%%v"
  set "MSG=release v!VER!: 飞牛监控pro - 风扇曲线控制 / 卡片尺寸 / PRO 图标"
)

echo === 1/4 暂存并提交本地改动 ===
git add -A
if errorlevel 1 (
  echo [错误] git add 失败
  exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
  echo [信息] 提交信息：!MSG!
  git commit -m "!MSG!"
  if errorlevel 1 (
    echo [错误] git commit 失败
    exit /b 1
  )
  set "HAVE_COMMIT=1"
) else (
  echo [提示] 无本地改动，仅同步远程
)

echo.
echo === 2/4 变基到远程最新（pull --rebase）===
git pull --rebase origin main
if errorlevel 1 (
  echo [错误] 拉取/变基失败。若有冲突请手动处理：
  echo        查看：  git status
  echo        解决后：git add -A ^&^& git rebase --continue
  echo        放弃：  git rebase --abort
  exit /b 1
)

echo.
echo === 3/4 推送到 origin/main ===
git push origin main
if errorlevel 1 (
  echo [错误] git push 失败
  exit /b 1
)

echo.
echo === 4/4 完成 ===
if defined HAVE_COMMIT (
  echo [完成] 已提交并推送到 https://github.com/RONGLINC93/fnmonitor
) else (
  echo [完成] 已同步到远程最新
)
exit /b 0