import feedparser, requests, os
  from datetime import datetime, timezone, timedelta

  SLACK_TOKEN = os.environ["SLACK_TOKEN"]
  DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
  SLACK_CHANNEL = "#tech-digest"

  FEEDS = [
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
      ("Gary Marcus", "https://garymarcus.substack.com/feed/"),
      ("Matt Stoller", "https://www.thebignewsletter.com/feed/"),
      ("Construction Physics", "https://www.construction-physics.com/feed/"),
      ("Eli Bendersky", "https://eli.thegreenplace.net/feeds/all.atom.xml"),
      ("Fabien Sanglard", "https://fabiensanglard.net/rss.xml"),
      ("Bert Hubert", "https://berthub.eu/articles/index.xml"),
      ("Troy Hunt", "https://feeds.troyhunt.com/TroyHunt"),
  ]

  def get_recent_articles(hours=24):
      cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
      articles = []
      for name, url in FEEDS:
          try:
              feed = feedparser.parse(url)
              for entry in feed.entries[:3]:
                  pub = entry.get("published_parsed") or entry.get("updated_parsed")
                  if pub:
                      pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                      if pub_dt > cutoff:
                          articles.append({
                              "source": name,
                              "title": entry.get("title", "无标题"),
                              "link": entry.get("link", ""),
                          })
          except Exception as e:
              print(f"Error: {name}: {e}")
      return articles

  def generate_digest(articles):
      if not articles:
          return "今日暂无新文章"
      article_list = "\n".join([f"- [{a['source']}] {a['title']} {a['link']}" for a in
  articles])
      prompt = f"你是 Andrej Karpathy
  风格的技术信息策展人。信噪比优先。\n\n今天的新文章：\n{article_list}\n\n请整理成每日技
  术雷达，按分类列出，每条附一句洞见，最后给出今日必读。600字以内，中文。"
      r = requests.post(
          "https://api.deepseek.com/chat/completions",
          headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":
  "application/json"},
          json={"model": "deepseek-chat", "messages": [{"role": "user", "content":
  prompt}], "max_tokens": 800}
      )
      return r.json()["choices"][0]["message"]["content"]

  def send_to_slack(message):
      requests.post(
          "https://slack.com/api/chat.postMessage",
          headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
          json={"channel": SLACK_CHANNEL, "text": message}
      )

  if __name__ == "__main__":
      articles = get_recent_articles(hours=24)
      print(f"找到 {len(articles)} 篇新文章")
      digest = generate_digest(articles)
      print(digest)
      send_to_slack(digest)
      print("已发送到 Slack！")
