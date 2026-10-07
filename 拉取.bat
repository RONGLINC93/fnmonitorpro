@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ============ 拉取.bat ============
rem 用途：从 origin/main 拉取最新代码（rebase 方式）
rem 用法：双击运行
rem 凭据：若 .env 中有 GITHUB_TOKEN 则用它认证（不落盘、不写进 remote URL）；
rem       否则回退到系统凭据管理器
rem 结束：窗口 5 秒后自动关闭

rem ---- 读取 .env 中的 Token，生成 git 认证头（token 不会出现在命令行/URL中）----
set "AUTHCFG="
for /f "usebackq delims=" %%b in (`python -c "import base64,io;t=[l.split('=',1)[1].strip() for l in io.open('.env',encoding='utf-8',errors='ignore') if l.strip().startswith('GITHUB_TOKEN=')];print(base64.b64encode(('x-access-token:'+t[0]).encode()).decode() if t else '')" 2^>nul`) do set "B64=%%b"
if defined B64 (
  set AUTHCFG="-c" "http.https://github.com/.extraheader=AUTHORIZATION: basic !B64!"
  echo [凭据] 使用 .env 中的 GITHUB_TOKEN
) else (
  echo [凭据] .env 中无 GITHUB_TOKEN，使用系统凭据
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [错误] 当前目录不是 git 仓库
  goto :theend
)

echo === 从 origin/main 拉取并变基 ===
git !AUTHCFG! pull --rebase origin main
if errorlevel 1 (
  echo.
  echo [错误] 拉取失败。若存在冲突，请手动处理：
  echo        查看冲突：git status
  echo        解决后：  git add -A ^&^& git rebase --continue
  echo        放弃：    git rebase --abort
  goto :theend
)

echo.
echo === 当前状态 ===
git --no-pager log --oneline -5
echo.
echo [完成] 已同步到远程最新

rem ---- 统一收尾：5 秒倒计时后自动关闭窗口 ----
:theend
echo.
echo 窗口将在 5 秒后自动关闭...
timeout /t 5 >nul 2>&1
if errorlevel 1 ping -n 6 127.0.0.1 >nul
exit /b 0