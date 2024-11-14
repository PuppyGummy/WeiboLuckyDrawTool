from flask import Flask, request, jsonify, render_template, redirect
import sinaweibopy3
import random
import os
import time
import json

app = Flask(__name__)

# Weibo App credentials
APP_KEY = '3782115072'
APP_SECRET = '61b979b2276797f389f5479ea18c1a61'
# REDIRECT_URL = 'https://api.weibo.com/oauth2/default.html'
REDIRECT_URL = 'https://weibo-lucky-draw-tool-82be7cb379f1.herokuapp.com/callback'

TOKEN_FILE = "token.json"

def save_token(token_data):
    with open(TOKEN_FILE, 'w') as file:
        json.dump(token_data, file)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as file:
            return json.load(file)
    return None

def is_token_expired(token_data):
    return time.time() > token_data['expires']

# Initialize the Weibo API client
client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)

# Step 1: Authorization Logic
# def auth():
#     try:
#         # Initialize Weibo API client and open the authorization URL
#         client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)
#         url = client.get_authorize_url()
#         webbrowser.open_new(url)

#         # Ask the user to input the authorization code from the URL
#         code = input("Please input the code from the URL: ")
#         result = client.request_access_token(code)
#         client.set_access_token(result.access_token, result.expires_in)
#         return client

#     except ValueError:
#         print('pyOauth2Error')

# # Initialize the Weibo client
# client = auth()

# Step 2: Define the route to render the HTML page
@app.route('/')
def home():
    # token_data = load_token()
    # if token_data and not is_token_expired(token_data):
    #     return render_template('index.html')

    auth_url = client.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed."

    # Request access token
    result = client.request_access_token(code)
    token_data = {
        'access_token': result.access_token,
        'expires': int(time.time()) + result.expires_in
    }
    save_token(token_data)
    client.set_access_token(result.access_token, result.expires_in)

    return render_template('index.html')

# Step 3: Define the route to handle repost timeline requests
@app.route('/fetch_reposts', methods=['GET'])
def fetch_reposts():
    try:
        weibo_url = request.args.get('weibo_url')
        count = int(request.args.get('count', 0))

        if not weibo_url or count <= 0:
            return jsonify({"error": "Invalid URL or count."})

        # Extract Weibo ID from URL
        weibo_id = weibo_url.split('/')[-1]

        # Fetch repost timeline data
        reposts = client.repost_timeline(weibo_id)
        users = [repost['user']['screen_name'] for repost in reposts]

        if len(users) == 0:
            return jsonify({"error": "No users found."})

        # Select random users
        selected_users = random.sample(users, min(count, len(users)))
        return jsonify({"users": selected_users})

    except Exception as e:
        return jsonify({"error": str(e)})

# Run the Flask app
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Host needs to be set to '0.0.0.0' for Heroku
    app.run(host='0.0.0.0', port=port, debug=False)