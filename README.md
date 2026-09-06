# karpathy-feed — RSS & A股 Digest

每日自动生成中文「技术雷达」+ A股行情摘要，推送到个人飞书。

## 这个项目做什么

1. **RSS 技术雷达**（每天 09:00）：抓取 39 个 RSS 源（Simon Willison / HN Best / Karpathy / 财新 / 36氪 等科技·财经·地缘），由 LLM 生成 600 字以内中文摘要（按分类 + 今日必读）。
2. **A股行情**（周一至五 11:30 早盘 / 15:00 收盘）：akshare 拉 5 大指数（上证/深成/创业板/沪深300/科创50），LLM 生成一句话市场概括。

推送渠道：**飞书**（News 应用，个人消息）。历史曾用 Slack，2026-09 账号已停用弃用。

## 当前架构（2026-09-06 迁移后）

```
调度: 7430byl (Dell 7430, 100.67.156.84) crontab（Asia/Shanghai）
  0 9  * * *   MODE=rss             → RSS 摘要
  30 11 * * 1-5 MODE=astock_morning → A股早盘
  0  15 * * 1-5 MODE=astock_afternoon → A股收盘
LLM:  ClawPA 集群（huangliang 的 new-api 网关，tailnet 100.86.225.99:3001/v1）
      模型 DeepSeekV4-Flash（推理模型，max_tokens≥4096 否则 content 为空）
数据: akshare（东方财富失败自动降级新浪源）
去重: seen_urls.json 本地持久化（7 天 TTL）
```

- **部署位置**：`/home/vagrant/karpathy-feed/`（venv + .env + crontab）
- **凭据**：`.env`（600 权限）——`LLM_API_KEY`（ClawPA neo-mac token）、`FEISHU_APP_SECRET`；权威副本在 Google Drive `credentials-vault/vault-source.md` + broker
- **日志**：`logs/{rss,astock_morning,astock_afternoon}.log`

## 手动运行

```bash
cd /home/vagrant/karpathy-feed
set -a && . ./.env && set +a
MODE=rss              ./venv/bin/python rss_digest.py   # RSS 摘要
MODE=astock_morning   ./venv/bin/python rss_digest.py   # A股早盘
MODE=astock_afternoon ./venv/bin/python rss_digest.py   # A股收盘
```

## 代码可配置项（环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `http://100.86.225.99:3001/v1` | OpenAI 兼容端点 |
| `LLM_API_KEY` | 空 | ClawPA token |
| `LLM_MODEL` | `DeepSeekV4-Flash` | 模型名 |
| `FEISHU_APP_ID` | `cli_a934f8ea79f8dcc6` | 飞书 News 应用 |
| `FEISHU_USER_ID` | `ou_73841a2902b303bd000cdc3011fd5c63` | 接收人 open_id |
| `SLACK_TOKEN` | 空 | 空则跳过（已弃用） |

## 历史

- 原架构：GitHub Actions 3 个 cron + DeepSeek 官方 API + Slack/飞书 + seen_urls.json 由 CI 提交回仓库
- 2026-09-06 迁移：DeepSeek 官方 key 全部删除（401）、Slack 停用（account_inactive）、ClawPA 仅 tailnet 可达 → LLM 切 ClawPA + 调度迁至 7430byl 本地 cron + 弃 Slack 只走飞书；GitHub workflow 已 disable
- 详见台账 PROJECT-LEDGER #91
