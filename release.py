#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""release.py [版本号]
===================
构建安装包 -> 打版本标签 -> 推送标签 -> 创建 GitHub Release 并上传 fpk。
版本号：默认读取 manifest 的 version=；也可显式传入（release.py 2.17.0）。
凭据：优先用 .env 中的 GITHUB_TOKEN（无需装 gh）；其次用 gh（需已登录）。
仓库: RONGLINC93/fnmonitorpro
"""
import base64
import io
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")
REPO = "RONGLINC93/fnmonitorpro"


def load_env(path):
    data = {}
    if not os.path.exists(path):
        return data
    with io.open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                data[k.strip()] = v.strip().strip("'").strip('"')
    return data


def get_version(text):
    m = re.search(r"(?m)^version=([0-9].*)$", text)
    return m.group(1).strip() if m else ""


def git_auth_args():
    env = load_env(os.path.join(ROOT, ".env"))
    tok = env.get("GITHUB_TOKEN", "")
    if tok:
        b64 = base64.b64encode(("x-access-token:" + tok).encode("utf-8")).decode("ascii")
        return ["-c", "http.https://github.com/.extraheader=AUTHORIZATION: basic " + b64], True
    return [], False


def run(cmd):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def main():
    os.chdir(ROOT)
    ver = sys.argv[1] if len(sys.argv) > 1 else ""
    if not ver:
        with io.open(MANIFEST, encoding="utf-8") as f:
            ver = get_version(f.read())
    if not ver:
        print("[错误] 无法从 manifest 读取版本号，请显式指定：release.py 2.17.0")
        return 1
    print("[信息] 发布版本：%s" % ver)
    print("[信息] 目标仓库：%s" % REPO)

    # manifest 版本一致性检查
    with io.open(MANIFEST, encoding="utf-8") as f:
        mfver = get_version(f.read())
    if mfver and mfver != ver:
        print("[警告] manifest中的版本是 %s，与本次发布 %s 不一致！" % (mfver, ver))

    # 工作区检查（含未跟踪文件）
    r = subprocess.run(["git", "status", "--porcelain"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.stdout.strip():
        print("[提示] 存在未提交改动，建议先运行「push.py」再发布")

    # ---- 1/3 构建安装包 ----
    print("")
    print("=== 1/3 构建安装包 ===")
    if run([sys.executable, os.path.join(ROOT, "build.py")]) != 0:
        print("[错误] 构建失败")
        return 1
    for plat in ("x86", "arm"):
        p = os.path.join(ROOT, "fnmonitorpro-%s-%s.fpk" % (ver, plat))
        if not os.path.exists(p):
            print("[错误] 未找到构建产物 %s" % p)
            return 1

    # ---- 2/3 打标签并推送 ----
    print("")
    print("=== 2/3 创建并推送版本标签 v%s ===" % ver)
    run(["git", "tag", "-a", "v%s" % ver, "-m", "v%s" % ver])
    auth, _ = git_auth_args()
    rc = run(["git"] + auth + ["push", "origin", "v%s" % ver])
    if rc != 0:
        print("[警告] 标签推送失败（若远程已存在该标签可忽略）")
    else:
        print("[完成] 标签 v%s 已在远程" % ver)

    # ---- 3/3 创建 Release 并上传资产 ----
    print("")
    print("=== 3/3 创建 GitHub Release 并上传安装包 ===")
    env = load_env(os.path.join(ROOT, ".env"))
    tok = env.get("GITHUB_TOKEN", "")
    rel_rc = 1
    if tok:
        print("[凭据] 使用 .env 中的 GITHUB_TOKEN")
        rel_rc = run([sys.executable, os.path.join(ROOT, "_gh_release.py"), ver])
    else:
        if subprocess.run(["where", "gh"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            print("[凭据] 使用 gh")
            if subprocess.run(["gh", "auth", "status"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0:
                x86 = os.path.join(ROOT, "fnmonitorpro-%s-x86.fpk" % ver)
                arm = os.path.join(ROOT, "fnmonitorpro-%s-arm.fpk" % ver)
                if subprocess.run(["gh", "release", "view", "v%s" % ver, "--repo", REPO],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL).returncode != 0:
                    run(["gh", "release", "create", "v%s" % ver, x86, arm,
                         "--repo", REPO, "--title", "v%s" % ver,
                         "--notes", "详见 manifest changelog"])
                else:
                    run(["gh", "release", "upload", "v%s" % ver, x86, arm,
                         "--clobber", "--repo", REPO])
                rel_rc = 0
            else:
                print("[提示] gh 已安装但未登录")
        else:
            print("[提示] 未安装 gh 命令行工具")

    if rel_rc != 0:
        print("[跳过] 无可用凭据（.env 无 GITHUB_TOKEN，且 gh 未安装/未登录）")
        print("        办法一：在 .env 中配置 GITHUB_TOKEN=xxx（需 repo 权限）")
        print("        办法二：winget install GitHub.cli 然后 gh auth login")
        print("        办法三：手动创建 https://github.com/%s/releases/new" % REPO)
        print("        需选择标签 v%s 并上传：" % ver)
        print("          fnmonitorpro-%s-x86.fpk" % ver)
        print("          fnmonitorpro-%s-arm.fpk" % ver)

    # ---- 结果汇总 ----
    print("")
    print("============== 发布结果 ==============")
    if rel_rc == 0:
        print("[成功] v%s 发布完成：标签 + Release + 安装包均已就绪" % ver)
    else:
        print("[未完成] 仅完成本地构建")
        print("        标签 v%s 已推送" % ver if rc == 0 else "        标签未推送成功")
        print("        Release 未创建，见上方说明")
    print("=======================================")
    print("")
    print("提示：把 fnpack.json 中 %s 的 download_url / sha256 / size 更新为本次资产" % ver)
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 0
    print("")
    print("窗口将在 5 秒后自动关闭...")
    time.sleep(5)
    sys.exit(rc)
