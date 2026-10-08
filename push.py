#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push.py ["自定义提交信息"]
===========================
提交本地改动 -> 变基到远程最新 -> 推送到 origin/main。
用法：双击运行；或命令行传入提交信息：push.py "自定义提交信息"
注意：git rebase 要求工作区干净，故必须「先提交、再变基、后推送」。
"""
import base64
import io
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


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


def git_auth_args():
    env = load_env(os.path.join(ROOT, ".env"))
    tok = env.get("GITHUB_TOKEN", "")
    if tok:
        b64 = base64.b64encode(("x-access-token:" + tok).encode("utf-8")).decode("ascii")
        return ["-c", "http.https://github.com/.extraheader=AUTHORIZATION: basic " + b64], True
    return [], False


def get_version(text):
    m = re.search(r"(?m)^version=([0-9].*)$", text)
    return m.group(1).strip() if m else ""


def run(cmd):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def main():
    os.chdir(ROOT)
    auth, has_tok = git_auth_args()
    if has_tok:
        print("[凭据] 使用 .env 中的 GITHUB_TOKEN")
    else:
        print("[凭据] .env 中无 GITHUB_TOKEN，使用系统凭据")

    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        print("[错误] 当前目录不是 git 仓库")
        return 1

    # 提交信息：优先用命令行参数，否则自动生成（带 manifest 版本号）
    msg = sys.argv[1] if len(sys.argv) > 1 else ""
    if not msg:
        with io.open(os.path.join(ROOT, "manifest"), encoding="utf-8") as f:
            ver = get_version(f.read())
        ver = ver or "unknown"
        msg = "release v%s: 飞牛监控pro - 风扇曲线控制 / 卡片尺寸 / PRO 图标" % ver

    print("=== 1/4 暂存并提交本地改动 ===")
    if run(["git", "add", "-A"]) != 0:
        print("[错误] git add 失败")
        return 1

    have_commit = False
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        print("[信息] 提交信息：%s" % msg)
        if run(["git", "commit", "-m", msg]) != 0:
            print("[错误] git commit 失败")
            return 1
        have_commit = True
    else:
        print("[提示] 无本地改动，仅同步远程")

    print("")
    print("=== 2/4 变基到远程最新（pull --rebase）===")
    if run(["git"] + auth + ["pull", "--rebase", "origin", "main"]) != 0:
        print("[错误] 拉取/变基失败。若有冲突请手动处理：")
        print("        查看：  git status")
        print("        解决后：git add -A && git rebase --continue")
        print("        放弃：  git rebase --abort")
        return 1

    print("")
    print("=== 3/4 推送到 origin/main ===")
    if run(["git"] + auth + ["push", "origin", "main"]) != 0:
        print("[错误] git push 失败")
        return 1

    print("")
    print("=== 4/4 完成 ===")
    if have_commit:
        print("[完成] 已提交并推送到 https://github.com/RONGLINC93/fnmonitorpro")
    else:
        print("[完成] 已同步到远程最新")
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
