# -*- coding: utf-8 -*-

import urllib.request
import urllib.parse
import json
import logging
import time

# general json object that can bind any fields but also act as a dict.
#a json class inhert dict class which can use d['key'] or d.key to get
class JsonDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value



#convert json object to python object.
def _obj_hook(paris):
    odict = JsonDict()
    for key, value in paris.items():
        odict[str(key)] = value
    return odict



#Encode parameters
def _encode_params(**kw):
    args = []
    for key, value in kw.items():
        para = value.encode('utf-8') if isinstance(value, str) else str(value)
        args.append('%s=%s' % (key, urllib.parse.quote(para)))
    return '&'.join(args)



#Build a multipart/form-data body with generated random boundary.
def _encode_multipart(**kw):
    #'encode mulyipart data'
    boundary = '----------%s' % hex(int(time.time() * 1000))
    data = []
    for key, value in kw.items():
        data.append('--%s' % boundary)
        if hasattr(value, 'read'):
            filename = getattr(value, 'name', '')
            name = filename.rfind('.')
            ext = filename[name:].lower() if name != (-1) else ""
            content = value.read()
            content = content.decode('ISO-8859-1')
            data.append('Content-Disposition: form-data; name="%s"; filename="hidden"' % key)
            data.append('Content-Length: %d' % len(content))
            data.append('Content-Type: %s\r\n' % _guess_content_type(ext))
            data.append(content)
        else:
            data.append('Content-Disposition: form-data; name="%s"\r\n' % key)
            data.append(value if isinstance(value, str) else value.decode('utf-8'))
    data.append('--%s--\r\n' % boundary)
    return '\r\n'.join(data), boundary




_CONTENT_TYPES = {'.png': 'image/png', '.gif': 'image/gif', '.jpg': 'image/jpeg',
                  '.jpeg': 'image/jpeg', '.jpe': 'image/jpeg'}



def _guess_content_type(ext):
    return _CONTENT_TYPES.get(ext, 'application/octet-stream')





_HTTP_GET = 0
_HTTP_POST = 1
_HTTP_UPLOAD = 2

def _http_get(url, authorization=None, **kw):
    logging.info('GET %s' % url)
    return _http_request(url, _HTTP_GET, authorization, **kw)

def _http_post(url, authorization=None, **kw):
    logging.info('POST %s' % url)
    return _http_request(url, _HTTP_POST, authorization, **kw)

def _http_upload(url, authorization=None, **kw):
    logging.info('UPLOAD %s' % url)
    return _http_request(url, _HTTP_UPLOAD, authorization, **kw)



#send an http request and expect to return a json object if no error.
def _http_request(url, method, authorization, **kw):
    params = None
    boundary = None
    if method == _HTTP_UPLOAD:
        params, boundary = _encode_multipart(**kw)
    else:
        params = _encode_params(**kw)

    http_url = f'{url}?{params}' if method == _HTTP_GET else url
    http_para = None if method == _HTTP_GET else params.encode(encoding='utf-8')

    logging.debug(f"Request URL: {http_url}")
    logging.debug(f"Request Params: {params}")

    req = urllib.request.Request(http_url, data=http_para)
    if authorization:
        req.add_header('Authorization', f'OAuth2 {authorization}')
    if boundary:
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

    resq = urllib.request.urlopen(req)
    body = resq.read().decode("utf-8")
    result = json.loads(body, object_hook=_obj_hook)
    
    logging.debug(f"Response: {result}")
    
    return result




class HttpObject(object):
    'post get or updload object'
    def __init__(self, client, method):
        self.client = client
        self.method = method

    def __getattr__(self, attr):
        def wrap(**kw):
            'request param'
            if self.client.is_expires():
                raise AttributeError
            return _http_request('%s%s.json' % (self.client.api_url, attr.replace('__', '/')),self.method, self.client.access_token, **kw)
        return wrap


#APIClient class
class APIClient(object):
    def __init__(self, app_key, app_secret, redirect_uri=None,response_type='code', domain='api.weibo.com', version='2'):
        self.client_id = app_key
        self.client_secret = app_secret
        self.redirect_uri = redirect_uri
        self.response_type = response_type
        self.auth_url = 'https://%s/oauth2/' % domain
        self.api_url = 'https://%s/%s/' % (domain, version)
        self.access_token = None
        self.expires = 0.0
        self.get = HttpObject(self, _HTTP_GET)
        self.post = HttpObject(self, _HTTP_POST)
        self.upload = HttpObject(self, _HTTP_UPLOAD)

    #get authorize url
    def get_authorize_url(self):
        return "https://api.weibo.com/oauth2/authorize?response_type=code&client_id=%s&redirect_uri=%s"%(self.client_id, self.redirect_uri)

    #post a request and then get a access_token
    def request_access_token(self, code):
        result = _http_post('%s%s' % (self.auth_url, 'access_token'), 
                          client_id=self.client_id, 
                          client_secret=self.client_secret, 
                          redirect_uri=self.redirect_uri, 
                          code=code, grant_type='authorization_code')
        result.expires_in += int(time.time())
        return result

    
    #set access_token and expires_in
    def set_access_token(self, access_token, expires_in):
        self.access_token = str(access_token)
        self.expires = float(expires_in)

    #Determine if the access token expires
    def is_expires(self):
        return not self.access_token or time.time() > self.expires

    #Custom function:Used to get the latest public Weibo
    def user_timeline(self):
        result = _http_get('%s'% (self.api_url)  + 'statuses/user_timeline.json', 
                           access_token=self.access_token, 
                           count=50, 
                           page=1, 
                           base_app=0, 
                )
        return result
    def repost_timeline(self, weibo_id):
        if self.access_token is None:
            raise Exception("Access token is required to fetch reposts")
        all_reposts = []  # List to store all reposts
        page = 1
        count_per_page = 50  # Number of reposts per page
        while True:
            # Fetch reposts for the current page
            result = _http_get(
                f'{self.api_url}statuses/repost_timeline.json',
                access_token=self.access_token,
                id=weibo_id,
                count=count_per_page,
                page=page
            )
            
            # Check if there are reposts in the current result
            if not result or 'reposts' not in result or len(result['reposts']) == 0:
                break
            
            # Append reposts to the all_reposts list
            all_reposts.extend(result['reposts'])
            
            # Increment the page number for the next request
            page += 1

            # Optional: Add a small delay to avoid hitting API rate limits
            time.sleep(0.5)
        
        return all_reposts