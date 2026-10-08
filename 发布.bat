@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "REPO=RONGLINC93/fnmonitorpro"
set "PREFIX=fnmonitorpro"

rem ============ 发布.bat ============
rem 用途：构建安装包 -> 打版本标签 -> 推送标签 -> 创建 GitHub Release 并上传 fpk
rem 用法：发布.bat            （版本号自动读取 manifest 的 version=）
rem       发布.bat 2.17.0      （指定版本号）
rem 版本号不自动递增：发布后请手动运行「递增版本号.bat」把 version 推进到下一开发版，
rem       并手动把 version_released 改为本次发布的版本，UI 据此区分「已发布版 / 开发版」。
rem 凭据：优先用 .env 中的 GITHUB_TOKEN（无需装 gh）；其次用 gh（需已登录）
rem       两者都没有时只构建，并提示手动创建 Release
rem 仓库: RONGLINC93/fnmonitorpro
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
echo [信息] 目标仓库：RONGLINC93/fnmonitorpro

rem ---- 2. 检查 manifest 版本与参数是否一致 ----
for /f "tokens=2 delims==" %%m in ('findstr /b "version=" manifest 2^>nul') do set "MFVER=%%m"
if not "%MFVER%"=="%VER%" (
  echo [警告] manifest中的版本是 %MFVER%，与本次发布 %VER% 不一致！
)

rem ---- 3. 工作区检查（含未跟踪文件）----
set "DIRTY="
for /f "delims=" %%s in ('git status --porcelain 2^>nul') do set "DIRTY=1"
if defined DIRTY echo [提示] 存在未提交改动，建议先运行「推送.bat」再发布

rem ---- 4. 检查发布凭据：优先 .env 中的 Token，其次 gh ----
set "HASTOK=0"
set "HASGH=0"
findstr /b /c:"GITHUB_TOKEN=" ".env" >nul 2>&1
if not errorlevel 1 (
  set "HASTOK=1"
  echo [凭据] 使用 .env 中的 GITHUB_TOKEN
) else (
  echo [提示] .env 中未找到 GITHUB_TOKEN
)
where gh >nul 2>&1
if not errorlevel 1 (
  gh auth status >nul 2>&1
  if not errorlevel 1 (
    set "HASGH=1"
    echo [凭据] gh 已登录
  ) else (
    echo [提示] gh 已安装但未登录
  )
) else (
  echo [提示] 未安装 gh 命令行工具
)

rem ---- 4b. 生成 git 认证头（供标签推送用；token 不落盘、不进 URL）----
set "AUTHCFG="
if "%HASTOK%"=="1" for /f "usebackq delims=" %%b in (`python -c "import base64,io;t=[l.split('=',1)[1].strip() for l in io.open('.env',encoding='utf-8',errors='ignore') if l.strip().startswith('GITHUB_TOKEN=')];print(base64.b64encode(('x-access-token:'+t[0]).encode()).decode() if t else '')" 2^>nul`) do set AUTHCFG="-c" "http.https://github.com/.extraheader=AUTHORIZATION: basic %%b"

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
git !AUTHCFG! push origin "v%VER%"
if errorlevel 1 (
  echo [警告] 标签推送失败（若远程已存在该标签可忽略）
  set "TAGOK=0"
) else (
  echo [完成] 标签 v%VER% 已在远程
)

rem ---- 6. 创建 Release 并上传资产（优先用 .env Token，其次 gh）----
echo.
echo === 3/3 创建 GitHub Release 并上传安装包 ===
set "RELOK=0"
if "%HASTOK%"=="1" (
  python "%~dp0_gh_release.py" %VER%
  if errorlevel 1 (
    echo [警告] 通过 .env Token 发布失败，可改用 gh 或网页手动创建
  ) else (
    set "RELOK=1"
  )
  goto :summary
)
if "%HASGH%"=="0" (
  echo [跳过] 无可用凭据（.env 无 GITHUB_TOKEN，且 gh 未安装/未登录）
  echo        办法一：在 .env 中配置 GITHUB_TOKEN=xxx（需 repo 权限）
  echo        办法二：winget install GitHub.cli 然后 gh auth login
  echo        办法三：手动创建 https://github.com/%REPO%/releases/new
  echo        需选择标签 v%VER% 并上传：
  echo          %PREFIX%-%VER%-x86.fpk
  echo          %PREFIX%-%VER%-arm.fpk
  goto :summary
)
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
:summary
echo.
echo ============== 发布结果 ==============
if "%RELOK%"=="1" (
  echo [成功] v%VER% 发布完成：标签 + Release + 安装包均已就绪
) else (
  echo [未完成] 仅完成本地构建
  if "%TAGOK%"=="1" (echo        标签 v%VER% 已推送) else (echo        标签未推送成功)
  echo        Release 未创建，见上方说明
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