#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lower_version.py  [patch|minor|major|x.y.z]
=============================================
降低 manifest 的 version=（全项目唯一版本源；构建/发布/关于页均读这里）。
仅替换 version= 一行（其余 UTF-8 无 BOM 原样保留）；
同时把 version_released= 设为「比新 version 低一个版本」的版本号
（如 version 变 2.17.2 则 version_released=2.17.1；自定义版本同理，始终比新版本低一个），
保持与 bump_version.py 一致的「已发布版 / 开发版」记录规则。

用法：
  lower_version.py               交互菜单（点击式 GUI：补丁-1 / 次版本-1 / 主版本-1 / 自定义）
  lower_version.py patch         补丁号 -1   （2.17.2 -> 2.17.1；2.18.0 -> 2.17.0）
  lower_version.py minor         次版本 -1   （2.18.0 -> 2.17.0；3.0.0 -> 2.0.0）
  lower_version.py major         主版本 -1   （3.0.0 -> 2.0.0）
  lower_version.py 2.16.5        直接指定更低的版本号（无 GUI 依赖，适合脚本/CI）
  lower_version.py --keep-changelog  仅降低 version/version_released，不改动 changelog
  lower_version.py /?            显示用法

注：无参数运行时，若环境支持 tkinter 会弹出点击式窗口选择降低模式；
传入 patch/minor/major/版本号 等参数则直接进入对应逻辑（无需 GUI，便于自动化）。

默认行为：降低版本后会同步裁剪 manifest 的 changelog——移除其中版本号高于新版本
的条目（回退开发版时不应保留更高版本的更新日志），其余条目原样保留。
"""
import io
import os
import re
import sys

# 无控制台环境（pythonw / .pyw）下 sys.stdout 为 None，print 会崩溃；重定向到空设备丢弃。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
    sys.stderr = sys.stdout

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")

sys.path.insert(0, ROOT)
try:
    import ver_gui
    HAVE_GUI = True
except Exception:
    HAVE_GUI = False


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


def compute_lower(mode, cur):
    """按模式计算降低后的版本号；已到 0.0.0 无法再降时返回 None。"""
    ma, mi, pa = parse_core(cur)
    ma, mi, pa = int(ma), int(mi), int(pa)
    if mode == "patch":
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
            return None
    elif mode == "minor":
        if mi > 0:
            mi -= 1
            pa = 0
        elif ma > 0:
            ma -= 1
            mi = 0
            pa = 0
        else:
            return None
    elif mode == "major":
        if ma > 0:
            ma -= 1
            mi = 0
            pa = 0
        else:
            return None
    else:
        return None
    return "%d.%d.%d" % (ma, mi, pa)


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
        newp = dec_one(cur)                       # patch -1
        newm = compute_lower("minor", cur)        # minor -1
        newj = compute_lower("major", cur)        # major -1
        print("")
        print("请选择降低模式（当前版本 %s）：" % cur)
        print("  [1] patch  补丁号 -1  -> %s" % newp)
        print("  [2] minor  次版本 -1  -> %s" % (newm if newm else "（已是最低）"))
        print("  [3] major  主版本 -1  -> %s" % (newj if newj else "（已是最低）"))
        print("  [4] 自定义 手动输入更低的版本号")
        try:
            ch = input("请按 1 / 2 / 3 / 4 选择：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[取消] 未选择。")
            return None
        if ch == "1":
            return newp
        if ch == "2":
            if newm is None:
                print("[错误] 已是最低版本 0.0.0，无法再降。")
                continue
            return newm
        if ch == "3":
            if newj is None:
                print("[错误] 已是最低版本 0.0.0，无法再降。")
                continue
            return newj
        if ch == "4":
            while True:
                v = input("请输入更低的版本号（如 2.16.5）：").strip()
                if not v:
                    print("[取消] 未输入版本号。")
                    return None
                if not is_valid_version(v):
                    print("[错误] 版本号格式不正确：%s（示例 2.16.5）" % v)
                    continue
                if parse_version_tuple(v) >= parse_version_tuple(cur):
                    print("[错误] 该版本（%s）不低于当前版本（%s），请用 bump_version.py 递增。" % (v, cur))
                    continue
                return v
        print("[取消] 未选择。")
        return None


def parse_version_tuple(ver):
    ma, mi, pa = parse_core(ver)
    return (int(ma), int(mi), int(pa))


def split_changelog(text):
    """把 changelog 字符串拆成 [(版本号, 完整片段)]，片段含 'vX.Y.Z' 标记及后续内容。"""
    raw = re.split(r"(v[0-9]+\.[0-9]+\.[0-9]+)", text)
    entries = []
    for i in range(1, len(raw) - 1, 2):
        ver = raw[i][1:]
        entries.append((ver, raw[i] + raw[i + 1]))
    return entries


def drop_higher_changelog(changelog, new_ver):
    """移除 changelog 中版本号高于 new_ver 的条目（回退开发版时不应保留更高版本的日志）。"""
    kept = [full for ver, full in split_changelog(changelog)
            if parse_version_tuple(ver) <= parse_version_tuple(new_ver)]
    return "".join(kept)


def main():
    os.chdir(ROOT)
    args = sys.argv[1:]
    if args and args[0] in ("/?", "-h", "--help"):
        print(__doc__)
        return 0

    text = read_manifest()
    cur = get_version(text)
    if not cur:
        print("[错误] 无法从 manifest 读取 version=，请检查文件是否存在。")
        return 1

    keep_changelog = "--keep-changelog" in args
    args = [a for a in args if a != "--keep-changelog"]

    mode = args[0] if args else None
    if mode in ("patch", "minor", "major"):
        new = compute_lower(mode, cur)
        if new is None:
            print("[错误] 当前版本 %s 已是最低（0.0.0），无法再降。" % cur)
            return 1
    elif mode:
        if not is_valid_version(mode):
            print("[错误] 无法识别的参数：%s" % mode)
            print("        可用：patch / minor / major / 显式版本号（如 2.16.5）")
            return 1
        if parse_version_tuple(mode) >= parse_version_tuple(cur):
            print("[错误] 指定版本 %s 不低于当前版本 %s，请用 bump_version.py 递增。" % (mode, cur))
            return 1
        new = mode
    else:
        if HAVE_GUI:
            newp = dec_one(cur)
            newm = compute_lower("minor", cur)
            newj = compute_lower("major", cur)

            def _validate(v):
                if not is_valid_version(v):
                    return (False, "版本号格式不正确（示例 2.16.5）")
                if parse_version_tuple(v) >= parse_version_tuple(cur):
                    return (False, "该版本不低于当前版本 %s，请用 bump_version.py 递增。" % cur)
                return (True, "")

            entries = [
                ("补丁号 -1  -> %s" % newp, newp),
                ("次版本 -1  -> %s" % (newm if newm else "（已是最低）"),
                 newm if newm else ver_gui.DISABLED),
                ("主版本 -1  -> %s" % (newj if newj else "（已是最低）"),
                 newj if newj else ver_gui.DISABLED),
                ("自定义更低版本号...", None),
            ]
            new = ver_gui.pick_version(
                "lower_version - 选择降低模式", cur, entries, validate=_validate)
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

    if HAVE_GUI:
        ok = ver_gui.confirm_dialog(
            "确认写入",
            "确认写入 manifest？\n\n新版本：%s（开发版）\nversion_released：%s" % (new, rel))
    else:
        ok = confirm("确认写入 manifest？(Y/n) ")
    if not ok:
        print("[取消] 未做任何修改。")
        return 0

    text2 = re.sub(r"(?m)^version=[0-9].*$", "version=%s" % new, text, count=1)
    if re.search(r"(?m)^version_released=.*$", text2):
        text2 = re.sub(r"(?m)^version_released=.*$", "version_released=%s" % rel, text2, count=1)
    else:
        if not text2.endswith("\n"):
            text2 += "\n"
        text2 += "version_released=%s\n" % rel

    cl_changed = False
    if not keep_changelog:
        m = re.search(r"(?m)^changelog=(.*)$", text2)
        if m:
            orig = m.group(1)
            pruned = drop_higher_changelog(orig, new)
            if pruned != orig:
                text2 = re.sub(r"(?m)^changelog=.*$", "changelog=%s" % pruned, text2, count=1)
                cl_changed = True
            elif not orig:
                pass
            else:
                print("[信息] changelog 中无高于 v%s 的条目，无需裁剪。" % new)
        else:
            print("[提示] manifest 无 changelog 字段，跳过裁剪。")

    write_manifest(text2)

    back = get_version(read_manifest())
    if back == new:
        print("[完成] manifest 版本号已降低：%s -> %s（开发版）" % (cur, new))
        print("[完成] version_released 已设为 %s（比 %s 低一个版本，已发布版记录；UI 将显示「DEV 开发版 · 已发布 v%s」）" % (rel, new, rel))
        if cl_changed:
            print("[完成] changelog 已裁剪：移除所有高于 v%s 的更新日志条目，其余原样保留。" % new)
            print("[提示] 如需为 v%s 补更新日志，可运行「changelog.py」/「release.py」。" % new)
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
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input("\n按 Enter 键退出...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(rc)
