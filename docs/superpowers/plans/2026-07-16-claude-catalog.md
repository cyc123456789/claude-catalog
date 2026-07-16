# Claude-Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `Claude-Catalog` GitHub Pages 網站（累積式 Claude 生態目錄）與每週二、五自動蒐集的 cloud routine。

**Architecture:** 沿用使用者既有「JSON 資料 / 版面分離」模式：cloud routine 只寫 `catalog.json`，靜態 `index.html` 一次寫好、純前端 fetch 渲染。無 build step、無後端。spec 見 `docs/superpowers/specs/2026-07-16-claude-catalog-design.md`。

**Tech Stack:** 純 HTML/CSS/JS（單檔 index.html）、Python 3（僅 stdlib，schema 檢查腳本）、gh CLI、Claude Code cloud routine（schedule skill）。

## Global Constraints

- Repo：`cyc123456789/Claude-Catalog`（public），GitHub Pages 從 `main` branch 根目錄服務。
- Routine **只寫 `catalog.json`，絕不碰 `index.html`**。
- `category` 只允許：`plugin | skill | mcp | technique | official | tool`（六種）。
- `source` 只允許：`github | anthropic | community | blog`（四種）。
- `summary` 一律繁體中文一句話；日期格式一律 `YYYY-MM-DD`。
- `id` 去重鍵：GitHub repo 用 `gh:owner/repo`（小寫）；其他用去 query string / trailing slash 的正規化 URL。
- Routine 排程：每週二、五 UTC 20:00（cron `0 20 * * 2,5`），model `claude-sonnet-5`。
- 策展門檻：GitHub repo stars ≥ 50（Anthropic 官方除外）且 90 天內有 commit；每次每 category 最多新增 5 條。
- 告警鐵律：全部來源失敗 / check 失敗 / push 失敗 → 必推播告警；絕不靜默失敗。
- PAT 為使用者提供的秘密（fine-grained，僅 Claude-Catalog repo contents read/write），只放在 routine prompt，**不得寫入任何 repo 檔案**。文中 `<PAT>` 是等使用者提供的秘密，不是計畫佔位符。

---

### Task 1: Repo 資料層 — catalog.json 種子 + check.py 守門

**Files:**
- Create: `/home/charles/claude-catalog/catalog.json`
- Create: `/home/charles/claude-catalog/check.py`
- Create: `/home/charles/claude-catalog/README.md`

**Interfaces:**
- Consumes: 無（首個任務；repo `/home/charles/claude-catalog` 已 git init，含 docs/）
- Produces:
  - `catalog.json`：頂層 `{updated: str, entries: list}`，entry 欄位見下方種子檔（Task 2 的 index.html 與 Task 4 的 routine prompt 都依賴此 schema）
  - `check.py`：`python3 check.py [path]`，通過印出 `OK — N entries` 並 exit 0，違規則 AssertionError exit 非 0（Task 4 routine 在 commit 前執行它）

- [ ] **Step 1: 寫 catalog.json 種子資料（4 條真實條目）**

```json
{
  "updated": "2026-07-16",
  "entries": [
    {
      "id": "gh:anthropics/skills",
      "category": "skill",
      "title": "anthropics/skills",
      "url": "https://github.com/anthropics/skills",
      "summary": "Anthropic 官方 Agent Skills 收藏庫，含可直接安裝的文件處理等技能範例。",
      "source": "github",
      "tags": ["official", "agent-skills"],
      "stars": 1000,
      "added": "2026-07-16",
      "last_seen": "2026-07-16"
    },
    {
      "id": "gh:modelcontextprotocol/servers",
      "category": "mcp",
      "title": "modelcontextprotocol/servers",
      "url": "https://github.com/modelcontextprotocol/servers",
      "summary": "MCP 官方參考伺服器大全，接外部工具與資料源的第一站。",
      "source": "github",
      "tags": ["mcp", "reference"],
      "stars": 50000,
      "added": "2026-07-16",
      "last_seen": "2026-07-16"
    },
    {
      "id": "gh:hesreallyhim/awesome-claude-code",
      "category": "tool",
      "title": "awesome-claude-code",
      "url": "https://github.com/hesreallyhim/awesome-claude-code",
      "summary": "社群維護的 Claude Code 資源清單：slash commands、CLAUDE.md 範例與工作流。",
      "source": "github",
      "tags": ["awesome-list"],
      "stars": 5000,
      "added": "2026-07-16",
      "last_seen": "2026-07-16"
    },
    {
      "id": "https://www.anthropic.com/engineering/claude-code-best-practices",
      "category": "technique",
      "title": "Claude Code Best Practices",
      "url": "https://www.anthropic.com/engineering/claude-code-best-practices",
      "summary": "Anthropic 官方最佳實踐：CLAUDE.md、工具權限、TDD 工作流與多 agent 用法。",
      "source": "anthropic",
      "tags": ["best-practices", "workflow"],
      "added": "2026-07-16",
      "last_seen": "2026-07-16"
    }
  ]
}
```

（種子的 stars 是近似值，routine 首次執行 re-encounter 時會校正。）

- [ ] **Step 2: 寫 check.py（schema 守門，僅 stdlib）**

```python
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
```

- [ ] **Step 3: 執行 check.py 驗證種子資料**

Run: `cd /home/charles/claude-catalog && python3 check.py`
Expected: `OK — 4 entries`，exit 0

- [ ] **Step 4: 負向測試 — 確認守門真的會擋**

Run:
```bash
cd /home/charles/claude-catalog && python3 - <<'EOF'
import json, subprocess
d = json.load(open("catalog.json", encoding="utf-8"))
d["entries"][0]["category"] = "bogus"
json.dump(d, open("/tmp/claude-1000/-home-charles/652de2a3-fe29-4ecd-87f3-449dc193ad1a/scratchpad/bad.json", "w", encoding="utf-8"))
r = subprocess.run(["python3", "check.py", "/tmp/claude-1000/-home-charles/652de2a3-fe29-4ecd-87f3-449dc193ad1a/scratchpad/bad.json"])
assert r.returncode != 0, "check.py 沒擋下壞資料"
print("negative test OK")
EOF
```
Expected: check.py 對壞檔拋 AssertionError（stderr 有 traceback），最後印 `negative test OK`

- [ ] **Step 5: 寫 README.md**

```markdown
# Claude-Catalog

累積式 Claude 生態目錄：plugin / skill / MCP / 技巧 / 官方功能 / 周邊工具。

- 網站：https://cyc123456789.github.io/Claude-Catalog/
- 資料：`catalog.json`（cloud routine 每週二、五自動更新，只寫此檔）
- 版面：`index.html`（靜態，routine 不碰）
- 守門：`python3 check.py` — routine commit 前必跑

設計文件：`docs/superpowers/specs/2026-07-16-claude-catalog-design.md`
```

- [ ] **Step 6: Commit**

```bash
cd /home/charles/claude-catalog
git add catalog.json check.py README.md
git commit -m "feat: catalog seed data + schema guard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: 靜態前端 index.html

**Files:**
- Create: `/home/charles/claude-catalog/index.html`

**Interfaces:**
- Consumes: `catalog.json`（Task 1 的 schema：`{updated, entries:[{id, category, title, url, summary, source, tags, stars?, added, last_seen}]}`，與網頁同目錄）
- Produces: 無（終端交付物；routine 永不修改此檔）

- [ ] **Step 1: 寫 index.html（完整單檔，無 build）**

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Catalog</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #1a1a1a; --paper: #fafaf7; --muted: #6b6b6b; --line: #e2e0da;
    --c-plugin: #2563eb; --c-skill: #7c3aed; --c-mcp: #0d9488;
    --c-technique: #d97706; --c-official: #dc2626; --c-tool: #4b5563;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "IBM Plex Mono", monospace; font-size: 14px; line-height: 1.7;
  }
  header { max-width: 960px; margin: 0 auto; padding: 40px 20px 8px; }
  h1 { font-family: "Noto Serif TC", serif; font-size: 34px; margin: 0 0 4px; }
  .updated { color: var(--muted); font-size: 12px; }
  main { max-width: 960px; margin: 0 auto; padding: 0 20px 80px; }
  nav { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 12px; }
  nav a {
    text-decoration: none; color: var(--ink); border: 1px solid var(--line);
    padding: 4px 12px; font-size: 12px; background: #fff;
  }
  nav a.active { background: var(--ink); color: #fff; border-color: var(--ink); }
  #q {
    width: 100%; padding: 8px 12px; font: inherit; font-size: 13px;
    border: 1px solid var(--line); background: #fff; margin-bottom: 28px;
  }
  h2 {
    font-family: "Noto Serif TC", serif; font-size: 20px;
    margin: 36px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--line);
  }
  .card {
    background: #fff; border: 1px solid var(--line); border-left: 4px solid var(--muted);
    padding: 12px 16px; margin-bottom: 10px;
  }
  .card.plugin { border-left-color: var(--c-plugin); }
  .card.skill { border-left-color: var(--c-skill); }
  .card.mcp { border-left-color: var(--c-mcp); }
  .card.technique { border-left-color: var(--c-technique); }
  .card.official { border-left-color: var(--c-official); }
  .card.tool { border-left-color: var(--c-tool); }
  .card .top { display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; }
  .card a.title { color: var(--ink); font-weight: 500; text-decoration: none; }
  .card a.title:hover { text-decoration: underline; }
  .meta { color: var(--muted); font-size: 12px; }
  .summary { margin: 4px 0 6px; }
  .tag {
    display: inline-block; font-size: 11px; color: var(--muted);
    border: 1px solid var(--line); padding: 0 8px; margin-right: 6px; cursor: pointer;
  }
  .tag:hover { border-color: var(--ink); color: var(--ink); }
  .empty { color: var(--muted); }
</style>
</head>
<body>
<header>
  <h1>Claude Catalog</h1>
  <div class="updated" id="updated"></div>
</header>
<main>
  <nav id="nav"></nav>
  <input id="q" type="search" placeholder="搜尋 title / summary / tags…">
  <div id="content"></div>
</main>
<script>
const CATS = {
  plugin:    { label: "Plugin" },
  skill:     { label: "Skill" },
  mcp:       { label: "MCP" },
  technique: { label: "技巧" },
  official:  { label: "官方" },
  tool:      { label: "工具" },
};
let DATA = null;
let q = "";

const esc = s => String(s).replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const activeCat = () => {
  const h = location.hash.slice(1);
  return CATS[h] ? h : "all";
};

function matches(e) {
  if (!q) return true;
  const hay = [e.title, e.summary, ...(e.tags || [])].join(" ").toLowerCase();
  return hay.includes(q.toLowerCase());
}

function card(e) {
  const stars = e.stars != null ? `★ ${e.stars.toLocaleString()}` : "";
  const tags = (e.tags || [])
    .map(t => `<span class="tag" data-tag="${esc(t)}">${esc(t)}</span>`).join("");
  return `<div class="card ${esc(e.category)}">
    <div class="top">
      <a class="title" href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>
      <span class="meta">${esc(CATS[e.category].label)} · ${esc(e.source)}${stars ? " · " + stars : ""} · ${esc(e.added)}</span>
    </div>
    <div class="summary">${esc(e.summary)}</div>
    <div>${tags}</div>
  </div>`;
}

function section(title, entries) {
  if (!entries.length) return "";
  return `<h2>${esc(title)}</h2>` + entries.map(card).join("");
}

function render() {
  if (!DATA) return;
  const cat = activeCat();
  document.getElementById("updated").textContent = `最後更新 ${DATA.updated} · 共 ${DATA.entries.length} 條`;
  document.getElementById("nav").innerHTML =
    [`<a href="#" class="${cat === "all" ? "active" : ""}">全部</a>`]
      .concat(Object.entries(CATS).map(([k, v]) =>
        `<a href="#${k}" class="${cat === k ? "active" : ""}">${v.label}</a>`)).join("");

  const visible = DATA.entries.filter(e => (cat === "all" || e.category === cat) && matches(e));
  let html = "";
  if (cat === "all" && !q) {
    const dates = [...new Set(DATA.entries.map(e => e.added))].sort().reverse().slice(0, 2);
    html += section("最近新增", DATA.entries.filter(e => dates.includes(e.added))
      .sort((a, b) => b.added.localeCompare(a.added)));
  }
  const catsToShow = cat === "all" ? Object.keys(CATS) : [cat];
  for (const k of catsToShow) {
    html += section(CATS[k].label, visible.filter(e => e.category === k));
  }
  document.getElementById("content").innerHTML = html || `<p class="empty">沒有符合的條目。</p>`;
}

document.getElementById("q").addEventListener("input", e => { q = e.target.value; render(); });
document.getElementById("content").addEventListener("click", e => {
  const t = e.target.closest(".tag");
  if (!t) return;
  q = t.dataset.tag;
  document.getElementById("q").value = q;
  render();
});
window.addEventListener("hashchange", render);

fetch("catalog.json").then(r => r.json()).then(d => { DATA = d; render(); })
  .catch(() => { document.getElementById("content").innerHTML = `<p class="empty">catalog.json 載入失敗。</p>`; });
</script>
</body>
</html>
```

- [ ] **Step 2: 本機起 server 驗證**

Run:
```bash
cd /home/charles/claude-catalog && python3 -m http.server 8899 &
sleep 1
curl -s http://localhost:8899/ | grep -c "Claude Catalog"
curl -s http://localhost:8899/catalog.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['entries']), 'entries')"
```
Expected: 第一個 curl 輸出 ≥ 1（頁面含標題），第二個輸出 `4 entries`

- [ ] **Step 3: 瀏覽器實測渲染（agent-browser skill）**

用 agent-browser 開 `http://localhost:8899/`，驗證：
1. 「最近新增」區塊顯示 4 張卡片（同日種子，兩個 distinct 日期內）
2. 點 nav「MCP」→ hash 變 `#mcp`，只剩 modelcontextprotocol/servers
3. 搜尋框輸入 `workflow` → 只剩 Claude Code Best Practices
4. 點某張卡片上的 tag → 搜尋框帶入該 tag 且列表過濾
5. 截圖確認排版無跑版

驗證完 `kill %1` 收掉 http.server。

- [ ] **Step 4: Commit**

```bash
cd /home/charles/claude-catalog
git add index.html
git commit -m "feat: static catalog frontend (single-file, no build)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: GitHub repo + Pages 上線

**Files:**
- Modify: 無（純 gh CLI 操作，repo = `/home/charles/claude-catalog`）

**Interfaces:**
- Consumes: Task 1–2 的完整 local repo（main branch 上有 catalog.json、check.py、index.html、README、docs/）
- Produces: `https://github.com/cyc123456789/Claude-Catalog`（Task 4 routine 的 push 目標）與 `https://cyc123456789.github.io/Claude-Catalog/`

- [ ] **Step 1: 確認 gh 已登入正確帳號**

Run: `gh auth status`
Expected: 顯示已登入 `cyc123456789`。若未登入，請使用者在自己終端跑 `! gh auth login`。

- [ ] **Step 2: 建 repo 並推上去**

Run:
```bash
cd /home/charles/claude-catalog
git branch -M main
gh repo create Claude-Catalog --public --source . --push
```
Expected: 輸出 repo URL，`git push` 成功

- [ ] **Step 3: 啟用 GitHub Pages（main branch 根目錄）**

Run:
```bash
gh api -X POST repos/cyc123456789/Claude-Catalog/pages \
  -f "source[branch]=main" -f "source[path]=/"
```
Expected: HTTP 201，回傳含 `"status"` 的 JSON。（若回 409 表示已啟用，也算通過。）

- [ ] **Step 4: 等 Pages build 完成並驗證上線**

Run:
```bash
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w '%{http_code}' https://cyc123456789.github.io/Claude-Catalog/)
  [ "$code" = "200" ] && break; sleep 10
done
echo "HTTP $code"
curl -s https://cyc123456789.github.io/Claude-Catalog/catalog.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)['entries']), 'entries')"
```
Expected: `HTTP 200` 與 `4 entries`（首次 build 可能需 1–2 分鐘，迴圈最多等 2 分鐘）

---

### Task 4: Cloud routine 建立

**Files:**
- Modify: 無（用 schedule skill 建 cloud routine；prompt 內容如下）

**Interfaces:**
- Consumes: Task 3 的 GitHub repo；Task 1 的 `check.py` 與 catalog.json schema；使用者提供的 `<PAT>`
- Produces: cloud routine（cron `0 20 * * 2,5`，model `claude-sonnet-5`），每次執行更新 `catalog.json` 並推播

- [ ] **Step 1: 向使用者要 PAT（阻塞步驟，只能由使用者做）**

請使用者到 GitHub → Settings → Developer settings → Fine-grained tokens 建立 token：
- Repository access：只勾 `cyc123456789/Claude-Catalog`
- Permissions：Contents → Read and write
- 到期日自選（提醒：到期會導致 routine push 失敗，告警會抓到，届時要換 token —— 與 Daily-Digest/Stock 相同的已知風險）

取得後把 token 貼給執行者，替換下方 prompt 中的 `<PAT>`。**PAT 只放 routine prompt，不寫入任何檔案。**

- [ ] **Step 2: 用 schedule skill 建立 routine**

排程：cron `0 20 * * 2,5`（UTC；台北週二/五早上 4 點），model `claude-sonnet-5`，名稱 `claude-catalog-weekly`。routine prompt 全文（`<PAT>` 已替換）：

```
你是 Claude-Catalog（https://github.com/cyc123456789/Claude-Catalog）的維護 routine，每週二、五執行一次。目標：把新發現的 Claude 生態資源（plugin / skill / MCP / 技巧 / 官方功能 / 周邊工具）經策展篩選後併入 catalog.json。這是累積式目錄，不是週報——寧缺勿濫。

## 步驟

1. git clone https://x-access-token:<PAT>@github.com/cyc123456789/Claude-Catalog.git
   讀 catalog.json：現有 id 集合就是去重基準。

2. 四路蒐集候選。任一路失敗就跳過該路、繼續其他路，並在最後的推播中註明哪一路失敗：
   a. GitHub：搜尋近兩週新建立或有明顯動靜的 Claude 相關 repo（topic:claude-code、"claude code" plugin / skill / MCP 等關鍵字，用 gh api 或 curl api.github.com 的 search endpoint，無須認證），並檢查 awesome-claude-code 等清單有無新收錄項目。
   b. Anthropic 官方：Claude Code release notes / docs changelog、Anthropic engineering blog 與 news 的新文章（WebFetch）。新功能、新官方技巧收 category=official 或 technique。
   c. 社群：用 WebSearch 搜近一週 Reddit r/ClaudeAI、Hacker News、X 上的 Claude Code 技巧討論。不要直連 reddit/x（出網白名單會擋），一律 WebSearch。
   d. 技巧文：用 WebSearch 搜近兩週的 claude code tips / workflow / plugin 教學文章。

3. 策展門檻（硬規則，不符合就不收）：
   - GitHub repo：stars ≥ 50（Anthropic 官方出品除外）、90 天內有 commit、README 有實質內容。
   - 文章 / 貼文：要有可實際操作的內容；行銷文、純新聞、與既有條目重複的觀點不收。
   - 每個 category 本次最多新增 5 條。

4. 合併進 catalog.json（只改這個檔，絕不碰 index.html 或其他任何檔案）：
   - 新條目 append 進 entries；已存在（id 相同）的條目只更新 stars 與 last_seen，其他欄位不動。
   - id 規則：GitHub repo 用 gh:owner/repo（全小寫）；其他來源用正規化 URL（去掉 query string 與結尾斜線）。
   - 條目 schema（category 只能六選一，source 只能四選一，日期一律 YYYY-MM-DD）：
     {"id","category":"plugin|skill|mcp|technique|official|tool","title","url",
      "summary","source":"github|anthropic|community|blog","tags":[],
      "stars"(僅 github 來源),"added","last_seen"}
   - summary 一律繁體中文，一句話講清楚這東西幹嘛用、對誰有用。
   - 新條目 added = last_seen = 今天；頂層 updated 改為今天。

5. 執行 python3 check.py，通過才准 commit + push：
   git commit -m "catalog: add N entries (YYYY-MM-DD)"（N=0 時仍可只更新 last_seen/updated，message 用 "catalog: refresh (YYYY-MM-DD)"）

6. 推播通知（成功時）：「Claude Catalog 本期新增 N 條」+ 每條一行「[category] title」；若有來源失敗附註哪一路。完全沒有新條目時推播「本期無新增」，這是正常結果不是失敗。

## 告警鐵律（沿用 Daily-Digest / Stock 的規矩，絕不允許靜默失敗）
- 全部來源失敗、check.py 失敗、或 git push 失敗 → 必推播告警並說明原因。
- push 因 401/403 失敗極可能是 PAT 到期 → 告警中明確提醒使用者更換 token。
```

- [ ] **Step 3: 手動觸發一次驗證端到端**

用 schedule skill 手動 run 一次該 routine，確認：
1. routine 成功 clone、產出合規 catalog.json（check.py 通過）、push 成功
2. 收到「本期新增 N 條」推播
3. `curl -s https://cyc123456789.github.io/Claude-Catalog/catalog.json` 的 `updated` 變成執行日、entries 數 ≥ 4

- [ ] **Step 4: 收尾 commit（本機 repo 同步遠端）**

```bash
cd /home/charles/claude-catalog && git pull --rebase
```
Expected: 拉回 routine 產生的 commit（若 Step 3 有新增條目）

---

## Self-Review 紀錄

- Spec coverage：資料層（Task 1）、前端（Task 2）、repo+Pages（Task 3）、routine+排程+告警+PAT（Task 4）——spec 各節皆有對應任務；「明確不做」清單無任務，正確。
- Placeholder scan：`<PAT>` 為使用者提供的秘密，已在 Global Constraints 註明非佔位符；其餘無 TBD。
- Type consistency：check.py 的 CATEGORIES/SOURCES、index.html 的 CATS keys、routine prompt 的 schema 三處枚舉一致（六 category / 四 source）。
