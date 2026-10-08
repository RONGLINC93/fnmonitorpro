#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
"""lower_version.pyw — 双击运行（无控制台黑窗口）。
等价于 lower_version.py，但使用 pythonw 启动，不会弹出黑色命令行窗口。
运行结果写入 lower_version.log；操作完成后用 GUI 弹窗提示。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lower_version

rc = 1
try:
    rc = lower_version.main()
except SystemExit:
    raise
except Exception as e:  # 异常时尽量用弹窗告知，而非静默失败
    rc = 1
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("错误", str(e))
        r.destroy()
    except Exception:
        pass

# 无控制台（pythonw）时，用弹窗反馈结果，替代原本打印到终端的提示
if sys.stdin is None and lower_version.HAVE_GUI:
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        if rc == 0:
            messagebox.showinfo("完成", "版本降低已成功完成。")
        else:
            messagebox.showwarning("未完成", "版本降低未成功完成。")
        r.destroy()
    except Exception:
        pass

sys.exit(rc)
