# Claude-Catalog 設計文件

日期：2026-07-16
狀態：已與使用者確認設計，待撰寫實作計畫

## 目的

一個累積式的 Claude 生態目錄網站（GitHub Pages）：cloud routine 每週兩次自動蒐集 Claude 相關的 plugin、skill、MCP server、技巧文、官方新功能與周邊工具，經策展門檻篩選後併入持續成長的總目錄。重點是「Claude 生態的完整地圖」，不是週報。

## 架構

沿用使用者既有的「JSON 資料 / 版面分離」模式（同 Daily-Digest、Stock）：

- 新 GitHub repo `Claude-Catalog`（cyc123456789 帳號）+ GitHub Pages。
- Cloud routine：每週二、五 UTC 20:00（台北 04:00），model claude-sonnet-5。
- routine **只寫 `catalog.json`，不碰 `index.html`**。版面固定在靜態 index.html，一次寫好。

## 資料層

單一 `catalog.json`（不分檔、無 manifest）。策展門檻下條目年增約一兩百條，單檔可撐多年；哪天檔案大到影響載入再拆。

### Schema

```json
{
  "updated": "2026-07-16",
  "entries": [{
    "id": "gh:owner/repo 或正規化 URL",
    "category": "plugin | skill | mcp | technique | official | tool",
    "title": "...",
    "url": "...",
    "summary": "一句繁中講清楚這東西幹嘛用",
    "source": "github | anthropic | community | blog",
    "tags": ["..."],
    "stars": 123,
    "added": "2026-07-16",
    "last_seen": "2026-07-16"
  }]
}
```

- `id` 為去重鍵：GitHub repo 用 `gh:owner/repo`（小寫），其他來源用正規化 URL（去 query string / trailing slash）。
- `stars` 僅 GitHub 來源有，其他來源省略該欄位。
- `summary` 一律繁體中文，一句話說明用途與價值。
- 條目只增不刪；re-encounter 時僅更新 `stars` 與 `last_seen`。

## Routine 流程

1. 讀取現有 `catalog.json` 作為去重基準。
2. 四路來源蒐集候選：
   - **GitHub**：搜尋 `topic:claude-code`、`topic:claude` 相關新 repo，以及 awesome-claude-code 類清單的新增項目。
   - **Anthropic 官方**：docs changelog、blog、release notes（WebFetch）。
   - **社群**：Reddit r/ClaudeAI、Hacker News、X 上的技巧討論（用 WebSearch，不直連 —— 雲端出網白名單擋得住的來源一律以 WebSearch 降級）。
   - **技巧文**：WebSearch 掃「claude code tips / workflow / plugin」類新文章。
3. 策展門檻（寬鬆收錄會讓目錄爛掉，這是硬規則）：
   - GitHub repo：stars ≥ 50（Anthropic 官方出品除外），且 90 天內有 commit，README 有實質內容。
   - 技巧文／社群貼文：要有可實際操作的內容，行銷文、純新聞不收。
   - **每次執行每個 category 最多新增 5 條**。
4. 合併新條目 + 更新 re-encounter 條目 → 寫回 `catalog.json` → commit + push（fine-grained PAT 放 routine prompt，沿用既有做法）。
5. 推播「本期新增 N 條」摘要通知。

## 錯誤處理

- 任一來源失敗：跳過該來源、照常處理其餘來源，並在推播中註明哪路來源失敗。
- 全部來源失敗、或 git push 失敗：**必推播告警**（沿用兩個既有 routine 的失敗必告警鐵律；2026-07-10/11 曾靜默失敗過才立的規矩）。
- 沒有任何新條目：屬正常結果，推播「本期無新增」，不視為失敗。
- PAT 到期會導致 push 失敗 → 告警會抓到，提醒使用者換 token（已知既有風險模式）。

## 前端（靜態 index.html，一次寫好）

- 單頁應用，純前端、無 build step，直接 fetch `catalog.json`。
- 頂部「最近新增」區：按 `added` 倒序取最新一批（例如最近兩次執行的新增）。
- 下方完整目錄：六個 category 分區。
- hash 路由切換分類（`#plugin`、`#skill`…）+ tag 篩選 + 純前端文字搜尋（title/summary/tags）。
- 風格延續使用者的簡報文件風：Noto Serif TC 標題 + IBM Plex Mono、每分類一條色脊。
- GitHub 條目顯示 stars；`last_seen` 距今過久的條目先不做視覺標記（見下）。

## 明確不做（YAGNI）

- 死專案自動清理／stale 標記（`last_seen` 欄位留著，之後要做再做）。
- 英文版介面、RSS、sitemap。
- 多檔拆分、manifest。
- 後端、資料庫、build pipeline。

## 交付物

1. `Claude-Catalog` GitHub repo：`index.html` + 初始 `catalog.json`（可由首次手動執行填種子資料）+ GitHub Pages 設定。
2. Cloud routine（每週二、五 UTC 20:00）與其 prompt：含來源清單、策展門檻、schema、告警規則、PAT。
