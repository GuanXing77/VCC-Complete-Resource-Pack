#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 sources.json 列出的上游 VPM 源同步进 index.json。

规则
----
* 清单里已有的包：只补充上游新增的版本，本地已有版本保持不动（加 --refresh 才用上游数据覆盖）；
* 上游新增的包：整体加入清单；
* 上游标记为 private 的版本：跳过，不写进清单；
* 每个包的版本按版本号从新到旧排序。

用法
----
    python update_vpm.py                # 默认：抓取上游并写入 index.json
    python update_vpm.py --dry-run      # 只预览变更，不写文件
    python update_vpm.py --refresh      # 写入的同时，用上游数据覆盖本地同版本条目
    python update_vpm.py --index path\\index.json --sources path\\sources.json
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_INDEX = ROOT / "index.json"
DEFAULT_SOURCES = ROOT / "sources.json"

TIMEOUT = 30
RETRIES = 3
USER_AGENT = (
    "VCC-Complete-Resource-Pack/1.0 "
    "(+https://github.com/guanxing77/VCC-Complete-Resource-Pack)"
)


# --------------------------------------------------------------------------- #
# 读写
# --------------------------------------------------------------------------- #
def read_json(path):
    with path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def fetch_json(url):
    """下载并校验一个 VPM 清单，失败时重试。"""
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                },
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read()
            data = json.loads(raw.decode(charset, errors="replace").lstrip("\ufeff"))
            if not isinstance(data, dict) or not isinstance(data.get("packages"), dict):
                raise ValueError("响应不是 VPM 清单（缺少 packages 字段）")
            return data
        except (OSError, ValueError) as exc:  # URLError / HTTPError 都是 OSError
            last_error = exc
            if attempt < RETRIES:
                time.sleep(attempt * 2)
    raise RuntimeError("抓取失败：%s" % last_error)


def load_sources(path):
    data = read_json(path)
    raw = data.get("sources") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise SystemExit("%s 格式不正确：需要一个 sources 数组" % path)

    urls = []
    for item in raw:
        if isinstance(item, str):
            url = item.strip()
        elif isinstance(item, dict):
            url = str(item.get("url") or "").strip()
        else:
            url = ""
        if url and url not in urls:
            urls.append(url)

    if not urls:
        raise SystemExit("%s 里没有可用的源地址" % path)
    return urls


# --------------------------------------------------------------------------- #
# 版本排序
# --------------------------------------------------------------------------- #
def version_key(version):
    """把 1.10.2 / 0.2.0-beta.3 这类版本号转成可比较的元组。"""
    text = str(version).strip()
    main, _, pre = text.partition("-")

    numbers = []
    for part in main.split("."):
        match = re.match(r"\d+", part)
        numbers.append(int(match.group(0)) if match else 0)

    pre_key = []
    for part in re.split(r"[.\-+]", pre):
        if not part:
            continue
        match = re.match(r"\d+", part)
        if match:
            pre_key.append((1, int(match.group(0)), ""))
        else:
            pre_key.append((0, 0, part))

    return (numbers, 0 if pre else 1, pre_key)


def sort_versions(versions):
    ordered = sorted(versions.keys(), key=version_key, reverse=True)
    return {name: versions[name] for name in ordered}


# --------------------------------------------------------------------------- #
# 合并
# --------------------------------------------------------------------------- #
def merge_source(target, source, source_url, refresh, stats):
    packages = source.get("packages") or {}

    for package_id, package in packages.items():
        versions = (package or {}).get("versions")
        if not isinstance(versions, dict) or not versions:
            continue

        # private 版本不对外发布，跳过
        usable = {}
        for version, meta in versions.items():
            if not isinstance(meta, dict) or meta.get("private"):
                continue
            usable[version] = meta
        if not usable:
            continue

        target_package = target["packages"].get(package_id)
        if target_package is None:
            target_package = {"versions": {}}
            target["packages"][package_id] = target_package
            stats["new_packages"].append(package_id)

        target_versions = target_package.setdefault("versions", {})

        for version, meta in usable.items():
            entry = deepcopy(meta)
            entry.setdefault("name", package_id)
            entry.setdefault("version", version)
            entry.setdefault("repo", source_url)

            if version not in target_versions:
                target_versions[version] = entry
                stats["new_versions"] += 1
                stats["per_package"][package_id] = stats["per_package"].get(package_id, 0) + 1
            elif refresh:
                target_versions[version] = entry
                stats["refreshed"] += 1


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="同步上游 VPM 清单到 index.json")
    parser.add_argument("--index", default=str(DEFAULT_INDEX), help="目标清单，默认 ./index.json")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES), help="上游列表，默认 ./sources.json")
    parser.add_argument("--dry-run", action="store_true", help="只报告变更，不写 index.json（默认会写入）")
    parser.add_argument("--refresh", action="store_true", help="用上游数据覆盖本地同版本条目")
    args = parser.parse_args(argv)

    index_path = Path(args.index)
    if not index_path.is_file():
        raise SystemExit("找不到清单文件：%s" % index_path)

    target = read_json(index_path)
    if not isinstance(target.get("packages"), dict):
        raise SystemExit("%s 不是 VPM 清单：缺少 packages 字段" % index_path)

    before = json.dumps(target, ensure_ascii=False, sort_keys=True)

    stats = {
        "new_packages": [],
        "new_versions": 0,
        "refreshed": 0,
        "per_package": {},
        "failed": [],
    }
    succeeded = 0

    for url in load_sources(Path(args.sources)):
        try:
            source = fetch_json(url)
        except RuntimeError as exc:
            stats["failed"].append(str(exc))
            print("[警告] %s" % exc, file=sys.stderr)
            continue

        merge_source(target, source, url, args.refresh, stats)
        succeeded += 1
        count = len(source.get("packages") or {})
        print("[源] %s（%d 个包）" % (url, count))

    for package in target["packages"].values():
        versions = package.get("versions") if isinstance(package, dict) else None
        if isinstance(versions, dict):
            package["versions"] = sort_versions(versions)

    after = json.dumps(target, ensure_ascii=False, sort_keys=True)
    changed = after != before

    total_versions = sum(
        len(pkg.get("versions") or {})
        for pkg in target["packages"].values()
        if isinstance(pkg, dict)
    )

    print("")
    if stats["new_packages"]:
        print("新增包 %d 个：%s" % (len(stats["new_packages"]), ", ".join(stats["new_packages"])))
    else:
        print("没有新增包")
    print("新增版本 %d 个，刷新版本 %d 个" % (stats["new_versions"], stats["refreshed"]))

    if stats["per_package"]:
        top = sorted(stats["per_package"].items(), key=lambda item: item[1], reverse=True)[:15]
        print("变更最多的包：" + "；".join("%s +%d" % (name, count) for name, count in top))

    print("清单现有 %d 个包 / %d 个版本" % (len(target["packages"]), total_versions))

    if succeeded == 0:
        print("所有上游源都抓取失败，未修改文件", file=sys.stderr)
        return 1

    if args.dry_run:
        print("[dry-run] " + ("有变更，未写入文件" if changed else "没有变更，未写入文件"))
        return 0

    # 默认行为：拉取结果写入 index.json（内容没有变化时也重新写入，保证文件是最新的规范格式）
    write_json(index_path, target)
    print("已写入 %s（%s）" % (index_path, "内容有更新" if changed else "内容无变化"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
