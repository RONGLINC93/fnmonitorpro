#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ver_gui.py — 为 bump_version.py / lower_version.py 提供点击式 GUI 对话框。
依赖标准库 tkinter（Windows/macOS/Linux 自带，无需额外安装）。
仅在使用 GUI 时才被调用；无显示环境（CI/终端无 tkinter）时由调用方回退到终端输入。
"""
import tkinter as tk
from tkinter import messagebox, simpledialog

DISABLED = "VER_GUI_DISABLED"  # 用作「不可选」条目的标记


def pick_version(title, cur, entries, validate=None):
    """点击式版本选择。
    entries: [(label, version_or_None_or_DISABLED), ...]
      - version 为 None  -> 「自定义」按钮，点击后弹输入框
      - version 为 DISABLED -> 灰色不可点击
      - 其它字符串        -> 该版本号直接选中
    validate(value) -> (ok, msg)：自定义时校验用，返回 (False, 提示) 则要求重输。
    返回选中的版本字符串，或 None（取消）。
    """
    state = {"val": None}

    def on_custom():
        while True:
            s = simpledialog.askstring("自定义版本号",
                                       "请输入版本号（如 2.18.0）：", parent=root)
            if s is None:
                return
            s = s.strip()
            if validate is not None:
                ok, msg = validate(s)
                if not ok:
                    messagebox.showerror("格式错误", msg, parent=root)
                    continue
            state["val"] = s
            root.destroy()
            return

    def choose(v):
        state["val"] = v
        root.destroy()

    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    tk.Label(root, text="当前版本：%s" % cur, padx=14, pady=8,
             font=("Microsoft YaHei", 10)).pack(anchor="w")
    for label, ver in entries:
        if ver == DISABLED:
            tk.Button(root, text=label, width=46, pady=4, state="disabled").pack(
                padx=14, pady=3, fill="x")
        elif ver is None:
            tk.Button(root, text=label, width=46, pady=4, command=on_custom).pack(
                padx=14, pady=3, fill="x")
        else:
            tk.Button(root, text=label, width=46, pady=4,
                      command=lambda v=ver: choose(v)).pack(padx=14, pady=3, fill="x")
    tk.Button(root, text="取消", width=46, pady=4,
              command=root.destroy).pack(padx=14, pady=(3, 10), fill="x")
    root.mainloop()
    return state["val"]


def confirm_dialog(title, message):
    """是/否确认框，返回 bool。"""
    root = tk.Tk()
    root.withdraw()
    try:
        return bool(messagebox.askyesno(title, message))
    finally:
        root.destroy()


def multiline_dialog(title, message):
    """多行文本输入（更新日志用）。返回以 <br> 连接的字符串，或 None（取消/空）。"""
    state = {"val": None}

    def ok():
        state["val"] = txt.get("1.0", "end").strip()
        root.destroy()

    root = tk.Tk()
    root.title(title)
    tk.Label(root, text=message, padx=12, pady=8, wraplength=380,
             justify="left", font=("Microsoft YaHei", 9)).pack(anchor="w")
    txt = tk.Text(root, width=52, height=8)
    txt.pack(padx=12, pady=6)
    f = tk.Frame(root)
    f.pack(pady=(0, 10))
    tk.Button(f, text="确定", width=12, command=ok).pack(side="left", padx=10)
    tk.Button(f, text="取消", width=12, command=root.destroy).pack(side="left", padx=10)
    root.mainloop()

    val = state["val"]
    if not val:
        return None
    return val.replace("\r\n", "\n").replace("\n", "<br>")
