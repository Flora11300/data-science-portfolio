"""SQLite persistence. Every expense operation requires a verified user ID."""
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from .domain import ValidationError, validate_month

class Store:
    def __init__(self,path):
        self.path=path
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS expenses(
              id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, request_id TEXT NOT NULL,
              category TEXT NOT NULL, date TEXT NOT NULL, cents INTEGER NOT NULL CHECK(cents>0),
              note TEXT NOT NULL, UNIQUE(user_id,request_id));
            CREATE INDEX IF NOT EXISTS expense_user_date ON expenses(user_id,date);
            CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,status TEXT NOT NULL,claimed_at REAL NOT NULL, owner TEXT NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally: c.close()

    def add_expense(self,user_id,request_id,expense):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM expenses WHERE user_id=? AND request_id=?',(user_id,request_id)).fetchone()
            if old:
                if any(old[k]!=expense[k] for k in ('category','date','cents','note')):
                    raise ValidationError('此提交編號已用於不同內容，請重新送出')
                return self.public(old),False
            cur=c.execute('INSERT INTO expenses(user_id,request_id,category,date,cents,note) VALUES(?,?,?,?,?,?)',(user_id,request_id,expense['category'],expense['date'],expense['cents'],expense['note']))
            row=c.execute('SELECT * FROM expenses WHERE id=?',(cur.lastrowid,)).fetchone()
            return self.public(row),True

    @staticmethod
    def public(row):
        return {k:row[k] for k in ('id','category','date','cents','note')}

    def list_expenses(self,user_id,limit=10):
        with self.connection() as c:
            return [self.public(r) for r in c.execute('SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC,id DESC LIMIT ?',(user_id,limit))]

    def monthly_summary(self,user_id,month):
        validate_month(month)
        with self.connection() as c:
            rows=c.execute('SELECT category,SUM(cents) AS cents,COUNT(*) AS count FROM expenses WHERE user_id=? AND substr(date,1,7)=? GROUP BY category ORDER BY cents DESC,category',(user_id,month)).fetchall()
        total=sum(r['cents'] for r in rows)
        return dict(month=month,total_cents=total,count=sum(r['count'] for r in rows),categories=[dict(category=r['category'],cents=r['cents'],count=r['count'],percent=round(100*r['cents']/total,2)) for r in rows])

    def claim_event(self,event_id,now=None):
        now=time.time() if now is None else now
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM events WHERE event_id=?',(event_id,)).fetchone()
            if row and (row['status']=='done' or now-row['claimed_at']<60): return False
            owner=uuid.uuid4().hex
            c.execute('INSERT INTO events VALUES(?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET status=excluded.status,claimed_at=excluded.claimed_at,owner=excluded.owner',(event_id,'processing',now,owner))
            return owner

    def finish_event(self,event_id,owner):
        with self.connection() as c: c.execute("UPDATE events SET status='done' WHERE event_id=? AND owner=?",(event_id,owner))

    def release_event(self,event_id,owner):
        with self.connection() as c: c.execute("DELETE FROM events WHERE event_id=? AND owner=? AND status='processing'",(event_id,owner))

    def event_done(self,event_id):
        with self.connection() as c:
            row=c.execute("SELECT status FROM events WHERE event_id=?",(event_id,)).fetchone()
            return row is not None and row["status"]=="done"
