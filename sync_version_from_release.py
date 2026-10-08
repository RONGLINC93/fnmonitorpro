#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_version_from_release.py [选项]
=====================================
自动读取 GitHub 仓库「最新已发布 Release」的版本号，同步本地 manifest 的版本字段：
  - version_released = 最新已发布版本（发布事实的来源）
  - version          = 该版本 +1 补丁号（进入下一开发版，与 release.py / bump_version.py 的约定一致）

说明：
  - 通过 GitHub API 的 /releases/latest 获取「最新已发布」Release（自动排除草稿与预发布）。
  - 默认仓库 RONGLINC93/fnmonitorpro，可用 --repo owner/name 覆盖。
  - 仅在「版本号本身」上做同步，不改动 changelog（已发布版本的日志通常已在 manifest/README 中）。
  - 若会把本地 version 调低（本地开发版已领先于已发布版），会给出告警并需确认，避免破坏本地进度。

用法：
  sync_version_from_release.py               交互确认后同步（patch +1）
  sync_version_from_release.py --dry-run      仅预览将要做的改动，不写文件
  sync_version_from_release.py --yes          无人值守：不询问直接应用（适合 CI/脚本）
  sync_version_from_release.py --bump minor   下一开发版用 minor +1（如 2.17.4 -> 2.18.0）
  sync_version_from_release.py --bump none    version 直接等于已发布版本（不 +1）
  sync_version_from_release.py --repo owner/name   指定其它仓库
  sync_version_from_release.py --token xxxx       显式传入 GitHub Token（也可用 .env 的 GITHUB_TOKEN 或环境变量）
  sync_version_from_release.py /?                   显示用法
"""
import io
import json
import os
import re
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "manifest")
DEFAULT_REPO = "RONGLINC93/fnmonitorpro"
API = "https://api.github.com/repos/%s/releases/latest"


# ---------- manifest 读写 ----------
def read_manifest():
    with io.open(MANIFEST, encoding="utf-8", newline="") as f:
        return f.read()


def write_manifest(text):
    with io.open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def get_field(text, name):
    m = re.search(r"(?m)^%s=(.*)$" % name, text)
    return m.group(1).strip() if m else ""


# ---------- 版本解析 ----------
def parse_core(ver):
    m = re.match(r"^([0-9]+)\.([0-9]+)\.([0-9]+)", ver)
    if not m:
        return None
    return m.groups()


def is_valid_version(ver):
    return parse_core(ver) is not None


def ver_key(ver):
    """返回可比较的 (int,int,int)；无法解析时返回 (0,0,0)，避免字符串比较把 2.10 判成小于 2.9。"""
    c = parse_core(ver or "")
    return tuple(int(x) for x in c) if c else (0, 0, 0)


def bump_ver(ver, kind="patch"):
    """ver 基础上生成下一开发版：patch/minor/major +1，或 none 表示不变。"""
    c = parse_core(ver)
    if not c:
        return None
    ma, mi, pa = c
    if kind == "patch":
        return "%s.%s.%d" % (ma, mi, int(pa) + 1)
    if kind == "minor":
        return "%s.%d.0" % (ma, int(mi) + 1)
    if kind == "major":
        return "%d.0.0" % (int(ma) + 1)
    if kind == "none":
        return ver
    return None


def extract_version(tag):
    """从 Release 的 tag_name 中提取 x.y.z（兼容 v2.17.4 / 2.17.4 / release-2.17.4）。"""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", tag or "")
    return "%s.%s.%s" % m.groups() if m else None


# ---------- GitHub ----------
def load_env_token():
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return ""
    with io.open(p, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                if k.strip() == "GITHUB_TOKEN":
                    return v.strip().strip("'").strip('"')
    return ""


def fetch_latest_release_tag(repo, token):
    url = API % repo
    headers = {
        "User-Agent": "sync-version-from-release",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = "token %s" % token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "该仓库暂无已发布 Release（或只有草稿/预发布）"
        if e.code in (401, 403):
            return None, "无权限或被限流（401/403）：请配置有效 GITHUB_TOKEN，或稍后重试"
        return None, "GitHub API 返回 HTTP %s" % e.code
    except urllib.error.URLError as e:
        return None, "无法连接 GitHub：%s" % e.reason
    except Exception as e:  # 超时等
        return None, "请求 GitHub 失败：%s" % e
    tag = data.get("tag_name", "")
    if not tag:
        return None, "Release 缺少 tag_name"
    return tag, None


# ---------- 交互 ----------
def confirm(prompt):
    try:
        a = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return a in ("", "y", "yes")


def apply_to_manifest(text, new_version, new_released):
    text2 = re.sub(r"(?m)^version=[0-9].*$", "version=%s" % new_version, text, count=1)
    if re.search(r"(?m)^version_released=.*$", text2):
        text2 = re.sub(r"(?m)^version_released=.*$", "version_released=%s" % new_released, text2, count=1)
    else:
        text2 = text2.rstrip("\n") + "\nversion_released=%s\n" % new_released
    return text2


def main():
    os.chdir(ROOT)
    argv = sys.argv[1:]
    if "/?" in argv or "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0

    repo = DEFAULT_REPO
    token = os.environ.get("GITHUB_TOKEN", "")
    bump = "patch"
    dry_run = False
    yes = False

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--repo":
            i += 1
            repo = argv[i] if i < len(argv) else ""
        elif a == "--token":
            i += 1
            token = argv[i] if i < len(argv) else ""
        elif a == "--bump":
            i += 1
            bump = argv[i] if i < len(argv) else "patch"
        elif a == "--dry-run":
            dry_run = True
        elif a == "--yes" or a == "-y":
            yes = True
        i += 1

    if not repo:
        print("[错误] 未指定有效的 --repo。")
        return 1
    if bump not in ("patch", "minor", "major", "none"):
        print("[错误] --bump 仅支持 patch/minor/major/none，收到：%s" % bump)
        return 1
    if not token:
        token = load_env_token()

    # 1) 拉取最新已发布 Release
    print("[信息] 查询仓库 %s 的最新已发布 Release ..." % repo)
    tag, err = fetch_latest_release_tag(repo, token)
    if err:
        print("[错误] %s" % err)
        return 1
    rel = extract_version(tag)
    if not rel:
        print("[错误] 无法从 tag「%s」解析出 x.y.z 版本号。" % tag)
        return 1
    print("[信息] 最新已发布版本：tag=%s -> %s" % (tag, rel))

    # 2) 计算将要写入的值
    new_released = rel
    new_version = bump_ver(rel, bump)
    if not new_version:
        print("[错误] 无法基于 %s 计算下一开发版（bump=%s）。" % (rel, bump))
        return 1

    text = read_manifest()
    cur_version = get_field(text, "version")
    cur_released = get_field(text, "version_released")

    print("")
    print("============== 同步计划 ==============")
    print("当前 manifest : version=%s  version_released=%s" % (cur_version or "(无)", cur_released or "(无)"))
    print("最新 Release  : %s" % rel)
    print("将写入        : version_released=%s" % new_released)
    print("                version=%s  （%s +1）" % (new_version, rel) if bump != "none"
          else "                version=%s  （等于已发布版本）" % new_version)
    print("======================================")

    if new_version != cur_version and ver_key(new_version) < ver_key(cur_version):
        print("[警告] 这会把本地开发版从 %s 降低到 %s（本地可能已有领先的开发进度）！" % (cur_version, new_version))

    if dry_run:
        print("[dry-run] 未做任何修改。")
        return 0

    if new_version == cur_version and new_released == cur_released:
        print("[完成] manifest 已是最新（version=%s / version_released=%s），无需修改。" % (cur_version, cur_released))
        return 0

    if not yes:
        if not confirm("确认写入 manifest？(Y/n) "):
            print("[取消] 未做任何修改。")
            return 0

    text2 = apply_to_manifest(text, new_version, new_released)
    write_manifest(text2)

    # 3) 校验
    back = read_manifest()
    bv = get_field(back, "version")
    br = get_field(back, "version_released")
    if bv == new_version and br == new_released:
        print("[完成] manifest 已同步到最新发布版：")
        print("        version=%s（下一开发版）  version_released=%s（已发布）" % (bv, br))
        print("[提示] 已发布版本的更新日志请确认已在 manifest/README 中；如需补充可运行 changelog.py。")
        return 0
    print("[警告] 写回校验失败：读回 version=%s version_released=%s（预期 %s / %s），请手动检查 manifest。"
          % (bv, br, new_version, new_released))
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
