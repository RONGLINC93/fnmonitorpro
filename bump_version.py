#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bump_version.py  [patch|minor|major|x.y.z]
=============================================
递增 manifest 的 version=（全项目唯一版本源；构建/发布/关于页均读这里）。
仅替换 version= 一行（其余 UTF-8 无 BOM 原样保留）；
同时把 version_released= 设为「比新 version 低一个版本」的版本号
（如 version 变 2.17.3 则 version_released=2.17.2；自定义版本同理，始终比新版本低一个），
作为新的已发布版本记录——使 UI 正确区分「已发布版 / 开发版」。

用法：
  bump_version.py               交互菜单：1=patch / 2=minor / 3=major / 4=自定义
  bump_version.py patch         补丁号 +1   （2.17.1 -> 2.17.2）
  bump_version.py minor         次版本 +1   （2.17.1 -> 2.18.0）
  bump_version.py major         主版本 +1   （2.17.1 -> 3.0.0）
  bump_version.py 2.18.0        直接指定版本号
  bump_version.py --no-changelog  仅递增 version/version_released，不更新 changelog
  bump_version.py /?            显示用法

默认行为：递增版本后会同步在 manifest 的 changelog 顶部新增该新版本的更新日志
（优先从 README.md「📋 版本历史」表自动获取，**加粗**自动转 <b>…</b>；
README 无该版本行则交互提示手动输入）。与 lower_version.py 默认裁剪高版本日志形成对称：
升版加一条、降版删高版。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")


def read_manifest():
    with io.open(MANIFEST, encoding="utf-8", newline="") as f:
        return f.read()


def write_manifest(text):
    # UTF-8 无 BOM，原样保留其余内容（含原有换行符）
    with io.open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def get_version(text):
    m = re.search(r"(?m)^version=([0-9].*)$", text)
    return m.group(1).strip() if m else ""


def parse_core(ver):
    core = re.split(r"[-+]", ver, 1)[0]
    parts = core.split(".")
    while len(parts) < 3:
        parts.append("0")
    return parts[:3]


def is_valid_version(v):
    return re.match(r"^[0-9]+(\.[0-9]+){1,2}$", v) is not None


def compute_new(mode, cur):
    ma, mi, pa = parse_core(cur)
    if mode == "patch":
        return "%s.%s.%d" % (ma, mi, int(pa) + 1)
    if mode == "minor":
        return "%s.%d.0" % (ma, int(mi) + 1)
    if mode == "major":
        return "%d.0.0" % (int(ma) + 1)
    return None


def dec_one(ver):
    """返回比 ver 低一个补丁号的版本（最低位 -1；到 0 则向高位借位）。"""
    m = re.match(r"^([0-9]+)\.([0-9]+)\.([0-9]+)", ver)
    if not m:
        return ver
    ma, mi, pa = [int(x) for x in m.groups()]
    if pa > 0:
        pa -= 1
    elif mi > 0:
        mi -= 1
        pa = 0
    elif ma > 0:
        ma -= 1
        mi = 0
        pa = 0
    else:
        return ver  # 0.0.0 无法再降
    return "%d.%d.%d" % (ma, mi, pa)


def confirm(prompt):
    try:
        ans = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans == "" or ans.lower() != "n"


def choose_interactive(cur):
    while True:
        ma, mi, pa = parse_core(cur)
        newp = "%s.%s.%d" % (ma, mi, int(pa) + 1)
        newm = "%s.%d.0" % (ma, int(mi) + 1)
        newj = "%d.0.0" % (int(ma) + 1)
        print("")
        print("请选择递增模式（当前版本 %s）：" % cur)
        print("  [1] patch  补丁号 +1  -> %s" % newp)
        print("  [2] minor  次版本 +1  -> %s" % newm)
        print("  [3] major  主版本 +1  -> %s" % newj)
        print("  [4] 自定义 手动输入版本号")
        try:
            ch = input("请按 1 / 2 / 3 / 4 选择：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[取消] 未选择。")
            return None
        if ch == "1":
            return newp
        if ch == "2":
            return newm
        if ch == "3":
            return newj
        if ch == "4":
            while True:
                v = input("请输入新版本号（如 2.18.0）：").strip()
                if not v:
                    print("[取消] 未输入版本号。")
                    return None
                if is_valid_version(v):
                    return v
                print("[错误] 版本号格式不正确：%s（示例 2.18.0）" % v)
            # unreachable
        print("[取消] 未选择。")
        return None


def read_multiline():
    """逐行读取更新内容，空行结束，各行以 <br> 连接。"""
    print("（逐行输入更新内容，每行一条，空行结束）")
    lines = []
    try:
        while True:
            ln = input("> ")
            if ln == "":
                break
            lines.append(ln)
    except (EOFError, KeyboardInterrupt):
        pass
    return "<br>".join(lines)


def sync_changelog(text, ver):
    """递增成功后，为新版本 ver 在 manifest changelog 顶部加一条：
    优先从 README.md 版本历史自动获取，取不到则交互提示输入。
    """
    m = re.search(r"(?m)^changelog=(.*)$", text)
    cur_cl = m.group(1).strip() if m else ""
    if cur_cl.startswith("v%s" % ver) or cur_cl.startswith("v%s<br>" % ver):
        print("[信息] manifest 已含 v%s 的更新日志，跳过 changelog 更新。" % ver)
        return text
    entry = changelog.readme_changelog_for(ver)
    if entry is None:
        print("")
        print("=== bump 后：为 v%s 填写更新日志 ===" % ver)
        print("[提示] README.md「版本历史」未找到 v%s，请手动输入内容（或直接回车跳过，稍后运行 changelog.py）：" % ver)
        content = read_multiline()
        if not content:
            print("[提示] 未填写 v%s 更新日志，changelog 未改动（请稍后补）。" % ver)
            return text
        entry = "v%s<br>%s" % (ver, content)
    else:
        print("[信息] 已从 README.md「版本历史」自动获取 v%s 更新日志。" % ver)
    new_cl = entry + ("<br>" + cur_cl if cur_cl else "")
    if m:
        text = re.sub(r"(?m)^changelog=.*$", "changelog=%s" % new_cl, text, count=1)
    else:
        text = text.rstrip("\n") + "\nchangelog=%s\n" % new_cl
    print("[完成] 已将 v%s 更新日志写入 manifest 顶部。" % ver)
    return text


def main():
    global changelog
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)
    import changelog
    args = sys.argv[1:]
    if args and args[0] in ("/?", "-h", "--help"):
        print(__doc__)
        return 0

    text = read_manifest()
    cur = get_version(text)
    if not cur:
        print("[错误] 无法从 manifest 读取 version=，请检查文件是否存在。")
        return 1

    no_changelog = "--no-changelog" in args
    args = [a for a in args if a != "--no-changelog"]

    mode = args[0] if args else None
    if mode in ("patch", "minor", "major"):
        new = compute_new(mode, cur)
    elif mode:
        if not is_valid_version(mode):
            print("[错误] 无法识别的参数：%s" % mode)
            print("        可用：patch / minor / major / 显式版本号（如 2.18.0）")
            return 1
        new = mode
    else:
        new = choose_interactive(cur)
        if new is None:
            return 0

    rel = dec_one(new)
    print("")
    print("[信息] 当前版本：%s" % cur)
    print("[信息] 新版本号：%s（开发版）" % new)
    print("[信息] version_released 将设为 %s（比新版本低一个版本，作已发布版记录；UI 显示「已发布 v%s」）" % (rel, rel))

    if new == cur:
        print("[提示] 新版本与当前版本相同，无需修改。")
        return 0

    if not confirm("确认写入 manifest？(Y/n) "):
        print("[取消] 未做任何修改。")
        return 0

    text2 = re.sub(r"(?m)^version=[0-9].*$", "version=%s" % new, text, count=1)
    if re.search(r"(?m)^version_released=.*$", text2):
        text2 = re.sub(r"(?m)^version_released=.*$", "version_released=%s" % rel, text2, count=1)
    else:
        if not text2.endswith("\n"):
            text2 += "\n"
        text2 += "version_released=%s\n" % rel

    if not no_changelog:
        text2 = sync_changelog(text2, new)
    else:
        print("[信息] 已加 --no-changelog，跳过 changelog 更新。")

    write_manifest(text2)

    back = get_version(read_manifest())
    if back == new:
        print("[完成] manifest 版本号已更新：%s -> %s（开发版）" % (cur, new))
        print("[完成] version_released 已设为 %s（比 %s 低一个版本，已发布版记录；UI 将显示「DEV 开发版 · 已发布 v%s」）" % (rel, new, rel))
        if not no_changelog:
            print("[完成] v%s 的更新日志已写入 manifest 顶部（README 缺失时由你手动输入）。" % new)
        else:
            print("[提示] 如需同步更新日志，可运行「changelog.py」/「release.py」。")
        return 0
    print("[警告] 写入后读回的版本是 %s，与预期 %s 不一致，请手动检查 manifest。" % (back, new))
    return 1


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 0
    if sys.stdin.isatty():
        try:
            input("\n按 Enter 键退出...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(rc)
