from flask import Flask, request, jsonify
import sinaweibopy3
import random
import os
import time
import json
import logging

app = Flask(__name__)

# 设置日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Weibo App credentials
APP_KEY = '3782115072'
APP_SECRET = '61b979b2276797f389f5479ea18c1a61'
REDIRECT_URL = 'https://puppygummy.github.io/WeiboLuckyDrawTool'  # 修改为前端根路径

def save_token(token_data):
    """使用环境变量存储令牌信息"""
    try:
        token_str = json.dumps(token_data)
        os.environ['WEIBO_TOKEN'] = token_str
        logger.info("Token saved to environment variable")
    except Exception as e:
        logger.error(f"Error saving token to environment: {str(e)}")

def load_token():
    """从环境变量加载令牌信息"""
    try:
        token_str = os.environ.get('WEIBO_TOKEN')
        if token_str:
            token_data = json.loads(token_str)
            logger.info("Token loaded from environment variable")
            return token_data
        logger.warning("No token found in environment variables")
        return None
    except Exception as e:
        logger.error(f"Error loading token from environment: {str(e)}")
        return None

def is_token_expired(token_data):
    """检查令牌是否过期"""
    if not token_data:
        return True
    
    expiration_time = float(token_data.get('expires', 0))
    current_time = time.time()
    is_expired = current_time > expiration_time
    
    logger.info(f"Token expiration check: current={current_time}, expires={expiration_time}, expired={is_expired}")
    
    return is_expired

# Initialize the Weibo API client
client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)

@app.route('/get_auth_url', methods=['GET'])
def get_auth_url():
    try:
        auth_url = client.get_authorize_url()
        return jsonify({"auth_url": auth_url})
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/process_auth_code', methods=['POST'])
def process_auth_code():
    try:
        data = request.json
        code = data.get('code')
        logger.info(f"Received authorization code: {code}")

        if not code:
            return jsonify({"error": "No authorization code received"}), 400

        try:
            result = client.request_access_token(code)
            client.set_access_token(result.access_token, result.expires_in)
        except Exception as token_error:
            logger.error(f"Error requesting access token: {str(token_error)}", exc_info=True)
            return jsonify({"error": "Failed to request access token"}), 500

        expires_in = int(result.expires_in)
        expiration_time = time.time() + expires_in

        token_data = {
            "access_token": result.access_token,
            "expires": expiration_time
        }
        save_token(token_data)

        return jsonify(token_data)

    except Exception as e:
        logger.error(f"Error in process_auth_code: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/fetch_reposts', methods=['GET'])
def fetch_reposts():
    try:
        logger.info("Fetch reposts request received")
        weibo_url = request.args.get('weibo_url')
        count = int(request.args.get('count', 0))
        
        logger.info(f"Parameters received - URL: {weibo_url}, Count: {count}")

        if not weibo_url or count <= 0:
            logger.error("Invalid parameters provided")
            return jsonify({"error": "Invalid URL or count."})

        # Extract Weibo ID from URL
        weibo_id = weibo_url.split('/')[-1]
        logger.info(f"Extracted Weibo ID: {weibo_id}")

        # 检查令牌状态
        token_data = load_token()
        if not token_data or is_token_expired(token_data):
            return jsonify({"error": "Access token is missing or expired"}), 401
        
        client.set_access_token(token_data['access_token'], token_data['expires'])
        
        # 调用微博API获取转发列表
        reposts = client.get.repost_timeline(id=weibo_id, count=count)
        users = [repost.user.screen_name for repost in reposts]
        
        # 随机选择用户
        selected_users = random.sample(users, min(count, len(users)))
        logger.info(f"Selected {len(selected_users)} users randomly")
        
        return jsonify({"users": selected_users})

    except Exception as e:
        logger.error(f"Error in fetch_reposts: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)