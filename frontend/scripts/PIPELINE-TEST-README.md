# Storyboard Platform Pipeline Test

Automated Playwright script to run 10 test projects through the full pipeline (Script → Anchor → Grid) on the storyboard platform and capture grid screenshots.

## Setup

```bash
cd /Users/xingbo.huang/code/demo-idea/others/shenzhen-pixel-city
source ~/.nvm/nvm.sh
nvm use 18  # Playwright requires Node 18+
pnpm install  # if not done
npx playwright install chromium
```

## Usage

```bash
# Use default API keys (storyboard-admin-2024, admin2024, etc.)
node scripts/run-storyboard-pipeline.mjs

# Use custom API key (from Railway ADMIN_API_KEY)
STORYBOARD_API_KEY=your-actual-admin-key node scripts/run-storyboard-pipeline.mjs

# Run with visible browser (for debugging)
# Remove CI env or set CI=0
node scripts/run-storyboard-pipeline.mjs
```

## 10 Project Configurations

| # | L1 | L2 | Title | Duration |
|---|----|----|-------|----------|
| 1 | narrative | 追逐场景 | 城市午夜飙车 | 30s |
| 2 | narrative | 对话场景 | 咖啡馆的秘密 | 30s |
| 3 | narrative | 动作场景 | 街头格斗高手 | 30s |
| 4 | narrative | 悬疑惊悚 | 废弃医院深夜 | 30s |
| 5 | narrative | 浪漫情感 | 初雪告白瞬间 | 30s |
| 6 | commercial | 产品展示 | 新款手机发布会 | 15s |
| 7 | commercial | 食物饮品 | 精品咖啡拉花 | 15s |
| 8 | lifestyle | 旅行探索 | 云南古镇漫步 | 30s |
| 9 | music_perf | 音乐MV | 霓虹雨夜独奏 | 30s |
| 10 | special | 群戏多人 | 篮球队训练日 | 30s |

## Output

- Screenshots saved to: `../../pipeline-test-screenshots/` (relative to script)
- Full path: `/Users/xingbo.huang/code/demo-idea/pipeline-test-screenshots/`
- Summary printed to console: succeeded/failed counts and list

## Troubleshooting

**Login fails:** The production site at `web-production-01d28.up.railway.app` may use a different `ADMIN_API_KEY` than the defaults. Check your Railway project's environment variables and set `STORYBOARD_API_KEY` accordingly.

**Session lost after login:** If the script logs in but then sees the login form again when navigating to browse, the cookie may not persist. Try ensuring the API key is correct.
