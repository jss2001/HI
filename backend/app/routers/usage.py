"""토큰/비용 사용량 — JSON API + HTML 대시보드."""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.core.usage_tracker import UsageTracker
from app.dependencies import get_usage_tracker


router = APIRouter()


_DASHBOARD_HTML = """<!doctype html>
<html lang=ko><head><meta charset=utf-8><title>HI Usage</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,'Apple SD Gothic Neo','Pretendard',Arial,sans-serif;background:#0a0a0c;color:#fafafa;-webkit-font-smoothing:antialiased}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:22px;font-weight:800;margin:0 0 6px;letter-spacing:-0.02em}
.sub{font-size:11px;color:#9ca3af;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.card{background:#131317;border:1px solid #26262b;border-radius:14px;padding:14px}
.lbl{font-size:10px;color:#9ca3af;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px}
.val{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums}
.val.cost{color:#ff7a7a}
.val.today{color:#ffd86b}
.sec{margin-top:24px}
.sec h2{font-size:13px;font-weight:800;color:#d4d4d8;margin:0 0 10px;letter-spacing:.02em}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #1c1c20;font-variant-numeric:tabular-nums}
th{font-size:10px;color:#9ca3af;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
td.num{text-align:right;color:#fafafa}
td.cost{text-align:right;color:#ff7a7a;font-weight:700}
.chart{height:60px;display:flex;align-items:flex-end;gap:3px;padding:6px 0}
.bar{flex:1;background:linear-gradient(180deg,#a78bfa,#7c3aed);border-radius:2px;min-height:2px;position:relative}
.bar:hover{background:#a78bfa}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}
.refresh{font-size:10px;color:#6b7280;margin-left:8px}
.live{display:inline-block;width:8px;height:8px;background:#10b981;border-radius:50%;margin-right:6px;animation:pulse 1.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
</style></head>
<body>
<div class=wrap>
<h1><span class=live></span>HI Usage Monitor<span class=refresh id=updated></span></h1>
<div class=sub>실시간 OpenAI 토큰/비용 추적 · 5초마다 자동 갱신</div>

<div class=grid>
<div class=card><div class=lbl>오늘 비용</div><div class="val cost today" id=today-cost>$0.000</div></div>
<div class=card><div class=lbl>오늘 호출</div><div class=val id=today-calls>0</div></div>
<div class=card><div class=lbl>누적 비용</div><div class="val cost" id=total-cost>$0.000</div></div>
<div class=card><div class=lbl>누적 호출</div><div class=val id=total-calls>0</div></div>
</div>

<div class=sec><h2>일자별 사용 추이</h2>
<div class=card><div class=chart id=chart></div></div>
<table id=daily><thead><tr><th>날짜</th><th>호출</th><th class=num>입력</th><th class=num>출력</th><th class=num>비용</th></tr></thead><tbody></tbody></table>
</div>

<div class=sec><h2>기능별 비용</h2>
<table id=labels><thead><tr><th>기능</th><th class=num>호출</th><th class=num>비용</th></tr></thead><tbody></tbody></table>
</div>

<div class=sec><h2>최근 호출 (최신순)</h2>
<table id=recent><thead><tr><th>시간</th><th>모델</th><th>라벨</th><th class=num>입력</th><th class=num>출력</th><th class=num>비용</th></tr></thead><tbody></tbody></table>
</div>
</div>

<script>
async function load(){
  const r=await fetch('/api/usage');
  const d=await r.json();
  document.getElementById('today-cost').textContent='$'+d.today.cost_usd.toFixed(4);
  document.getElementById('today-calls').textContent=d.today.calls.toLocaleString();
  document.getElementById('total-cost').textContent='$'+d.total.cost_usd.toFixed(4);
  document.getElementById('total-calls').textContent=(d.total.prompt+d.total.completion).toLocaleString()+' tok';
  document.getElementById('updated').textContent='· '+new Date().toLocaleTimeString();
  const days=[...d.by_day].reverse();
  const max=Math.max(...days.map(x=>x.cost_usd),0.0001);
  document.getElementById('chart').innerHTML=days.map(x=>`<div class=bar style="height:${(x.cost_usd/max*100)}%" title="${x.date}: $${x.cost_usd.toFixed(4)}"></div>`).join('');
  document.querySelector('#daily tbody').innerHTML=d.by_day.map(x=>
    `<tr><td>${x.date}</td><td>${x.calls}</td><td class=num>${x.prompt.toLocaleString()}</td><td class=num>${x.completion.toLocaleString()}</td><td class=cost>$${x.cost_usd.toFixed(4)}</td></tr>`
  ).join('');
  document.querySelector('#labels tbody').innerHTML=d.by_label.map(x=>
    `<tr><td>${x.label}</td><td class=num>${x.calls}</td><td class=cost>$${x.cost_usd.toFixed(4)}</td></tr>`
  ).join('');
  document.querySelector('#recent tbody').innerHTML=d.recent.map(x=>
    `<tr><td>${x.ts.slice(11,19)}</td><td>${x.model}</td><td>${x.label}</td><td class=num>${x.prompt}</td><td class=num>${x.completion}</td><td class=cost>$${x.cost_usd.toFixed(6)}</td></tr>`
  ).join('');
}
load();
setInterval(load,5000);
</script>
</body></html>"""


@router.get("/api/usage")
def api_usage(tracker: UsageTracker = Depends(get_usage_tracker)):
    return tracker.summary()


@router.get("/usage", response_class=HTMLResponse)
def usage_dashboard():
    return _DASHBOARD_HTML
