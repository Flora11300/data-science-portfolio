"""HTTP boundaries, LINE command routing, and isolated local demo mode."""
import re
from datetime import datetime
from functools import wraps
from flask import Blueprint,request,current_app,jsonify,render_template,g,abort
from werkzeug.exceptions import BadRequest,UnsupportedMediaType
from . import line_api
from .domain import CATEGORIES,TAIPEI,ValidationError,current_month,validate_month,validate_expense,summary_text,records_text

bp=Blueprint('spending',__name__)

def store():return current_app.extensions['store']

def authenticated(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        if current_app.config['DEMO_MODE']:g.user_id='demo-user'
        else:
            scheme,_,token=request.headers.get('Authorization','').partition(' ')
            if scheme!='Bearer' or not token or len(token)>8192:return jsonify(error='請先使用 LINE 登入'),401
            try:g.user_id=line_api.verify_id_token(token,current_app.config['LINE_LOGIN_CHANNEL_ID'])
            except line_api.AuthenticationError:return jsonify(error='LINE 登入已失效，請重新開啟表單'),401
        return view(*args,**kwargs)
    return wrapped

@bp.before_request
def check_origin():
    # No CORS is enabled. Reject cross-site writes even in local demo mode.
    if request.method=='POST' and request.path!='/callback':
        origin=request.headers.get('Origin')
        allowed=request.host_url.rstrip('/') if current_app.config['DEMO_MODE'] else current_app.config['PUBLIC_ORIGIN']
        if origin and origin!=allowed:
            return jsonify(error='不接受跨網站提交'),403

@bp.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['X-Frame-Options']='DENY'
    return response

@bp.errorhandler(ValidationError)
def validation_error(exc):return jsonify(error=str(exc)),400

@bp.errorhandler(BadRequest)
@bp.errorhandler(UnsupportedMediaType)
def bad_json(exc):return jsonify(error='請提供有效 JSON 資料'),400

@bp.route('/')
def home():
    return render_template('index.html',demo=current_app.config['DEMO_MODE'],liff_id=current_app.config['LIFF_ID'],categories=CATEGORIES,today=datetime.now(TAIPEI).date().isoformat())

@bp.get('/health')
def health():return jsonify(status='ok',mode='demo' if current_app.config['DEMO_MODE'] else 'line')

@bp.post('/api/expenses')
@authenticated
def add_expense():
    p=request.get_json()
    e=validate_expense(p)
    key=p.get('request_id')
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',key):raise ValidationError('提交編號無效')
    try:record,created=store().add_expense(g.user_id,key,e)
    except ValidationError as exc:return jsonify(error=str(exc)),409
    return jsonify(record=record,created=created),201 if created else 200

@bp.get('/api/expenses')
@authenticated
def expenses():return jsonify(records=store().list_expenses(g.user_id))

@bp.get('/api/summary')
@authenticated
def summary():
    month=validate_month(request.args.get('month',current_month()))
    return jsonify(store().monthly_summary(g.user_id,month))

@bp.post('/demo/seed')
def seed():
    if not current_app.config['DEMO_MODE']:abort(404)
    month=current_month()
    for n,(category,amount,note) in enumerate([('food','180','Demo lunch'),('transport','90','Demo train'),('shopping','980','Demo books'),('food','80','Demo coffee')]):
        e=validate_expense(dict(category=category,amount=amount,date=month+'-01',note=note))
        store().add_expense('demo-user',f'demo-{month}-{n}',e)
    return jsonify(ok=True)

def command(text,user):
    if text in ('記帳','@recording'):
        return '點此記帳：\nhttps://liff.line.me/'+current_app.config['LIFF_ID']
    if text=='明細':return records_text(store().list_expenses(user))
    if text in ('分析','@analyze'):return summary_text(store().monthly_summary(user,current_month()))
    return 'Spending 記帳助手\n記帳：開啟記帳表單\n明細：最近 10 筆支出\n分析：本月分類統計'

@bp.post('/callback')
def callback():
    if current_app.config['DEMO_MODE']:abort(404)
    body=request.get_data()
    if not line_api.verify_signature(body,request.headers.get('X-Line-Signature',''),current_app.config['LINE_CHANNEL_SECRET']):
        return jsonify(error='Invalid webhook signature'),400
    p=request.get_json()
    if not isinstance(p,dict) or not isinstance(p.get('events'),list):raise ValidationError('Invalid webhook events')
    for e in p['events']:
        if not isinstance(e,dict):raise ValidationError('Invalid webhook event')
        source=e.get('source');message=e.get('message')
        if e.get('type')!='message' or not isinstance(source,dict) or source.get('type')!='user' or not isinstance(message,dict) or message.get('type')!='text':continue
        event_id=e.get('webhookEventId');user=source.get('userId');token=e.get('replyToken');text=message.get('text')
        if not all(isinstance(v,str) and v for v in (event_id,user,token,text)):continue
        owner=store().claim_event(event_id)
        if not owner:
            if store().event_done(event_id):continue
            return jsonify(error='Event is still processing; retry later'),503
        try:
            line_api.reply_message(token,command(text.strip(),user))
        except line_api.TransportError:
            store().release_event(event_id,owner)
            return jsonify(error='LINE temporarily unavailable; retry later'),503
        store().finish_event(event_id,owner)
    return jsonify(ok=True)
