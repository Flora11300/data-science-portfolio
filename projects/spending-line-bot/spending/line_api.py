"""Small LINE HTTP adapter; credentials and token responses are never logged."""
import base64
import hashlib
import hmac
import time
import requests
from flask import current_app

class AuthenticationError(Exception): pass
class TransportError(Exception): pass

def verify_signature(body,signature,secret):
    if not isinstance(signature,str) or not signature or not signature.isascii() or not secret:return False
    expected=base64.b64encode(hmac.new(secret.encode(),body,hashlib.sha256).digest()).decode()
    return hmac.compare_digest(expected,signature)

def verify_id_token(token,channel_id):
    try:
        response=requests.post('https://api.line.me/oauth2/v2.1/verify',data={'id_token':token,'client_id':channel_id},timeout=8)
        if response.status_code!=200:raise AuthenticationError()
        data=response.json()
        if not isinstance(data,dict):raise AuthenticationError()
        subject=data.get('sub')
        expires=data.get('exp')
        if data.get('aud')!=channel_id or data.get('iss')!='https://access.line.me' or not isinstance(expires,(int,float)) or isinstance(expires,bool) or expires<=time.time() or not isinstance(subject,str) or not subject:
            raise AuthenticationError()
        return subject
    except (requests.RequestException,ValueError,TypeError) as exc:
        raise AuthenticationError() from exc

def reply_message(reply_token,text):
    try:
        response=requests.post('https://api.line.me/v2/bot/message/reply',headers={'Authorization':'Bearer '+current_app.config['LINE_CHANNEL_ACCESS_TOKEN']},json={'replyToken':reply_token,'messages':[{'type':'text','text':text[:4900]}]},timeout=8)
        if response.status_code!=200:raise TransportError()
    except requests.RequestException as exc:raise TransportError() from exc
