#!/usr/bin/env python3
"""catalog.json schema 守門 — routine 於 commit 前執行，失敗即不 push。"""
import json
import re
import sys

CATEGORIES = {"plugin", "skill", "mcp", "technique", "official", "tool"}
SOURCES = {"github", "anthropic", "community", "blog"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check(path="catalog.json"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert DATE.match(data["updated"]), "updated 格式錯誤"
    ids = [e["id"] for e in data["entries"]]
    assert len(ids) == len(set(ids)), "id 重複"
    for e in data["entries"]:
        assert e["category"] in CATEGORIES, f"未知 category: {e['id']}"
        assert e["source"] in SOURCES, f"未知 source: {e['id']}"
        for k in ("title", "url", "summary"):
            assert e.get(k), f"{e['id']} 缺 {k}"
        assert DATE.match(e["added"]), f"{e['id']} added 格式錯誤"
        assert DATE.match(e["last_seen"]), f"{e['id']} last_seen 格式錯誤"
        assert isinstance(e.get("tags", []), list), f"{e['id']} tags 非 list"
        if e["id"].startswith("gh:"):
            assert isinstance(e.get("stars"), int), f"{e['id']} 缺 stars"
    print(f"OK — {len(ids)} entries")


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "catalog.json")
