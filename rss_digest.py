import feedparser, requests, os, json, sys, time
from datetime import datetime, timezone, timedelta

SLACK_TOKEN = os.environ.get("SLACK_TOKEN", "")
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a934f8ea79f8dcc6")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID", "ou_73841a2902b303bd000cdc3011fd5c63")

SLACK_CHANNEL = "#tech-digest"

FEEDS = [
    # Tech
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    ("Paul Graham", "http://www.paulgraham.com/rss.html"),
    ("Dan Luu", "https://danluu.com/atom.xml"),
    ("Julia Evans", "https://jvns.ca/atom.xml"),
    ("Hacker News Best", "https://hnrss.org/best"),
    ("Karpathy Blog", "https://karpathy.bearblog.dev/feed/"),
    ("Anthropic", "https://www.anthropic.com/blog/feed.xml"),
    ("Gwern", "https://gwern.net/feed/site.xml"),
    ("Jeff Geerling", "https://www.jeffgeerling.com/blog.xml"),
    ("Daring Fireball", "https://daringfireball.net/feeds/main"),
    ("antirez", "http://antirez.com/rss"),
    ("Xe Iaso", "https://xeiaso.net/blog.rss"),
    ("lcamtuf", "https://lcamtuf.substack.com/feed/"),
    ("Mitchell Hashimoto", "https://mitchellh.com/feed.xml"),
    ("Rachel Kroll", "https://rachelbebay.com/w/atom.xml"),
    ("Cory Doctorow", "https://pluralistic.net/feed/"),
    ("Ken Shirriff", "https://www.righto.com/feeds/posts/default"),
    ("Raymond Chen", "https://devblogs.microsoft.com/oldnewthing/feed/"),
    ("Dynomight", "https://dynomight.net/feed/"),
    ("Dan Abramov", "https://overreacted.io/rss.xml"),
    ("John D. Cook", "https://www.johndcook.com/blog/feed/"),
    ("Hillel Wayne", "https://buttondown.com/hillelwayne/rss"),
    ("Brian Krebs", "https://krebsonsecurity.com/feed/"),
    ("Eli Bendersky", "https://eli.thegreenplace.net/feeds/all.atom.xml"),
    ("Fabien Sanglard", "https://fabiensanglard.net/rss.xml"),
    ("Bert Hubert", "https://berthug.eu/articles/index.xml"),
    ("Troy Hunt", "https://feeds.troyhunt.com/TroyHunt"),
    # Economics & Investment
    ("Marginal Revolution", "https://marginalrevolution.com/feed"),
    ("Noah Smith", "https://noahpinion.substack.com/feed"),
    ("Abnormal Returns", "https://abnormalreturns.com/feed/"),
    ("Morgan Housel", "https://collabfund.com/blog/rss/"),
    ("Barry Ritholtz", "https://ritholtz.com/feed/"),
    ("Econbrowser", "https://econbrowser.com/feed"),
    ("VoxEU", "https://cepr.org/vox/vox.rss"),
    # Politics & Geopolitics
    ("Gary Marcus", "https://garymarcus.substack.com/feed/"),
    ("Matt Stoller", "https://www.thebignewsletter.com/feed/"),
    ("Construction Physics", "https://www.construction-physics.com/feed/"),
    # 中文财经
    ("财新网", "https://www.caixin.com/rss20.xml"),
    ("36氪", "https://36kr.com/feed"),
]

SEEN_URLS_FILE = "seen_urls.json"
SEEN_URLS_TTL_DAYS = 7


def load_seen_urls():
    if not os.path.exists(SEEN_URLS_FILE):
        return {}
    with open(SEEN_URLS_FILE) as f:
        return json.load(f)


def save_seen_urls(seen):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_URLS_TTL_DAYS)).isoformat()
    pruned = {url: ts for url, ts in seen.items() if ts > cutoff}
    with open(SEEN_URLS_FILE, "w") as f:
        json.dump(pruned, f, ensure_ascii=False, indent=2)


def get_recent_articles(hours=24):
    seen = load_seen_urls()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = []
    now_ts = datetime.now(timezone.utc).isoformat()
    for name, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if not pub:
                    continue
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt <= cutoff:
                    continue
                link = entry.get("link", "")
                if link and link in seen:
                    print(f"[跳过重复] {name}: {entry.get('title', '')}")
                    continue
                articles.append({
                    "source": name,
                    "title": entry.get("title", "无标题"),
                    "link": link,
                })
                if link:
                    seen[link] = now_ts
        except Exception as e:
            print(f"Error: {name}: {e}")
    save_seen_urls(seen)
    return articles


def call_deepseek(prompt, max_tokens, timeout):
    """调用 DeepSeek API：3 次自动重试 + 错误判断。成功返回文本，失败返回 None。"""
    for attempt in range(1, 4):
        try:
            r = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                timeout=timeout,
            )
            if r.status_code != 200:
                print(f"[DeepSeek] 第{attempt}次尝试 HTTP {r.status_code}: {r.text[:200]}")
            else:
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if content:
                    return content
                print(f"[DeepSeek] 第{attempt}次尝试响应无 choices/content: {r.text[:200]}")
        except Exception as e:
            print(f"[DeepSeek] 第{attempt}次尝试异常: {e}")
        if attempt < 3:
            time.sleep(2 * attempt)
    print("[DeepSeek] 3 次重试均失败")
    return None


def generate_digest(articles):
    if not articles:
        return "今日暂无新文章"
    article_list = "\n".join([f"- [{a['source']}] {a['title']} {a['link']}" for a in articles])
    prompt = (
        "你是 Andrej Karpathy 风格的技术信息策展人。信噪比优先。\n\n"
        f"今天的新文章：\n{article_list}\n\n"
        "请整理成每日技术雷达，按分类列出，每条附一句洞见，最后给出今日必读。600字以内，中文。"
    )
    result = call_deepseek(prompt, max_tokens=800, timeout=30)
    if not result:
        return "⚠️ 今日摘要生成失败（DeepSeek API 异常），以下为原文列表供参考：\n\n" + article_list
    return result


# ── A股行情 ────────────────────────────────────────────────────────────────────

ASTOCK_INDICES = [
    ("上证指数", "000001"),
    ("深证成指", "399001"),
    ("创业板指", "399006"),
    ("沪深300",  "000300"),
    ("科创50",   "000688"),
]


def get_astock_data():
    import akshare as ak
    try:
        df = ak.stock_zh_index_spot_em()
    except Exception as e:
        print(f"[AStock] akshare 拉取失败: {e}")
        return []

    results = []
    for name, code in ASTOCK_INDICES:
        row = df[df["代码"] == code]
        if row.empty:
            row = df[df["名称"].str.contains(name, na=False)]
        if row.empty:
            continue
        r = row.iloc[0]
        try:
            pct = float(r["涨跌幅"])
            arrow = "▲" if pct >= 0 else "▼"
            results.append({
                "name":   r["名称"],
                "price":  r["最新价"],
                "pct":    f"{arrow}{abs(pct):.2f}%",
                "change": r["涨跌额"],
                "amount": r["成交额"],
            })
        except Exception:
            continue
    return results


def generate_astock_digest(indices, session_label):
    if not indices:
        return f"📊 A股{session_label}行情数据获取失败"

    lines = "\n".join(
        [f"{i['name']}  {i['price']}  {i['pct']}  成交额{i['amount']:.0f}亿" for i in indices]
    )
    prompt = (
        f"以下是今日A股{session_label}主要指数数据：\n{lines}\n\n"
        "请用100字以内中文做一句话市场概括，点出今日最关键的走势特征，语气客观简洁。"
    )
    comment = call_deepseek(prompt, max_tokens=150, timeout=20)
    if not comment:
        comment = "（市场概括生成失败，DeepSeek API 异常）"
    else:
        comment = comment.strip()

    header = f"📊 A股{session_label}行情\n{'─'*28}\n"
    body = "\n".join([f"{i['name']}  {i['price']}  {i['pct']}" for i in indices])
    return f"{header}{body}\n\n💬 {comment}"


# ── 推送 ───────────────────────────────────────────────────────────────────────

def send_to_slack(message):
    if not SLACK_TOKEN:
        print("[Slack] 未配置 SLACK_TOKEN，跳过")
        return
    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        json={"channel": SLACK_CHANNEL, "text": message},
        timeout=15,
    )
    print(f"[Slack] {'成功' if r.json().get('ok') else '失败: ' + r.text}")


def get_feishu_token():
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10,
    )
    return r.json().get("tenant_access_token", "")


def send_to_feishu(message):
    if not FEISHU_APP_SECRET:
        print("[Feishu] 未配置 FEISHU_APP_SECRET，跳过")
        return
    token = get_feishu_token()
    if not token:
        print("[Feishu] 获取 token 失败")
        return
    r = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": FEISHU_USER_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message}),  # 正确转义，避免引号/换行破坏 JSON
        },
        timeout=15,
    )
    print(f"[Feishu] {'成功' if r.status_code == 200 else '失败: ' + r.text}")


# ── 入口 ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = os.environ.get("MODE", "rss")

    if mode == "astock_morning":
        print("=== A股早盘收盘行情 ===")
        indices = get_astock_data()
        digest = generate_astock_digest(indices, "早盘收盘（11:30）")
        print(digest)
        send_to_feishu(digest)
        send_to_slack(digest)

    elif mode == "astock_afternoon":
        print("=== A股全天收盘行情 ===")
        indices = get_astock_data()
        digest = generate_astock_digest(indices, "收盘（15:00）")
        print(digest)
        send_to_feishu(digest)
        send_to_slack(digest)

    else:
        print("=== 每日技术 RSS 摘要 ===")
        articles = get_recent_articles(hours=24)
        print(f"找到 {len(articles)} 篇新文章")
        if not articles:
            print("无新文章，跳过推送")
        else:
            digest = generate_digest(articles)
            print(digest)
            send_to_slack(digest)
            send_to_feishu(digest)

    print("完成！")
