'use strict';
const config=JSON.parse(document.getElementById('app-config').textContent);
const form=document.getElementById('expense-form');
const statusEl=document.getElementById('status');
const submit=document.getElementById('submit');
let ready=false, requestId=crypto.randomUUID(), retryPayload=null;
const currency=cents=>new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(cents/100);
function status(message,error=false){statusEl.textContent=message;statusEl.classList.toggle('error',error);}
async function api(path,options={}){
  const headers={...options.headers};
  if(options.body)headers['Content-Type']='application/json';
  if(!config.demo){const token=liff.getIDToken();if(!token)throw Error('請重新使用 LINE 登入');headers.Authorization='Bearer '+token;}
  const response=await fetch(path,{...options,headers});
  let data;try{data=await response.json();}catch{throw Error('服務暫時無法使用，請稍後再試');}
  if(!response.ok)throw Error(data.error||'無法完成操作，請稍後再試');
  return data;
}
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
async function refresh(){
  const [summary,result]=await Promise.all([api('/api/summary'),api('/api/expenses')]);
  document.getElementById('month-label').textContent=summary.month.replace('-',' / ');
  document.getElementById('total').textContent='NT$ '+currency(summary.total_cents);
  document.getElementById('count').textContent=summary.count+' 筆記錄';
  const categories=document.getElementById('categories');categories.replaceChildren();
  if(!summary.categories.length)categories.append(el('p','empty','本月尚無支出，從第一筆開始。'));
  for(const row of summary.categories){
    const item=el('div','category-row'),top=el('div','category-top'),right=el('span');
    top.append(el('span','',config.categories[row.category]));right.append(el('b','','NT$ '+currency(row.cents)),document.createTextNode(row.percent.toFixed(1)+'%'));top.append(right);
    const bar=el('div','bar'),fill=el('i');fill.style.width=Math.min(100,Math.max(0,row.percent))+'%';bar.append(fill);item.append(top,bar);categories.append(item);
  }
  const records=document.getElementById('records');records.replaceChildren();
  if(!result.records.length)records.append(el('li','empty','尚無記錄'));
  for(const record of result.records){const item=el('li'),detail=el('div');detail.append(el('span','record-name',config.categories[record.category]+(record.note?' · '+record.note:'')),el('span','record-date',record.date));item.append(detail,el('span','record-money','NT$ '+currency(record.cents)));records.append(item);}
}
form.addEventListener('input',()=>{requestId=crypto.randomUUID();retryPayload=null;});
form.addEventListener('submit',async event=>{
  event.preventDefault();if(!ready)return;
  const payload=retryPayload||{...Object.fromEntries(new FormData(form)),request_id:requestId};
  retryPayload=payload;submit.disabled=true;status('正在記下這筆支出…');
  try{
    const data=await api('/api/expenses',{method:'POST',body:JSON.stringify(payload)});
    requestId=crypto.randomUUID();retryPayload=null;form.elements.amount.value='';form.elements.note.value='';
    status(data.created?'已記下這筆支出。':'這筆已經儲存，沒有重複記帳。');
    try{await refresh();}catch{status('支出已儲存，但列表更新失敗，請按重新整理。',true);}
  }catch(error){status(error.message+'；重試相同內容不會重複記帳。',true);}finally{submit.disabled=false;}
});
document.getElementById('refresh').addEventListener('click',async()=>{try{await refresh();status('記錄已更新。');}catch(error){status(error.message,true);}});
const seed=document.getElementById('seed');
if(seed)seed.addEventListener('click',async()=>{seed.disabled=true;try{await api('/demo/seed',{method:'POST',body:'{}'});await refresh();status('已載入虛構示範資料。');}catch(error){status(error.message,true);}finally{seed.disabled=false;}});
(async()=>{
  try{
    if(!config.demo){await liff.init({liffId:config.liffId});if(!liff.isLoggedIn()){liff.login();return;}if(!liff.getIDToken())throw Error('請在 LIFF 設定中啟用 openid 權限');}
    await refresh();ready=true;submit.disabled=false;status(config.demo?'本機展示已就緒，資料僅供示範。':'已使用 LINE 登入，可以開始記帳。');
  }catch(error){status(error.message,true);}
})();
