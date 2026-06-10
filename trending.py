import os
import requests
import json

# 1. 获取飞书调用 Token
def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": os.environ.get("FEISHU_APP_ID"),
        "app_secret": os.environ.get("FEISHU_APP_SECRET")
    }
    res = requests.post(url, json=payload).json()
    return res.get("tenant_access_token")

# 2. 抓取 GitHub Trending 数据
def get_github_trending():
    url = "https://api.gitter.xyz/trending" 
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()[:10]  # 取前 10 个项目
    except Exception as e:
        print(f"抓取失败: {e}")
    return []

# 3. 给个人发送卡片消息
def send_to_personal(token, trending_list):
    # 使用手机号作为接收者类型
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=mobile"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 构造卡片内容
    elements = []
    for idx, repo in enumerate(trending_list):
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**{idx+1}. {repo['name']}** (⭐ {repo['stars']})\n简介：{repo.get('description', '无描述')}\n🔗 [项目链接]({repo['url']})",
                "tag": "lark_md"
            }
        })
        elements.append({"tag": "hr"})
        
    if elements:
        elements.pop()  # 移除最后一个分割线

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
        print("获取飞书 Token 失败，请检查 APP_ID 和 APP_SECRET")
        exit(1)
        
    trending = get_github_trending()
    if trending:
        send_to_personal(token, trending)
    else:
        print("未获取到今日 Trending 数据")
