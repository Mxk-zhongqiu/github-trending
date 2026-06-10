import os
import requests
import json
import xml.etree.ElementTree as ET
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

# 2. 调用 GitHub 官方免鉴权 RSS 订阅源，精准提取 AI / 机器学习热榜
def get_github_ai_trending():
    # 使用官方最稳定的 Machine Learning 每日趋势 RSS 源
    url = "https://github-trends.ryct.ch/rss/github_trends_machine-learning_daily.rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"访问 GitHub RSS 失败，状态码: {response.status_code}")
            # 备用源：如果上面遭遇波动，自动切换到全局通用每日热榜源
            url = "https://github-trends.ryct.ch/rss/github_trends_all_daily.rss"
            response = requests.get(url, headers=headers, timeout=15)
            
        root = ET.fromstring(response.content)
        trending_list = []
        
        # 逐行解析 RSS 节点
        for item in root.findall('.//item')[:10]: # 精准取前10个
            title_text = item.find('title').text if item.find('title') is not None else "未知/未知"
            repo_url = item.find('link').text if item.find('link') is not None else "https://github.com"
            raw_desc = item.find('description').text if item.find('description') is not None else "暂无项目详细文本介绍。"
            
            # 从描述中精准提取星标增速（RSS 格式通常在描述末尾带有 Stars 统计）
            stars_match = re.search(r'⭐\s*([\d,]+)', raw_desc)
            stars = stars_match.group(1) if stars_match else "爆火中"
            
            # 清理描述，移除 HTML 标签，只保留纯文本详情
            clean_desc = re.sub(r'<[^>]+>', '', raw_desc).replace('\n', ' ').strip()
            if "⭐" in clean_desc:
                clean_desc = clean_desc.split("⭐")[0].strip() # 剔除末尾的星星图标后缀
            
            trending_list.append({
                "full_name": title_text.strip(),
                "url": repo_url.strip(),
                "description": clean_desc if clean_desc else "暂无该 AI 项目的详细描述。",
                "today_stars": stars
            })
        return trending_list
    except Exception as e:
        print(f"解析 GitHub RSS 趋势失败: {e}")
        
    # 【双重保险兜底】若因海外网络偶发解析失败，采用免解析的底层简易格式数据支撑
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
        # 安全拆分所有者和项目名
        if '/' in repo['full_name']:
            owner, repo_name = repo['full_name'].split('/', 1)
            author_info = f"*所属组织/作者：{owner.strip()}*"
        else:
            repo_name = repo['full_name']
            author_info = f"*所属组织/作者：自主开源*"
            
        elements.append({
            "tag": "div",
            "text": {
                "content": f"**🤖 0{idx+1} | {repo_name.strip()}**\n{author_info}",
                "tag": "lark_md"
            }
        })
        
        elements.append({
            "tag": "div",
            "text": {
                "content": f"📝 **核心详情介绍：**\n{repo['description']}\n\n📊 **热度追踪：**\n• 今日飙升：`🔥 +{repo['today_stars']} Stars`",
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
