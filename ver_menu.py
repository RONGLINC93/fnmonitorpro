#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ver_menu.py — 控制台方向键选择菜单（无需第三方依赖，Windows 控制台即可）。
替代 tkinter 弹窗：在黑色窗口里用 ↑/↓ 移动高亮、回车确认，也可直接按数字键。
供 bump_version.py / lower_version.py 复用。
"""
try:
    import msvcrt
    _HAVE_MSVC = True
except Exception:
    _HAVE_MSVC = False

# 与 ver_gui.DISABLED 同义：标记为不可选的条目
DISABLED = "VER_MENU_DISABLED"


def _simple_select(title, cur, entries, validate=None):
    """无 msvcrt（非 Windows）时的退化实现：数字选择。"""
    selectable = [(i, l, v) for i, (l, v) in enumerate(entries) if v != DISABLED]
    print(title)
    print("当前版本：%s" % cur)
    for n, (i, lbl, ver) in enumerate(selectable):
        print("  %d. %s" % (n + 1, lbl))
    while True:
        try:
            ch = input("请选择（数字，输入 q 退出）：").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if ch.lower() == "q":
            return None
        if not ch.isdigit():
            continue
        d = int(ch) - 1
        if 0 <= d < len(selectable):
            _, lbl, ver = selectable[d]
            if ver is None:
                s = input("请输入版本号（如 2.18.0）：").strip()
                if not s:
                    continue
                if validate:
                    ok, msg = validate(s)
                    if not ok:
                        print(msg)
                        continue
                return s
            return ver
    return None


def console_select(title, cur, entries, validate=None):
    """在控制台用方向键选择。
    entries: [(label, version_or_None_or_DISABLED), ...]
      - version 为 None  -> 「自定义」：确认后要求输入版本号
      - version 为 DISABLED -> 灰色不可选
      - 其它字符串        -> 该版本号直接选中
    validate(value) -> (ok, msg)：自定义时校验用。
    返回选中的版本字符串，或 None（取消）。
    """
    if not _HAVE_MSVC:
        return _simple_select(title, cur, entries, validate)

    import os
    selectable = [(i, l, v) for i, (l, v) in enumerate(entries) if v != DISABLED]
    if not selectable:
        return None
    sel = 0

    def render():
        os.system("cls")
        print(title)
        print("当前版本：%s" % cur)
        print("（↑/↓ 移动高亮，回车确认；也可直接按数字键；Esc 取消）")
        print("")
        idx = 0
        for i, (lbl, ver) in enumerate(entries):
            if ver == DISABLED:
                print("     [不可选] %s" % lbl)
            else:
                mark = "> " if idx == sel else "  "
                print("%s%d. %s" % (mark, idx + 1, lbl))
                idx += 1

    def choose_current():
        _, lbl, ver = selectable[sel]
        if ver is None:
            os.system("cls")
            s = input("请输入版本号（如 2.18.0）：").strip()
            if not s:
                return False, None
            if validate:
                ok, msg = validate(s)
                if not ok:
                    print(msg)
                    input("按回车继续...")
                    return False, None
            return True, s
        return True, ver

    while True:
        render()
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            ok, val = choose_current()
            if ok:
                return val
        elif key == "\x1b":  # Esc
            return None
        elif key in ("\x00", "\xe0"):  # 扩展键前缀
            nxt = msvcrt.getwch()
            if nxt == "H":  # ↑
                sel = (sel - 1) % len(selectable)
            elif nxt == "P":  # ↓
                sel = (sel + 1) % len(selectable)
        elif key.isdigit():
            d = int(key) - 1
            if 0 <= d < len(selectable):
                sel = d
                ok, val = choose_current()
                if ok:
                    return val
        # 其它键忽略
