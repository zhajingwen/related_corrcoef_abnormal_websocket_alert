import requests
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Lark Alert')

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒
REQUEST_TIMEOUT = 10  # 秒

def sender(msg, url=None, title='', del_blank_row=True):
    """
    # 文本格式化官方文档
    https://open.larksuite.com/document/ukTMukTMukTM/uMDMxEjLzATMx4yMwETM?lang=zh-CN
    # 关于加粗：用Card中的Fields来实现
    加粗（文档最底部）：https://open.larksuite.com/document/common-capabilities/message-card/message-cards-content/content-module
    https://open.larksuite.com/document/common-capabilities/message-card/message-cards-content/card-structure
    https://open.larksuite.com/document/common-capabilities/message-card/message-cards-content/using-markdown-tags
    加粗：（文档最底部）：https://open.larksuite.com/document/common-capabilities/message-card/message-cards-content/embedded-non-interactive-elements/field
    :param url: webhook地址
    :param msg: 需要发送的消息
    """
    if not url:
        # 从环境变量读取默认的 webhook ID
        default_webhook_id = os.getenv('LARKBOT_ID')
        if not default_webhook_id:
            logger.error("未提供 url 且环境变量 LARKBOT_ID 未设置")
            return None
        url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{default_webhook_id}'
    msg_list = []
    for i in msg.strip().split('\n'):
        i = i.strip()
        if del_blank_row:
            if not i:
                continue
        if i:
            i_list = i.split(' ')
            msg_row = []
            for i_word in i_list:
                if '&url&' in i_word:
                    href =  i_word.split('&url&')[-1].strip()
                    link_name = i_word.split('&url&')[0].strip()
                    item_json = {
                        "tag": "a",
                        "href": href,
                        "text": link_name
                    }
                else:
                    item_json = {
                        "tag": "text",
                        "text": i_word + ' '
                    }
                msg_row.append(item_json)
        else:
            msg_row = [{"tag": "text","text": "\n"}]
        msg_list.append(msg_row)

    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": msg_list
                }
            }
        }
    }
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(url, headers=headers, data=json.dumps(data), timeout=REQUEST_TIMEOUT)
            
            # 检查 HTTP 状态码
            if res.status_code == 200:
                logger.info(f'lark 告警调用成功：{res.text}')
                return res.text
            else:
                logger.warning(f'lark 告警返回错误状态码: {res.status_code}, 响应: {res.text}')
        except requests.exceptions.RequestException as e:
            logger.warning(f'lark 告警网络错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}')
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    logger.error(f'lark 告警调用失败，已重试 {MAX_RETRIES} 次')
    return None

def sender_colourful(url, content, title=''):
    """
    https://open.larksuite.com/document/common-capabilities/message-card/message-cards-content/using-markdown-tags
    """
    message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": "red"
            },
            "elements": [{
                "tag": "markdown",
                "content": content,
            }]
        }
    }
    headers = {
        'Content-Type': 'application/json'
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(message), timeout=REQUEST_TIMEOUT)
            
            # 检查 HTTP 状态码
            if response.status_code == 200:
                logger.info(f'lark 彩色告警调用成功：{response.text}')
                return response.text
            else:
                logger.warning(f'lark 彩色告警返回错误状态码: {response.status_code}, 响应: {response.text}')
        except requests.exceptions.RequestException as e:
            logger.warning(f'lark 彩色告警网络错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}')
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    logger.error(f'lark 彩色告警调用失败，已重试 {MAX_RETRIES} 次')
    return None