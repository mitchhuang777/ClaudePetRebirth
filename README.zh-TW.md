# ClaudePetRebirth

> English version: [README.md](README.md)

重新抽取你的 Claude Code 寵物，直到遇見命中注定的那一隻。

靈感來源：[any-buddy](https://github.com/cpaczek/any-buddy)

---

## 這是什麼？

Claude Code 會根據你的帳號 ID 決定寵物，正常情況下無法更改。**ClaudePetRebirth** 讓你在終端機中重新抽取隨機寵物，收藏喜歡的，並**直接套用到 Claude Code**（透過暴力搜尋匹配的 salt）。

---

## 功能特色

- **18 種物種** — 鴨子、鵝、果凍、貓、龍、章魚、貓頭鷹、企鵝、烏龜、蝸牛、幽靈、六角恐龍、水豚、仙人掌、機器人、兔子、蘑菇、胖胖
- **5 種稀有度** — 普通 (60%)、非凡 (25%)、稀有 (10%)、史詩 (4%)、傳說 (1%)
- **6 種眼睛** — `·` `✦` `×` `◉` `@` `°`
- **7 種帽子** — 皇冠、高帽、螺旋槳、光環、巫師帽、毛帽、小鴨（非凡以上才有）
- **5 項屬性** — 除錯力、耐心、混沌、智慧、嘴砲
- **閃光寵物** — 每次 1% 機率
- **收藏系統** — 收藏、比較、套用寵物
- **自選模式** — 指定物種、稀有度、眼睛、帽子、最強屬性
- **高速平行搜尋** — 持久 bun 進程 + 多核心，約 500k–1M+ hashes/秒
- **自動偵測工作數** — 根據 CPU 核心數自動調整，電腦越好搜尋越快
- **中/英雙語介面**

---

## 系統需求

- Python 3.8+
- [Bun](https://bun.sh)（用於 wyhash，需在 PATH 中）

**必須安裝 Bun。** Claude Code 內部使用 `Bun.hash`（wyhash）來生成寵物，Python 沒有原生的等效實作。工具會啟動一個持久的 Bun 子進程來複現完全相同的雜湊值——沒有 Bun 的話搜尋功能完全無法運作。

**安裝 Bun：**

```bash
# Linux / macOS / WSL
curl -fsSL https://bun.sh/install | bash

# Windows (PowerShell)
powershell -c "irm bun.sh/install.ps1 | iex"
```

---

## 使用方式

```bash
cd ClaudePetRebirth
python main.py
```

---

## 操作說明

| 按鍵 | 功能 |
|---|---|
| `Enter` | 重新抽取新的隨機寵物 |
| `k` | 收藏當前寵物 |
| `f` | 查看收藏 / 套用到 Claude Code |
| `d` | 移除最後一個收藏 |
| `a` | 開關動畫預覽 |
| `p` | 自選模式 |
| `l` | 切換中/英語言 |
| `h` | 顯示說明 |
| `q` | 離開 |

---

## 套用寵物流程

從收藏列表（`f`）選擇號碼 → 確認後工具會：

1. 從 `~/.claude.json` 讀取 `oauthAccount.accountUuid`
2. 自動偵測 CPU 核心數，啟動對應數量的平行工作進程
3. 暴力搜尋一個 15 字元 salt，使 `hash(userId + salt)` 骰出你選的寵物
4. 顯示實際會在 `/buddy` 出現的**屬性數值**，確認後再套用
5. 原地修補 Claude Code binary（自動備份）
6. 將 salt 存至 `~/.claude-code-any-buddy.json`
7. 更新 `~/.claude.json` 中的 `companion.name` / `companion.personality`

修補後重啟 Claude Code，執行 `/buddy` 即可看到新寵物。

---

## 自選模式 (`p`)

指定物種 → 稀有度 → 眼睛 → 帽子 → 閃光 → 最強/最弱屬性（選填）。搜尋成功後，套用前會先顯示 `/buddy` 實際會出現的屬性數值。按 `Enter` 重搜不同屬性，或按 `p` 新增最強/最弱條件。

---

## 搜尋速度

工具使用持久 Bun 子進程 + Python 多進程。每次搜尋前會自動偵測並顯示工作進程數。

| 硬體 | 大約速度 |
|---|---|
| 2 核心 | ~200k hashes/秒 |
| 4 核心 | ~400k hashes/秒 |
| 8 核心 | ~800k hashes/秒 |
| 16 核心 | ~1.5M hashes/秒 |

---

## 匹配難度說明

每多指定一個條件，預期搜尋次數就會倍增。

| 目標 | 機率 | 預估次數 |
|---|---|---|
| 任意寵物 | — | 1 |
| 普通 + 物種 + 眼睛 | 1/180 | ~180 |
| 稀有 + 物種 + 眼睛 + 帽子 | 1/6,480 | ~6,480 |
| 傳說 + 物種 + 眼睛 + 帽子 | 1/75,600 | ~75,600 |
| 傳說 + 物種 + 眼睛 + 帽子 + 最強/最弱屬性 | 1/1,512,000 | ~150 萬 |
| 任意 + 閃光 | ×100 | ×100 |

以 1M hashes/秒 計算，即使是最難的組合也只需幾分鐘。

> **注意：** 屬性不可能全部是 100。PRNG 設計上一定會產生一個最強與一個最弱屬性，傳說稀有度的最弱屬性最高也只到約 54。

---

## 專案結構

| 檔案 | 用途 |
|---|---|
| `main.py` | 主迴圈 |
| `lang.py` | 雙語字串表 + `t()` helper |
| `ui.py` | 顯示與渲染函式 |
| `apply.py` | `apply_pet()` — 搜尋 salt 並修補 binary |
| `pick.py` | `custom_pick()` — 自選模式 |
| `save.py` | 收藏存取 |
| `patcher.py` | 核心搜尋與修補引擎、bun hash |
| `generation.py` | 隨機骰寵物（Mulberry32 PRNG） |
| `sprites.py` | ASCII 點陣圖資料與渲染 |
| `constants.py` | 物種、稀有度、眼睛、帽子、屬性、個性常數 |

---

## 稀有度

| 稀有度 | 星等 | 機率 | 屬性下限 |
|---|---|---|---|
| 普通 (Common) | ★ | 60% | 5 |
| 非凡 (Uncommon) | ★★ | 25% | 15 |
| 稀有 (Rare) | ★★★ | 10% | 25 |
| 史詩 (Epic) | ★★★★ | 4% | 35 |
| 傳說 (Legendary) | ★★★★★ | 1% | 50 |

---

## License

MIT
