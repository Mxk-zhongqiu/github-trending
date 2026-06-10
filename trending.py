import os
import requests
import json
import re

# 1. 获取飞书调用 Token
def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": os.environ.get("FEISHU_APP_ID"),
        "app_secret": os.environ.get("FEISHU_APP_SECRET")
    }
    try:
        res = requests.post(url, json=payload).json()
        return res.get("tenant_access_token")
    except Exception as e:
        print(f"获取飞书 Token 失败: {e}")
        return None

# 2. 直接解析 GitHub 官方 AI 专项 Trending 网页
def get_github_ai_trending():
    url = "https://github.com/trending?spoken_language_code=&topics%5B%5D=artificial-intelligence"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"访问 GitHub 官方失败，状态码: {response.status_code}")
            return []
            
        html = response.text
        articles = re.findall(r'<article class="Box-row">([\s\S]*?)</article>', html)
        
        trending_list = []
        for article in articles[:10]:  
            repo_match = re.search(r'href="([^"]+)"', article)
            if not repo_match:
                continue
            repo_path = repo_match.group(1).strip('/')
            repo_url = f"https://github.com/{repo_path}"
            
            desc_match = re.search(r'<p class="col-9 color-fg-muted my-1 pr-4">([\s\S]*?)</p>', article)
            desc = desc_match.group(1).strip() if desc_match else "暂无该 AI 项目的详细文本描述。"
            desc = re.sub(r'<[^>]+>', '', desc).replace('\n', ' ').strip()
            desc = " ".join(desc.split())
            
            stars_match = re.search(r'href="/[^"]+/stargazers"[\s\S]*?>([\s\S]*?)</a>', article)
            stars = stars_match.group(1).strip().replace(',', '') if stars_match else "0"
            
            today_stars_match = re.search(r'([\d,]+)\s+stars\s+(?:today|this\s+week)', article)
            today_stars = today_stars_match.group(1).strip() if today_stars_match else "爆火中"
            
            trending_list.append({
                "name": repo_path,
                "url": repo_url,
                "description": desc,
                "stars": stars,
                "today_stars": today_stars
            })
        return trending_list
    except Exception as e:
        print(f"抓取 GitHub AI 趋势失败: {e}")
    return []

# 3. 构造深度排版的飞书富文本卡片
def send_to_personal_by_email(token, email, trending_list):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=email"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    elements = []
    for idx, repo in enumerate(trending_list):
        # 【核心修复点】安全拆分所有者和项目名，防止无 '/' 的字符串导致 ValueError
        if '/' in repo['name']:
            owner, repo_name = repo['name'].split('/', 1)
            author_info = f"*所属组织/作者：{owner}*"
        else:
            repo_name = repo['name']
            author_info = "*所属组织/作者：未知*"
        
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**🤖 0{idx+1} | {repo_name}**\n{author_info}",
                "tag": "lark_md"
            }
        })
        
        elements.append({
            "tag": "div",
            "text": {
                "content": f"📝 **核心详情介绍：**\n{repo['description']}\n\n📊 **热度追踪：**\n• 累计总星标：`⭐ {repo['stars']}`\n• 今日飙升：`🔥 +{repo['today_stars']}`",
                "tag": "lark_md"
            }
        })
        
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"content": "查看源码仓库 🔗", "tag": "plain_text"},
                    "type": "primary",
                    "url": repo['url']
                },
                {
                    "tag": "button",
                    "text": {"content": "看 Issues 💬", "tag": "plain_text"},
                    "type": "default",
                    "url": f"{repo['url']}/issues"
                }
            ]
        })
        elements.append({"tag": "hr"})
        
    if elements:
        elements.pop()

    card_content = {
        "config": {"enable_forward": True},
        "header": {
            "title": {"content": "🌟 GitHub Daily AI Trending (Top 10)", "tag": "plain_text"},
            "template": "carmine"  
        },
        "elements": elements
    }

    payload = {
        "receive_id": email, 
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    
    res = requests.post(url, headers=headers, json=payload).json()
    print("飞书发送结果:", res)

if __name__ == "__main__":
    token = get_tenant_access_token()
    if not token:
        exit(1)
        
    email = os.environ.get("FEISHU_RECEIVER_EMAIL")
    if not email:
        print("未配置 FEISHU_RECEIVER_EMAIL 环境变量")
        exit(1)
        
    trending = get_github_ai_trending()
    if trending:
        send_to_personal_by_email(token, email, trending)
    else:
        print("未获取到今日 AI Trending 数据")
