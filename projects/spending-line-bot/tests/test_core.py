import pytest
from spending.domain import validate_expense, ValidationError
from spending.store import Store


def expense(**kw):
    return dict(category='food', date='2026-11-25', amount='12.30', note='Lunch', **kw)

@pytest.mark.parametrize('amount', ['0', '-1', '1.001', 'NaN', 'Infinity', True, '1e2', '1000000000'])
def test_reject_bad_money(amount):
    p=expense(); p['amount']=amount
    with pytest.raises(ValidationError): validate_expense(p)

def test_exact_cents():
    p=expense(); p['amount']='0.10'
    assert validate_expense(p)['cents']==10

@pytest.mark.parametrize('change', [{'date':'2026-02-30'}, {'date':'25/11/2026'}, {'category':'unknown'}, {'note':'x'*201}])
def test_bad_fields(change):
    p=expense();p.update(change)
    with pytest.raises(ValidationError): validate_expense(p)

@pytest.fixture
def store(tmp_path): return Store(str(tmp_path/'test.sqlite3'))

def test_isolation_idempotency_conflicts(store):
    e=validate_expense(expense())
    a,new=store.add_expense('alice','request-0001',e)
    assert new
    b,new=store.add_expense('alice','request-0001',e)
    assert not new and b==a
    assert store.list_expenses('bob')==[]
    _,new=store.add_expense('bob','request-0001',e)
    assert new
    e['cents']=50
    with pytest.raises(ValidationError): store.add_expense('alice','request-0001',e)

def test_month_summary_and_recent(store):
    for n,(day,amount,category) in enumerate([('2026-10-31','99','food'),('2026-11-01','0.10','food'),('2026-11-30','0.20','food'),('2026-11-25','1','transport'),('2026-12-01','99','food')]):
        store.add_expense('a',f'request-{n:04}',validate_expense(dict(date=day,amount=amount,category=category,note='')))
    s=store.monthly_summary('a','2026-11')
    assert s['total_cents']==130 and s['count']==3
    assert s['categories'][0]['category']=='transport'
    assert s['categories'][1]['cents']==30
    assert store.monthly_summary('b','2026-11')['total_cents']==0
    assert len(store.list_expenses('a',2))==2
    assert store.list_expenses('a',2)[0]['date']=='2026-12-01'

def test_event_lease_retry(store):
    assert store.claim_event('event',now=100)
    assert not store.claim_event('event',now=110)
    owner=store.claim_event('event',now=200)
    assert owner
    store.release_event('event',owner)
    owner=store.claim_event('event',now=201)
    assert owner
    store.finish_event('event',owner)
    assert not store.claim_event('event',now=1000)

def test_stale_worker_cannot_change_new_lease(store):
    old=store.claim_event('lease',now=100)
    new=store.claim_event('lease',now=200)
    assert old and new and old!=new
    store.release_event('lease',old)
    store.finish_event('lease',old)
    assert not store.claim_event('lease',now=201)
    store.finish_event('lease',new)
    assert store.event_done('lease')
