@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ============ 拉取.bat ============
rem 用途：从 origin/main 拉取最新代码（rebase 方式）
rem 用法：双击运行
rem 说明：若本地有未推送的提交，会先变基到最新远程之上
rem 结束：窗口 5 秒后自动关闭

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [错误] 当前目录不是 git 仓库
  goto :theend
)

echo === 从 origin/main 拉取并变基 ===
git pull --rebase origin main
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