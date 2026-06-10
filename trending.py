import os
import requests
import json
import xml.etree.ElementTree as ET

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

# 2. 从 GitHub 官方趋势 RSS 抓取数据
def get_github_trending():
    # 绕过镜像站，直接用 GitHub 官方的每日趋势 RSS 源
    url = "https://github-trends.ryct.ch/rss/github_trends_all_daily.rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            trending_list = []
            
            # 解析 RSS 中的前 10 个项目
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else "未知项目"
                link = item.find('link').text if item.find('link') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else "无描述"
                
                trending_list.append({
                    "name": title.strip(),
                    "url": link.strip(),
                    "description": desc.strip()
                })
            return trending_list
    except Exception as e:
        print(f"官方源抓取失败: {e}，正在尝试备用方式...")
        
    # 如果发生意外，用公共的非 SSL 稳定中转兜底
    try:
        res = requests.get("https://trendings.akass.cn/api/repo/daily", timeout=10).json()
        if "items" in res:
            return [{"name": i["repo"], "url": i["repo_link"], "description": i["desc"]} for i in res["items"][:10]]
    except Exception as e:
        print(f"所有抓取渠道均失效: {e}")
        
    return []

# 3. 给个人发送卡片消息
def send_to_personal(token, trending_list):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=mobile"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    elements = []
    for idx, repo in enumerate(trending_list):
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**{idx+1}. {repo['name']}**\n简介：{repo['description']}\n🔗 [项目链接]({repo['url']})",
                "tag": "lark_md"
            }
        })
        elements.append({"tag": "hr"})
        
    if elements:
        elements.pop()

    card_content = {
        "config": {"enable_forward": True},
        "header": {
            "title": {"content": "🔥 GitHub 每日热门项目（个人专属版）", "tag": "plain_text"},
            "template": "violet"
        },
        "elements": elements
    }

    payload = {
        "receive_id": os.environ.get("FEISHU_RECEIVER_MOBILE"), 
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    
    res = requests.post(url, headers=headers, json=payload).json()
    print("飞书发送结果:", res)

if __name__ == "__main__":
    token = get_tenant_access_token()
    if not token:
        exit(1)
        
    trending = get_github_trending()
    if trending:
        send_to_personal(token, trending)
    else:
        print("未获取到今日 Trending 数据")
