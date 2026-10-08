#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""changelog.py  [版本号] [--show | --from-readme | --interactive]
==============================================================
管理 manifest 的 changelog= 字段（全项目更新日志唯一来源；
release.py 发布时会把它写进 Release 说明）。

更新日志文本默认从 README.md 的「📋 版本历史」Markdown 表格自动获取：
先把新版本的更新内容写进 README 表格（如 | v2.17.3 | **新增...** |），
再运行本脚本即可同步到 manifest（**加粗** 自动转成 <b>...</b>）。

用法：
  changelog.py                为当前 manifest 的 version= 同步更新日志：
                              优先从 README 版本历史自动获取，取不到则改为手动输入
  changelog.py 2.17.3         为指定版本同步/更新更新日志
  changelog.py --from-readme  强制从 README 版本历史获取（README 无该版本则报错退出）
  changelog.py --interactive  跳过 README，改为逐行手动输入
  changelog.py --show         查看 manifest 当前 changelog 顶部若干条（不修改）
  changelog.py /?             显示用法

写入格式：
  - 自动模式：取 README 表格该行「内容」列，转成 v2.17.3<br><b>新增...</b>
  - 手动模式：逐行输入，每行一条（用 ① ② 等符号），空行结束，自动以 <br> 连接
  - 若该版本条目已存在则覆盖其内容（保留 vX.Y.Z 版本头）
  - 仅替换 changelog= 一行，其余 UTF-8 无 BOM 内容原样保留

建议在 release.py 发布前运行本脚本（或让 release.py 自动调用），
把当前版本的更新日志写入 manifest。
"""
import io
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")
README = os.path.join(ROOT, "README.md")
SHOW_COUNT = 3
VERSION_HISTORY_HEADER = "## 📋 版本历史"


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


def get_changelog(text):
    m = re.search(r"(?m)^changelog=(.*)$", text)
    return m.group(1).strip() if m else None


def readme_entries():
    """解析 README.md「版本历史」表格，返回 {版本号: 内容}（内容含 markdown ** 加粗）。"""
    if not os.path.exists(README):
        return {}
    entries = {}
    in_table = False
    with io.open(README, encoding="utf-8") as f:
        for line in f:
            if VERSION_HISTORY_HEADER in line:
                in_table = True
                continue
            if in_table and line.strip().startswith("## "):
                # 离开版本历史小节
                in_table = False
                continue
            if not in_table:
                continue
            m = re.match(r"^\|\s*(v[0-9]+\.[0-9]+\.[0-9]+)\s*\|(.*?)\s*\|\s*$", line)
            if m:
                ver = m.group(1)[1:]  # 去掉前缀 v
                entries[ver] = m.group(2).strip()
    return entries


def md_to_html(text):
    """把 markdown 的 **加粗** 转成 manifest 用的 <b>...</b>。"""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def readme_changelog_for(ver):
    """从 README 版本历史表取指定版本的更新内容（已转 HTML，不含 vX 前缀），取不到返回 None。"""
    entries = readme_entries()
    if ver in entries:
        return md_to_html(entries[ver])
    return None


def is_valid_version(v):
    return re.match(r"^[0-9]+(\.[0-9]+){1,2}$", v) is not None


def split_entries(changelog):
    """按版本头 vX.Y.Z 切分为一条条更新块。"""
    blocks = re.split(r"(?=v[0-9]+\.[0-9]+\.[0-9]+)", changelog)
    return [b for b in blocks if b.strip()]


def entry_version(block):
    m = re.match(r"v([0-9]+\.[0-9]+\.[0-9]+)", block)
    return m.group(1) if m else None


def show_changelog(changelog):
    if not changelog:
        print("[信息] manifest 暂无 changelog 内容")
        return
    blocks = split_entries(changelog)
    print("")
    print("=== manifest 更新日志（最新 %d 条）===" % min(SHOW_COUNT, len(blocks)))
    for i, b in enumerate(blocks[:SHOW_COUNT]):
        ver = entry_version(b) or "?"
        body = b[len("v%s" % ver):].lstrip("<br>")
        print("")
        print("[%d] v%s" % (i + 1, ver))
        # 把 <br> 还原为换行便于阅读
        for ln in body.split("<br>"):
            print("    %s" % ln)
    print("")
    print("（共 %d 个版本条目）" % len(blocks))


def read_multiline():
    """逐行读取更新内容，空行结束，自动用 <br> 连接。"""
    print("请逐行输入 v%s 的更新内容（每行一条，可用 ① ② ③ 等符号；空行结束）：" % "")
    lines = []
    try:
        while True:
            ln = input("  > ").strip()
            if ln == "":
                break
            lines.append(ln)
    except (EOFError, KeyboardInterrupt):
        print("")
    return "<br>".join(lines)


def confirm(prompt):
    try:
        ans = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans == "" or ans.lower() != "n"


def main():
    os.chdir(ROOT)
    args = [a for a in sys.argv[1:] if a not in ("/?", "-h", "--help")]

    show_only = "--show" in args
    from_readme = "--from-readme" in args
    interactive = "--interactive" in args
    ver_arg = next((a for a in args
                    if a not in ("--show", "--from-readme", "--interactive")), None)

    text = read_manifest()
    cur_ver = get_version(text)
    if not cur_ver:
        print("[错误] 无法从 manifest 读取 version=，请检查文件是否存在。")
        return 1

    changelog = get_changelog(text)
    if changelog is None:
        print("[错误] manifest 无 changelog= 字段，请先确认 manifest 格式。")
        return 1

    if show_only:
        show_changelog(changelog)
        return 0

    ver = ver_arg or cur_ver
    if ver_arg and not is_valid_version(ver_arg):
        print("[错误] 版本号格式不正确：%s（示例 2.17.3）" % ver_arg)
        return 1

    # 展示当前该版本现状
    blocks = split_entries(changelog)
    existing = None
    for b in blocks:
        if entry_version(b) == ver:
            existing = b
            break
    if existing:
        print("[信息] manifest 已存在 v%s 的更新日志，本次将覆盖其内容：" % ver)
        body = existing[len("v%s" % ver):].lstrip("<br>")
        for ln in body.split("<br>"):
            print("    当前：%s" % ln)
    else:
        print("[信息] 将为 v%s 新增更新日志（当前 manifest 顶部为 %s）。"
              % (ver, (entry_version(blocks[0]) if blocks else "空")))

    print("")
    # 内容来源：默认优先从 README 版本历史自动获取；--interactive 强制手动输入
    content = None
    if not interactive:
        rcontent = readme_changelog_for(ver)
        if rcontent is not None:
            content = rcontent
            print("[信息] 已从 README.md「版本历史」自动获取 v%s 更新日志。" % ver)
    if content is None:
        if from_readme:
            print("[错误] README.md 中未找到 v%s 的版本历史条目，无法自动获取。" % ver)
            print("        请先在 README 的「版本历史」表格中添加 v%s 一行，或改用 --interactive 手动输入。" % ver)
            return 1
        content = read_multiline()
    if not content:
        print("[提示] 未输入任何内容，未做任何修改。")
        return 0

    # manifest 的 changelog 只保留当前版本一条（完整历史见 README 版本历史表）
    new_changelog = "v%s<br>%s" % (ver, content)

    print("")
    print("[预览] 新 changelog（仅当前版本 v%s）：" % ver)
    preview = new_changelog if len(new_changelog) <= 90 else new_changelog[:90] + "..."
    print("    %s" % preview)

    if not confirm("确认写入 manifest？(仅保留当前版本，Y/n) "):
        print("[取消] 未做任何修改。")
        return 0

    text2 = re.sub(r"(?m)^changelog=.*$", "changelog=%s" % new_changelog, text, count=1)
    write_manifest(text2)

    back = get_changelog(read_manifest())
    if back is not None and back == new_changelog:
        print("[完成] v%s 更新日志已写入 manifest（仅当前版本）。" % ver)
        print("[提示] 现在可运行「release.py」发布（发布前会自动校验 changelog）。")
        return 0
    print("[警告] 写回校验失败，请手动检查 manifest changelog。")
    return 1


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 0
    print("")
    if sys.stdin.isatty():
        try:
            input("按 Enter 键退出...")
        except (EOFError, KeyboardInterrupt):
            pass
    else:
        print("窗口将在 5 秒后自动关闭...")
        time.sleep(5)
    sys.exit(rc)
