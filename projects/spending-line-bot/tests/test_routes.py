import base64,hashlib,hmac,json,time
from unittest.mock import Mock
import pytest
from app import create_app
from spending import line_api

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DEMO_MODE':False,'DATABASE':str(tmp_path/'db.sqlite3'),'LINE_CHANNEL_SECRET':'test-secret','LINE_CHANNEL_ACCESS_TOKEN':'test-access','LINE_LOGIN_CHANNEL_ID':'123','LIFF_ID':'123-demo','PUBLIC_ORIGIN':'https://spending.example'})

@pytest.fixture
def client(app):return app.test_client()

def headers(user='alice'):return {'Authorization':'Bearer '+user}

def payload(**changes):
    p=dict(category='food',date='2026-11-25',amount='12.30',note='Lunch',request_id='request-0001');p.update(changes);return p

def test_auth_and_user_isolation(client,monkeypatch):
    monkeypatch.setattr(line_api,'verify_id_token',lambda token,channel: token)
    assert client.get('/api/expenses').status_code==401
    assert client.post('/api/expenses',json=payload(),headers=headers()).status_code==201
    assert client.post('/api/expenses',json=payload(),headers=headers()).status_code==200
    assert client.get('/api/expenses',headers=headers('bob')).json['records']==[]
    assert len(client.get('/api/expenses',headers=headers()).json['records'])==1
    assert client.get('/api/summary?month=2026-11',headers=headers()).json['total_cents']==1230
    assert client.post('/api/expenses',json=payload(amount='22'),headers=headers()).status_code==409

@pytest.mark.parametrize('body',[None,[],{'amount':'x'},payload(request_id='x'),payload(amount='0'),payload(category=['food'])])
def test_invalid_json_fields(client,monkeypatch,body):
    monkeypatch.setattr(line_api,'verify_id_token',lambda token,channel: token)
    assert client.post('/api/expenses',json=body,headers=headers()).status_code in (400,415)

def test_token_failure(client,monkeypatch):
    monkeypatch.setattr(line_api,'verify_id_token',Mock(side_effect=line_api.AuthenticationError()))
    assert client.get('/api/expenses',headers=headers()).status_code==401

def signed(client,body):
    data=json.dumps(body,ensure_ascii=False).encode()
    sig=base64.b64encode(hmac.new(b'test-secret',data,hashlib.sha256).digest()).decode()
    return client.post('/callback',data=data,headers={'X-Line-Signature':sig,'Content-Type':'application/json'})

def event():return {'webhookEventId':'event-001','type':'message','replyToken':'reply-test','source':{'type':'user','userId':'alice'},'message':{'type':'text','text':'分析'}}

def test_signature_rejects_modified_body(client):
    assert client.post('/callback',json={'events':[]}).status_code==400
    assert signed(client,{'events':[]}).status_code==200
    assert signed(client,{'events':'wrong'}).status_code==400
    assert signed(client,[]).status_code==400

def test_duplicate_event_and_retry(client,monkeypatch):
    reply=Mock(side_effect=[line_api.TransportError(),None])
    monkeypatch.setattr(line_api,'reply_message',reply)
    assert signed(client,{'events':[event()]}).status_code==503
    assert signed(client,{'events':[event()]}).status_code==200
    assert signed(client,{'events':[event()]}).status_code==200
    assert reply.call_count==2

def test_private_events_only(client,monkeypatch):
    reply=Mock();monkeypatch.setattr(line_api,'reply_message',reply)
    e=event();e['source']['type']='group'
    assert signed(client,{'events':[e]}).status_code==200
    reply.assert_not_called()

def test_recording_link(client,monkeypatch):
    reply=Mock();monkeypatch.setattr(line_api,'reply_message',reply)
    e=event();e['message']['text']='@recording'
    assert signed(client,{'events':[e]}).status_code==200
    assert 'https://liff.line.me/123-demo' in reply.call_args.args[1]

def test_cross_origin_and_demo_disabled(client,monkeypatch):
    monkeypatch.setattr(line_api,'verify_id_token',lambda token,channel: token)
    assert client.post('/api/expenses',json=payload(),headers={**headers(),'Origin':'https://evil.example'}).status_code==403
    assert client.post('/demo/seed',json={}).status_code==404
    assert 'demo-user' not in client.get('/').text

def test_demo_mode(tmp_path):
    demo=create_app({'TESTING':True,'DEMO_MODE':True,'DATABASE':str(tmp_path/'demo.db')}).test_client()
    assert demo.post('/demo/seed',json={}).status_code==200
    assert demo.post('/demo/seed',json={}).status_code==200
    assert demo.get('/api/summary').json['count']==4
    assert demo.get('/api/summary').json['total_cents']==133000
    assert demo.post('/callback',json={'events':[]}).status_code==404
    assert demo.post('/api/expenses',json=payload()).status_code==201

def test_token_validation(monkeypatch):
    response=Mock(status_code=200)
    response.json.return_value={'sub':'verified-user','aud':'123','iss':'https://access.line.me','exp':time.time()+60}
    monkeypatch.setattr(line_api.requests,'post',Mock(return_value=response))
    assert line_api.verify_id_token('token','123')=='verified-user'
    for patch in [{'aud':'wrong'},{'exp':0},{'iss':'https://evil.example'},{'sub':''}]:
        original=response.json.return_value.copy();response.json.return_value.update(patch)
        with pytest.raises(line_api.AuthenticationError):line_api.verify_id_token('token','123')
        response.json.return_value=original

def test_production_config_required(tmp_path):
    with pytest.raises(RuntimeError):create_app({'DATABASE':str(tmp_path/'db')})

def test_non_ascii_signature_rejected(client):
    assert client.post('/callback',json={'events':[]},headers={'X-Line-Signature':'中文'}).status_code==400

def test_https_origin_behind_proxy(client,monkeypatch):
    monkeypatch.setattr(line_api,'verify_id_token',lambda token,channel: token)
    response=client.post('/api/expenses',json=payload(),headers={**headers(),'Host':'spending.example','Origin':'https://spending.example','X-Forwarded-Proto':'https'})
    assert response.status_code==201

def test_active_webhook_returns_retryable_status(app,client):
    app.extensions['store'].claim_event('event-001')
    assert signed(client,{'events':[event()]}).status_code==503
