import webbrowser
import sinaweibopy3
import random


# Get Authorization
def auth():
    try:
        # step 1 : sign a app in weibo and then define const app key,app srcret,redirect_url
        APP_KEY = '3782115072'
        APP_SECRET = '61b979b2276797f389f5479ea18c1a61'
        REDIRECT_URL = 'https://api.weibo.com/oauth2/default.html'
        # step 2 : get authorize url and code
        client = sinaweibopy3.APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=REDIRECT_URL)
        url = client.get_authorize_url()
        webbrowser.open_new(url)
        # step 3 : get Access Token
        # Copy the above address to the browser to run, 
        #enter the account and password to authorize, the new URL contains code
        result = client.request_access_token(
            input("please input code : "))  # Enter the CODE obtained in the authorized address
        
        print(result)
        client.set_access_token(result.access_token, result.expires_in)

        return client

    except ValueError:
        print('pyOauth2Error')

def select_users(users, count):
    return random.sample(users, count)

if __name__ == '__main__':
    client = auth()
    # weibo_id = input("Please input the weibo id: ")
    weibo_url = input("Please input the weibo url: ")
    weibo_id = weibo_url.split('/')[-1]
    data = client.repost_timeline(weibo_id)
    users = [repost['user']['screen_name'] for repost in data]
    if len(users) == 0:
        print("No users to select")
        exit()
    print("users count: ", len(users))
    select_num = input("Please input the number of users you want to select: ")
    select_users = select_users(users, int(select_num))
    print("Selected users: ", select_users)