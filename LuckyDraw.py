from flask import Flask, request, jsonify
from flask_cors import CORS
import sinaweibopy3
import random
import os
import time
import json
import logging

app = Flask(__name__)
# CORS(app, resources={
#     r"/*": {
#         "origins": ["https://puppygummy.github.io"],
#         "methods": ["GET", "POST", "OPTIONS"],
#         "allow_headers": ["Content-Type"]
#     }
# })

# logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Weibo App credentials
APP_KEY = '3782115072'
APP_SECRET = '61b979b2276797f389f5479ea18c1a61'
REDIRECT_URL = 'https://puppygummy.github.io/WeiboLuckyDrawTool'

def save_token(token_data):
    """Use the token data to save the token to a JSON file"""
    try:
        # Convert the token data to a JSON string
        token_str = json.dumps(token_data)
        
        # Save the token data to a file
        with open('token_data.json', 'w') as f:
            json.dump(token_data, f)
        logger.info("Token saved to JSON file")
    except Exception as e:
        logger.error(f"Error saving token to environment: {str(e)}")

def load_token():
    """Load the token data from a JSON file"""
    try:
        token_str = os.environ.get('WEIBO_TOKEN')
        if token_str:
            token_data = json.loads(token_str)
            # 确保expires是数值类型
            if isinstance(token_data.get('expires'), str):
                token_data['expires'] = float(token_data['expires'])
            logger.info(f"Token loaded from environment variable: {token_data}")
            return token_data
        logger.warning("No token found in environment variables")
        return None
    except Exception as e:
        logger.error(f"Error loading token from environment: {str(e)}")
        return None

def is_token_expired(token_data):
    """Check if the token has expired"""
    if not token_data:
        return True
    
    try:
        expiration_time = float(token_data.get('expires', 0))
        current_time = time.time()
        is_expired = current_time > expiration_time
        
        logger.info(f"Token expiration check: current={current_time}, expires={expiration_time}, expired={is_expired}")
        
        return is_expired
    except (ValueError, TypeError) as e:
        logger.error(f"Error checking token expiration: {str(e)}")
        return True

# Initialize the Weibo API client
client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)

@app.route('/get_auth_url', methods=['GET', 'OPTIONS'])
def get_auth_url():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        auth_url = client.get_authorize_url()
        return jsonify({"auth_url": auth_url})
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/process_auth_code', methods=['POST', 'OPTIONS'])
def process_auth_code():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        code = data.get('code')
        logger.info(f"Received authorization code: {code}")

        if not code:
            return jsonify({"error": "No authorization code received"}), 400

        # Request access token
        try:
            result = client.request_access_token(code)
            client.set_access_token(result.access_token, result.expires_in)
        except Exception as token_error:
            logger.error(f"Error requesting access token: {str(token_error)}", exc_info=True)
            return jsonify({"error": "Failed to request access token"}), 500

        # Calculate expiration time
        expires_in = int(result.expires_in)
        expiration_time = time.time() + expires_in
        
        
        # Save token data
        token_data = {
            "access_token": result.access_token,
            "expires": expiration_time
        }
        save_token(token_data)

        client.set_access_token(result.access_token, expires_in)
        logger.info(f"Access token set: {result.access_token}, expires in {expires_in} seconds")
        
        logger.info(f"Token data prepared: {token_data}")
        
        # Set access token in client
        try:
            client.set_access_token(result.access_token, expires_in)
            logger.info("Access token set in client successfully")
        except Exception as set_token_error:
            logger.error(f"Error setting access token: {str(set_token_error)}")
            return f"Error setting access token: {str(set_token_error)}", 500

        # Save token data to file
        try:
            save_token(token_data)
        except Exception as save_error:
            logger.error(f"Error saving token: {str(save_error)}")

        return render_template('index.html', server_url = 'https://' + request.host)
    
    except Exception as e:
        logger.error(f"Error in process_auth_code: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/fetch_reposts', methods=['GET', 'OPTIONS'])
def fetch_reposts():
    if request.method == 'OPTIONS':
        return '', 204
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

        # Check for token
        token_data = load_token()
        if token_data:
            if not is_token_expired(token_data):
                logger.info("Valid token found, setting in client")
                client.set_access_token(token_data['access_token'], int(token_data['expires'] - time.time()))
            else:
                logger.error("Token expired")
                return jsonify({"error": "Token expired."}), 401
        else:
            logger.error("Token not found")
            return jsonify({"error": "Token not found."}), 401

        # Fetch reposts
        logger.info("Fetching repost timeline")
        reposts = client.repost_timeline(weibo_id)
        users = [repost['user']['screen_name'] for repost in reposts]

        if len(users) == 0:
            logger.warning("No users found in reposts")
            return jsonify({"error": "No users found."})

        # Randomly select users
        selected_users = random.sample(users, min(count, len(users)))
        logger.info(f"Selected {len(selected_users)} users randomly")
        
        return jsonify({"users": selected_users})

    except Exception as e:
        logger.error(f"Error in fetch_reposts: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, ssl_context='adhoc')