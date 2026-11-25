"""Validation and formatting independent of Flask and LINE."""
import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

CATEGORIES = {'food':'飲食', 'household':'生活用品', 'transport':'交通', 'entertainment':'娛樂', 'shopping':'購物', 'other':'其他'}
TAIPEI = ZoneInfo('Asia/Taipei')

class ValidationError(ValueError):
    pass

def current_month():
    return datetime.now(TAIPEI).strftime('%Y-%m')

def validate_month(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}',value):
        raise ValidationError('月份格式須為 YYYY-MM')
    try: date.fromisoformat(value+'-01')
    except ValueError as exc: raise ValidationError('月份無效') from exc
    return value

def validate_expense(payload):
    if not isinstance(payload,dict): raise ValidationError('請提供記帳資料')
    category=payload.get('category')
    if not isinstance(category,str) or category not in CATEGORIES: raise ValidationError('請選擇有效類別')
    day=payload.get('date')
    if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day): raise ValidationError('日期格式須為 YYYY-MM-DD')
    try: date.fromisoformat(day)
    except ValueError as exc: raise ValidationError('日期無效') from exc
    amount=payload.get('amount')
    if not isinstance(amount,(str,int)) or isinstance(amount,bool): raise ValidationError('金額須為正數，最多兩位小數')
    raw=str(amount)
    if len(raw)>16 or not re.fullmatch(r'\d{1,9}(?:\.\d{1,2})?',raw): raise ValidationError('金額須為正數，最多兩位小數')
    cents=int(Decimal(raw)*100)
    if cents<=0: raise ValidationError('金額須大於零')
    note=payload.get('note','')
    if not isinstance(note,str) or len(note)>200: raise ValidationError('備註最多 200 字')
    return dict(category=category,date=day,cents=cents,note=note.strip())

def money(cents): return f'{cents//100:,}.{cents%100:02d}'

def summary_text(summary):
    if not summary['count']: return f"{summary['month']} 尚無記帳資料，輸入「記帳」開始。"
    lines=[f"{summary['month']} 支出分析",f"總支出 NT$ {money(summary['total_cents'])}｜{summary['count']} 筆"]
    lines.extend(f"{CATEGORIES[r['category']]}：NT$ {money(r['cents'])}（{r['percent']:.1f}%）" for r in summary['categories'])
    return '\n'.join(lines)

def records_text(records):
    if not records: return '尚無記帳資料，輸入「記帳」開始。'
    return '最近 10 筆支出\n'+'\n'.join(f"{r['date']} {CATEGORIES[r['category']]} NT$ {money(r['cents'])}" for r in records)
