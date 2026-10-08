#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py - 构建 fnMonitor 安装包（x86 / arm）
=============================================
前提：已安装 Python 3
      fnpack：优先使用本目录 fnpack.exe，其次取 PATH 中的 fnpack
      官方文档 https://developer.fnnas.com/docs/cli/fnpack/
产物：fnmonitorpro-<版本>-x86.fpk 与 fnmonitorpro-<版本>-arm.fpk
"""
import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")


def read_manifest():
    with io.open(MANIFEST, encoding="utf-8", newline="") as f:
        return f.read()


def write_manifest(text):
    with io.open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def get_version(text):
    m = re.search(r"(?m)^version=([0-9].*)$", text)
    return m.group(1).strip() if m else ""


def find_fnpack():
    local = os.path.join(ROOT, "fnpack.exe")
    if os.path.exists(local):
        return local
    return shutil.which("fnpack")


def run(cmd):
    print("> " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def main():
    os.chdir(ROOT)

    print("[1/4] 生成应用图标...")
    rc = run([sys.executable, os.path.join(ROOT, "make_icon.py")])
    if rc != 0:
        print("[警告] make_icon.py 返回非零（%d），继续。" % rc)

    fnpack = find_fnpack()
    if not fnpack:
        print("未找到 fnpack 命令。")
        print("  1) 下载 fnpack Windows 版: https://developer.fnnas.com/docs/cli/fnpack/")
        print("  2) 将 fnpack.exe 放到本目录，或加入 PATH 后重试")
        return 1

    orig = read_manifest()
    version = get_version(orig)
    if not version:
        print("无法从 manifest 解析 version")
        return 1
    print("[3/4] 读取 manifest 版本号: %s" % version)

    try:
        print("[4/4] 分别打包 x86 / arm ...")
        for plat in ("x86", "arm"):
            swapped = re.sub(r"(?m)^platform=.*$", "platform=%s" % plat, orig, count=1)
            write_manifest(swapped)
            if run([fnpack, "build"]) != 0:
                raise RuntimeError("fnpack build (%s) 失败" % plat)
            src = os.path.join(ROOT, "fnmonitorpro.fpk")
            if not os.path.exists(src):
                raise RuntimeError("未找到构建产物 fnmonitorpro.fpk（%s 构建可能失败）" % plat)
            out = os.path.join(ROOT, "fnmonitorpro-%s-%s.fpk" % (version, plat))
            shutil.move(src, out)
            print("  -> %s" % out)
    finally:
        # 无论成功与否，恢复源 manifest 的原始 platform
        write_manifest(orig)

    print("")
    print("打包完成！")
    print("  fnmonitorpro-%s-x86.fpk （x86 机型）" % version)
    print("  fnmonitorpro-%s-arm.fpk （arm64 机型）" % version)
    print("在飞牛 OS 应用中心 -> 左下角\"手动安装\" -> 按架构选择 fpk 安装。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
