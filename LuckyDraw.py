from flask import Flask, request, jsonify, render_template, redirect
import sinaweibopy3
import random
import os
import time
import json
import logging

app = Flask(__name__)

# logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Weibo App credentials
APP_KEY = '3782115072'
APP_SECRET = '61b979b2276797f389f5479ea18c1a61'
REDIRECT_URL = 'https://luckydrawtool.online/callback'

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
        logger.error(f"Error saving token: {str(e)}")

def load_token():
    """Load the token data from a JSON file"""
    try:
        with open('token_data.json', 'r') as f:
            token_data = json.load(f)
        logger.info("Token loaded from JSON file")
        if 'expires' in token_data:
            token_data['expires'] = float(token_data['expires'])
        return token_data
    except FileNotFoundError:
        logger.warning("No token file found")
        return None
    except Exception as e:
        logger.error(f"Error loading token from JSON file: {str(e)}")
        return None

def is_token_expired(token_data):
    """Check if the token has expired"""
    if not token_data:
        return True
    
    expiration_time = float(token_data.get('expires', 0))
    current_time = time.time()
    is_expired = current_time > expiration_time
    
    logger.info(f"Token expiration check:")
    logger.info(f"  - Current time: {current_time}")
    logger.info(f"  - Expiration time: {expiration_time}")
    logger.info(f"  - Is expired: {is_expired}")
    
    return is_expired

# Initialize the Weibo API client
client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)

@app.before_request
def before_request():
    if request.headers.get('X-Forwarded-Proto') == 'https':
        request.url = request.url.replace('http://', 'https://')

@app.route('/')
def home():
    try:
        if load_token() and not is_token_expired(load_token()):
            return render_template('index.html', server_url = 'https://' + request.host)
        else:
            auth_url = client.get_authorize_url()
            logger.info(f"Generated auth URL: {auth_url}")
            return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}", exc_info=True)
        return f"Error generating authorization URL: {str(e)}", 500

@app.route('/callback')
def callback():
    try:
        logger.info(f"Callback received - Full URL: {request.url}")
        code = request.args.get('code')
        logger.info(f"Received authorization code: {code}")
        
        if not code:
            logger.error("No authorization code received")
            return "Authorization failed - no code received.", 400

        # Request access token
        try:
            result = client.request_access_token(code)
            logger.info("Access token request successful")
            logger.info(f"Token result type: {type(result)}")
            logger.info(f"Token expires_in type: {type(result.expires_in)}")
            logger.info(f"Token expires_in value: {result.expires_in}")
        except Exception as token_error:
            logger.error(f"Error requesting access token: {str(token_error)}", exc_info=True)
            return f"Error requesting access token: {str(token_error)}", 500

        # Calculate expiration time
        expires_in = int(result.expires_in)
        expiration_time = time.time() + expires_in
        
        
        # Save token data
        token_data = {
            'access_token': result.access_token,
            'expires': expiration_time
        }
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
        logger.error(f"Unexpected error in callback: {str(e)}", exc_info=True)
        return f"Authorization failed: {str(e)}", 500

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
        # Remove any spaces
        weibo_id = weibo_id.replace(' ', '')
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
        if 'error_code' in reposts:
            logger.error(f"Error fetching reposts: {reposts['error']}")
            return jsonify({"error": reposts['error']})
        logger.info(f"Received {len(reposts) if reposts else 0} reposts")
        
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
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)