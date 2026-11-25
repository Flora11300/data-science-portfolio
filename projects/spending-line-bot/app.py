"""Run locally: DEMO_MODE=1 python app.py. Production: gunicorn 'app:create_app()'."""
import os
from urllib.parse import urlparse
from flask import Flask
from spending.store import Store
from spending.routes import bp

def create_app(config=None):
    app=Flask(__name__)
    app.config.from_mapping(DEMO_MODE=os.getenv('DEMO_MODE','0')=='1',DATABASE=os.getenv('DATABASE','instance/spending.sqlite3'),LINE_CHANNEL_SECRET=os.getenv('LINE_CHANNEL_SECRET',''),LINE_CHANNEL_ACCESS_TOKEN=os.getenv('LINE_CHANNEL_ACCESS_TOKEN',''),LINE_LOGIN_CHANNEL_ID=os.getenv('LINE_LOGIN_CHANNEL_ID',''),LIFF_ID=os.getenv('LIFF_ID',''),PUBLIC_ORIGIN=os.getenv('PUBLIC_ORIGIN',''),MAX_CONTENT_LENGTH=1024*1024)
    if config:app.config.update(config)
    if not app.config['DEMO_MODE']:
        for key in ('LINE_CHANNEL_SECRET','LINE_CHANNEL_ACCESS_TOKEN','LINE_LOGIN_CHANNEL_ID','LIFF_ID','PUBLIC_ORIGIN'):
            if not app.config[key]:raise RuntimeError(f'Missing required configuration: {key}. Use DEMO_MODE=1 for a local demonstration.')
    if not app.config['DEMO_MODE']:
        origin=urlparse(app.config['PUBLIC_ORIGIN'])
        if origin.scheme!='https' or not origin.netloc or origin.path or origin.query or origin.fragment or origin.username:
            raise RuntimeError('PUBLIC_ORIGIN must be an HTTPS origin without a path or trailing slash')
    app.extensions['store']=Store(app.config['DATABASE'])
    app.register_blueprint(bp)
    return app

if __name__=='__main__':
    create_app().run(host='127.0.0.1',port=int(os.getenv('PORT','5050')),debug=False)
