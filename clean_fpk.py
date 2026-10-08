#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""clean_fpk.py  [选项]
=============================================
清除构建/下载产生的 .fpk 安装包（仅 .fpk，不动源码、图标与 GitHub Release 上的文件）。

默认清理范围（项目根目录）：
  - fnmonitorpro.fpk                —— fnpack build 的中间产物（打包中途失败会残留）
  - fnmonitorpro-<版本>-x86.fpk     —— build.py / build.ps1 生成的正式产物
  - fnmonitorpro-<版本>-arm.fpk
  - building/ 目录下的 *.fpk       —— fnpack 工作目录残留
加 --all 时：上述范围内所有 *.fpk 一并删除（含从别处下载的其它命名包）。

用法：
  clean_fpk.py                    交互确认后删除默认范围内的 fpk
  clean_fpk.py -n                 只列出将被删除的文件，不实际删除（预演）
  clean_fpk.py -y                 不询问，直接删除
  clean_fpk.py --keep-latest 2    保留最新的 2 个版本（同一版本的 x86/arm 成对保留），其余删除
  clean_fpk.py --all              删除范围内所有 *.fpk（含非本项目命名的包）
  clean_fpk.py --dir D:\\downloads  额外扫描指定目录
  clean_fpk.py /?                 显示用法

返回码：0 成功（含无文件可删）；1 参数错误或删除失败。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILDING = os.path.join(ROOT, "building")

# 仅匹配本项目产物命名：fnmonitorpro.fpk / fnmonitorpro-<版本>-<架构>.fpk
OWN_RE = re.compile(r"^fnmonitorpro(-\d[^\\/]*)?(-(x86|arm))?\.fpk$", re.IGNORECASE)
# 带版本与架构的产物：用于 --keep-latest 按「同一版本的两个架构成对保留」分组
VER_RE = re.compile(r"^fnmonitorpro-(.+)-(x86|arm)\.fpk$", re.IGNORECASE)


def group_key(name):
    """--keep-latest 的分组键：同一版本号的 x86/arm 视为一组，避免删掉一半。"""
    m = VER_RE.match(name)
    return m.group(1).lower() if m else name.lower()


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
        n /= 1024.0
    return "%.1f GB" % n


def collect(dirs, delete_all):
    """返回 [(路径, 大小, 修改时间)]，按修改时间从旧到新排序。"""
    found = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            names = os.listdir(d)
        except OSError as e:
            print("[警告] 无法读取目录 %s：%s" % (d, e))
            continue
        for name in names:
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            if not name.lower().endswith(".fpk"):
                continue
            if not delete_all and not OWN_RE.match(name):
                continue
            try:
                st = os.stat(p)
            except OSError as e:
                print("[警告] 无法读取 %s：%s" % (p, e))
                continue
            found.append((p, st.st_size, st.st_mtime))
    found.sort(key=lambda x: x[2])
    return found


def remove(path):
    """删除文件；Windows 上下载的包可能带只读属性，先清除再删。"""
    try:
        if os.name == "nt" and not os.access(path, os.W_OK):
            os.chmod(path, 0o666)
        os.remove(path)
        return True
    except OSError as e:
        print("[错误] 删除失败 %s：%s" % (path, e))
        return False


def confirm(prompt):
    try:
        ans = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans == "" or ans.lower() != "n"


def main():
    args = sys.argv[1:]
    if args and args[0] in ("/?", "-h", "--help"):
        print(__doc__)
        return 0

    delete_all = False
    dry_run = False
    assume_yes = False
    keep = 0
    extra_dirs = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-a", "--all"):
            delete_all = True
        elif a in ("-n", "--dry-run"):
            dry_run = True
        elif a in ("-y", "--yes"):
            assume_yes = True
        elif a == "--keep-latest":
            i += 1
            if i >= len(args):
                print("[错误] --keep-latest 需要一个数字参数。")
                return 1
            try:
                keep = int(args[i])
            except ValueError:
                print("[错误] --keep-latest 的参数必须是整数：%s" % args[i])
                return 1
            if keep < 0:
                print("[错误] --keep-latest 不能为负数。")
                return 1
        elif a == "--dir":
            i += 1
            if i >= len(args):
                print("[错误] --dir 需要一个目录参数。")
                return 1
            extra_dirs.append(os.path.abspath(args[i]))
        else:
            print("[错误] 无法识别的参数：%s" % a)
            print("        可用：-a/--all  -n/--dry-run  -y/--yes  --keep-latest N  --dir 目录  /?")
            return 1
        i += 1

    dirs = [ROOT, BUILDING] + extra_dirs
    found = collect(dirs, delete_all)
    if not found:
        print("没有找到可清理的 .fpk 文件（%s）。" % ("、".join(dirs) if delete_all else "仅本项目产物命名"))
        return 0

    targets = found
    kept = []
    if keep > 0:
        # 按版本分组保留最新 N 组（同一版本的 x86/arm 一并保留）
        groups = {}
        for item in found:
            groups.setdefault(group_key(os.path.basename(item[0])), []).append(item)
        order = sorted(groups, key=lambda g: groups[g][-1][2])
        keep_groups = set(order[-keep:]) if keep < len(order) else set(order)
        kept = [it for g, items in groups.items() if g in keep_groups for it in items]
        kept_paths = set(k[0] for k in kept)
        targets = [it for it in found if it[0] not in kept_paths]

    total = sum(s for _, s, _ in targets)
    print("在 %s 发现 %d 个 .fpk：" % ("、".join(dirs), len(found)))
    kept_paths = set(k[0] for k in kept)
    for p, s, _ in found:
        mark = "保留" if p in kept_paths else "删除"
        print("  [%s] %s  (%s)" % (mark, p, human_size(s)))
    print("")
    print("将删除 %d 个文件，释放约 %s。" % (len(targets), human_size(total)))

    if dry_run:
        print("[预演] --dry-run 已启用，未删除任何文件。")
        return 0
    if not targets:
        print("[提示] 全部被 --keep-latest 保留，无需删除。")
        return 0

    if not assume_yes and not confirm("确认删除？(Y/n) "):
        print("[取消] 未删除任何文件。")
        return 0

    ok = 0
    failed = 0
    for p, _, _ in targets:
        if remove(p):
            print("  已删除 %s" % p)
            ok += 1
        else:
            failed += 1
    print("")
    print("[完成] 已删除 %d 个 fpk%s。" % (ok, "，失败 %d 个" % failed if failed else ""))
    return 1 if failed else 0


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
