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

# 2. 通过手机号获取用户的 user_id
def get_user_id_by_mobile(token, mobile):
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=user_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "mobiles": [mobile]
    }
    try:
        res = requests.post(url, headers=headers, json=payload).json()
        user_list = res.get("data", {}).get("user_list", [])
        if user_list and "user_id" in user_list[0]:
            return user_list[0]["user_id"]
        else:
            print(f"手机号查询失败，飞书返回: {res}")
            return None
    except Exception as e:
        print(f"请求查询 user_id 接口出错: {e}")
        return None

# 3. 直接解析 GitHub 官方 Trending 网页
def get_github_trending():
    url = "https://github.com/trending"
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
            desc = desc_match.group(1).strip() if desc_match else "无描述"
            desc = re.sub(r'<[^>]+>', '', desc).replace('\n', '').strip()
            
            stars_match = re.search(r'href="/[^"]+/stargazers"[\s\S]*?>([\s\S]*?)</a>', article)
            stars = stars_match.group(1).strip().replace(',', '') if stars_match else "0"
            
            trending_list.append({
                "name": repo_path,
                "url": repo_url,
                "description": desc,
                "stars": stars
            })
        return trending_list
    except Exception as e:
        print(f"直接抓取官方源失败: {e}")
    return []

# 4. 给个人发送卡片消息
def send_to_personal(token, user_id, trending_list):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    elements = []
    for idx, repo in enumerate(trending_list):
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**{idx+1}. {repo['name']}** (⭐ {repo['stars']})\n简介：{repo['description']}\n🔗 [项目链接]({repo['url']})",
                "tag": "lark_md"
            }
        })
        elements.append({"tag": "hr"})
        
    if elements:
        elements.pop()

    card_content = {
        "config": {"enable_forward": True},
        "header": {
            "title": {"content": "🔥 GitHub 每日热门项目（官方直连版）", "tag": "plain_text"},
            "template": "violet"
        },
        "elements": elements
    }

    payload = {
        "receive_id": user_id, 
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    
    res = requests.post(url, headers=headers, json=payload).json()
    print("飞书发送结果:", res)

if __name__ == "__main__":
    token = get_tenant_access_token()
    if not token:
        exit(1)
        
    mobile = os.environ.get("FEISHU_RECEIVER_MOBILE")
    user_id = get_user_id_by_mobile(token, mobile)
    
    if not user_id:
        print("未能获取到有效的飞书 User ID，请检查应用权限或手机号设置。")
        exit(1)
        
    trending = get_github_trending()
    if trending:
        send_to_personal(token, user_id, trending)
    else:
        print("未获取到今日 Trending 数据")
