"""
Admin dashboard page: visual tracking of voice calls,
outreach log, interest breakdown, and follow-up status.
Protected by a simple password cookie.
"""

import hashlib
import os

from fastapi import APIRouter, Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "amplivo")
_TOKEN = hashlib.sha256(f"amplivo-admin-{ADMIN_PASSWORD}".encode()).hexdigest()[:32]


def _is_authed(admin_token: str | None) -> bool:
    return admin_token == _TOKEN


@router.get("/admin/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    error_html = (
        '<p style="color:var(--red);margin-bottom:16px">Falsches Passwort.</p>'
        if error else ""
    )
    return LOGIN_HTML.replace("{{ERROR}}", error_html)


@router.post("/admin/login")
async def login(request: Request):
    form = await request.form()
    password = form.get("password", "")
    if password == ADMIN_PASSWORD:
        resp = RedirectResponse("/admin", status_code=303)
        resp.set_cookie(
            "admin_token", _TOKEN,
            httponly=True, max_age=60 * 60 * 24 * 7, samesite="lax",
        )
        return resp
    return RedirectResponse("/admin/login?error=1", status_code=303)


@router.get("/admin/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie("admin_token")
    return resp


@router.get("/admin", response_class=HTMLResponse)
def admin_page(admin_token: str | None = Cookie(default=None)):
    if not _is_authed(admin_token):
        return RedirectResponse("/admin/login", status_code=303)
    return ADMIN_HTML


@router.get("/api/admin/data")
def admin_data_proxy(admin_token: str | None = Cookie(default=None)):
    """Guard the admin API behind the same cookie."""
    if not _is_authed(admin_token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    from dashboard.api import get_admin_data
    return get_admin_data()


LOGIN_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Amplivo Admin - Login</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0f172a;--card:#1e293b;--accent:#3b82f6;--red:#ef4444;--text:#e2e8f0;--muted:#94a3b8;--border:#334155}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);
min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-box{background:var(--card);border-radius:16px;padding:40px;width:100%;max-width:380px;text-align:center}
h1{font-size:1.3rem;font-weight:700;margin-bottom:8px}
h1 span{color:var(--accent)}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:28px}
input[type=password]{width:100%;padding:12px 16px;border-radius:8px;border:1px solid var(--border);
background:#0f172a;color:var(--text);font-size:.95rem;margin-bottom:16px;outline:none}
input[type=password]:focus{border-color:var(--accent)}
button{width:100%;padding:12px;border-radius:8px;border:none;background:var(--accent);
color:#fff;font-size:.95rem;font-weight:600;cursor:pointer}
button:hover{opacity:.9}
</style>
</head>
<body>
<div class="login-box">
    <h1><span>Amplivo</span> Admin</h1>
    <p class="sub">Bitte Passwort eingeben</p>
    {{ERROR}}
    <form method="POST" action="/admin/login">
        <input type="password" name="password" placeholder="Passwort" autofocus>
        <button type="submit">Anmelden</button>
    </form>
</div>
</body>
</html>"""


ADMIN_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Amplivo Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0f172a;--card:#1e293b;--accent:#3b82f6;--green:#22c55e;
--red:#ef4444;--yellow:#eab308;--orange:#f97316;--purple:#a78bfa;
--text:#e2e8f0;--muted:#94a3b8;--border:#334155}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.app{max-width:1400px;margin:0 auto;padding:24px}
.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;flex-wrap:wrap;gap:12px}
h1{font-size:1.4rem;font-weight:700;display:flex;align-items:center;gap:10px}
h1 span{color:var(--accent)}
.btn{border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:600;
     transition:opacity .2s}
.btn:hover{opacity:.85}
.btn-primary{background:var(--accent);color:#fff}
.nav-links{display:flex;gap:12px;align-items:center}
.nav-links a{color:var(--muted);text-decoration:none;font-size:.85rem}
.nav-links a:hover{color:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:28px}
.stat{background:var(--card);border-radius:12px;padding:18px;text-align:center}
.stat-value{font-size:1.8rem;font-weight:700}
.stat-label{font-size:.78rem;color:var(--muted);margin-top:3px}
.blue{color:var(--accent)}.green{color:var(--green)}.yellow{color:var(--yellow)}
.orange{color:var(--orange)}.red{color:var(--red)}.purple{color:var(--purple)}
.section{margin-bottom:32px}
.section-title{font-size:1rem;font-weight:600;color:var(--muted);margin-bottom:14px;
display:flex;align-items:center;gap:8px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}
@media(max-width:768px){.grid-2{grid-template-columns:1fr}}
.chart-card{background:var(--card);border-radius:12px;padding:20px}
.chart-card h3{font-size:.9rem;color:var(--muted);margin-bottom:14px}
.bar-chart{display:flex;flex-direction:column;gap:10px}
.bar-row{display:flex;align-items:center;gap:10px}
.bar-label{width:110px;font-size:.82rem;color:var(--muted);text-align:right;flex-shrink:0}
.bar-track{flex:1;height:28px;background:#0f172a;border-radius:6px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:6px;transition:width .4s ease;display:flex;align-items:center;
padding-left:10px;font-size:.78rem;font-weight:600;color:#fff;min-width:fit-content}
.bar-fill.green{background:var(--green)}.bar-fill.yellow{background:var(--yellow)}
.bar-fill.red{background:var(--red)}.bar-fill.blue{background:var(--accent)}
.bar-fill.purple{background:var(--purple)}.bar-fill.orange{background:var(--orange)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden}
th{text-align:left;padding:10px 14px;background:#0f172a;color:var(--muted);font-size:.75rem;
text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}
td{padding:10px 14px;border-top:1px solid var(--border);font-size:.83rem}
tr:hover td{background:rgba(59,130,246,.04)}
.badge{padding:2px 9px;border-radius:16px;font-size:.72rem;font-weight:600;display:inline-block;white-space:nowrap}
.badge-voice{background:#312e81;color:#a78bfa}
.badge-email{background:#1e3a5f;color:#60a5fa}
.badge-sms{background:#422006;color:#fbbf24}
.badge-sent{background:#14532d;color:#4ade80}
.badge-failed{background:#450a0a;color:#fca5a5}
.badge-skipped{background:#3f3f46;color:#a1a1aa}
.badge-interested{background:#064e3b;color:#34d399}
.badge-maybe_later{background:#422006;color:#fbbf24}
.badge-not_interested{background:#450a0a;color:#fca5a5}
.badge-other{background:#1e293b;color:#94a3b8}
.badge-deployed{background:#422006;color:#fbbf24}
.badge-outreach_sent{background:#312e81;color:#a78bfa}
.badge-rejected{background:#450a0a;color:#fca5a5}
.badge-responded{background:#064e3b;color:#34d399}
.badge-converted{background:#14532d;color:#22c55e;border:1px solid #22c55e}
.transcript{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
color:var(--muted);font-size:.78rem;cursor:help}
.empty{text-align:center;padding:40px;color:var(--muted)}
.tabs{display:flex;gap:4px;margin-bottom:16px}
.tab{padding:6px 16px;border-radius:6px;cursor:pointer;font-size:.82rem;color:var(--muted);
background:transparent;border:1px solid var(--border);transition:all .2s}
.tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
</style>
</head>
<body>
<div class="app">
    <div class="top-bar">
        <h1><span>Amplivo</span> Admin</h1>
        <div class="nav-links">
            <a href="/">Pipeline Dashboard</a>
            <a href="/admin/logout">Logout</a>
            <button class="btn btn-primary" onclick="loadData()">Refresh</button>
        </div>
    </div>

    <div id="stats" class="stats"></div>

    <div class="grid-2">
        <div class="chart-card">
            <h3>Voice Calls nach Interesse</h3>
            <div id="interest-chart" class="bar-chart"></div>
        </div>
        <div class="chart-card">
            <h3>Outreach nach Kanal</h3>
            <div id="channel-chart" class="bar-chart"></div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">
            <div class="tabs" id="tabs">
                <div class="tab active" data-tab="voice" onclick="switchTab('voice')">Voice Calls</div>
                <div class="tab" data-tab="all" onclick="switchTab('all')">Alle Outreach</div>
            </div>
        </div>
        <table>
            <thead id="table-head"></thead>
            <tbody id="table-body"></tbody>
        </table>
        <div id="empty-state" class="empty" style="display:none">Noch keine Daten vorhanden.</div>
    </div>
</div>

<script>
let DATA = null;
let currentTab = 'voice';

async function loadData(){
    try{
        const resp = await fetch('/api/admin/data');
        if(resp.status===401){window.location='/admin/login';return;}
        DATA = await resp.json();
        render();
    }catch(e){
        console.error('Failed to load admin data', e);
    }
}

function render(){
    if(!DATA) return;
    renderStats(DATA.summary);
    renderInterestChart(DATA.summary.interest_counts);
    renderChannelChart(DATA.summary.channel_counts);
    renderTable();
}

function renderStats(s){
    document.getElementById('stats').innerHTML=`
        <div class="stat"><div class="stat-value blue">${s.total_outreach}</div>
            <div class="stat-label">Total Outreach</div></div>
        <div class="stat"><div class="stat-value purple">${s.total_voice_calls}</div>
            <div class="stat-label">Voice Calls</div></div>
        <div class="stat"><div class="stat-value green">${s.interest_counts.interested||0}</div>
            <div class="stat-label">Interessiert</div></div>
        <div class="stat"><div class="stat-value yellow">${s.interest_counts.maybe_later||0}</div>
            <div class="stat-label">Vielleicht spaeter</div></div>
        <div class="stat"><div class="stat-value red">${s.interest_counts.not_interested||0}</div>
            <div class="stat-label">Kein Interesse</div></div>
        <div class="stat"><div class="stat-value orange">${s.followup_counts.email_sent+s.followup_counts.sms_sent}</div>
            <div class="stat-label">Follow-ups gesendet</div></div>
        <div class="stat"><div class="stat-value blue">${s.opened_count}</div>
            <div class="stat-label">Previews geoeffnet</div></div>
        <div class="stat"><div class="stat-value green">${s.open_rate}%</div>
            <div class="stat-label">Open Rate</div></div>
    `;
}

function renderBarChart(containerId, items){
    const max = Math.max(...items.map(i=>i.value), 1);
    document.getElementById(containerId).innerHTML = items.map(i=>{
        const pct = Math.max((i.value/max)*100, i.value>0?8:0);
        return `<div class="bar-row">
            <div class="bar-label">${i.label}</div>
            <div class="bar-track">
                <div class="bar-fill ${i.color}" style="width:${pct}%">${i.value}</div>
            </div>
        </div>`;
    }).join('');
}

function renderInterestChart(ic){
    renderBarChart('interest-chart', [
        {label:'Interessiert', value:ic.interested||0, color:'green'},
        {label:'Vielleicht', value:ic.maybe_later||0, color:'yellow'},
        {label:'Kein Interesse', value:ic.not_interested||0, color:'red'},
        {label:'Sonstige', value:ic.other||0, color:'blue'},
    ]);
}

function renderChannelChart(cc){
    renderBarChart('channel-chart', [
        {label:'Voice', value:cc.voice||0, color:'purple'},
        {label:'E-Mail', value:cc.email||0, color:'blue'},
        {label:'SMS', value:cc.sms||0, color:'orange'},
    ]);
}

function switchTab(tab){
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===tab));
    renderTable();
}

function renderTable(){
    const head = document.getElementById('table-head');
    const body = document.getElementById('table-body');
    const empty = document.getElementById('empty-state');

    if(currentTab === 'voice'){
        head.innerHTML=`<tr>
            <th>Zeit</th><th>Unternehmen</th><th>Typ</th><th>Stadt</th>
            <th>Interesse</th><th>Follow-up</th><th>Lead Status</th><th>Transcript</th>
        </tr>`;
        const rows = DATA.voice_calls || [];
        if(!rows.length){empty.style.display='block';body.innerHTML='';return;}
        empty.style.display='none';
        body.innerHTML = rows.map(r=>`<tr>
            <td>${fmtDate(r.sent_at)}</td>
            <td><strong>${r.business_name}</strong></td>
            <td>${r.business_type}</td>
            <td>${r.city}</td>
            <td><span class="badge badge-${r.interest_level}">${fmtInterest(r.interest_level)}</span></td>
            <td>${fmtFollowup(r)}</td>
            <td><span class="badge badge-${r.lead_status}">${r.lead_status}</span></td>
            <td><span class="transcript" title="${esc(r.transcript_preview||'')}">${esc(r.transcript_preview||'-')}</span></td>
        </tr>`).join('');
    } else {
        head.innerHTML=`<tr>
            <th>Zeit</th><th>Unternehmen</th><th>Kanal</th><th>Empfaenger</th>
            <th>Betreff</th><th>Status</th><th>Geoeffnet</th><th>Lead Status</th>
        </tr>`;
        const rows = DATA.outreach_log || [];
        if(!rows.length){empty.style.display='block';body.innerHTML='';return;}
        empty.style.display='none';
        body.innerHTML = rows.map(r=>`<tr>
            <td>${fmtDate(r.sent_at)}</td>
            <td><strong>${r.business_name}</strong></td>
            <td><span class="badge badge-${r.channel}">${r.channel}</span></td>
            <td>${r.recipient}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.subject)}</td>
            <td><span class="badge badge-${r.status}">${r.status}</span></td>
            <td>${r.opened_at ? fmtDate(r.opened_at) : '-'}</td>
            <td><span class="badge badge-${r.lead_status}">${r.lead_status}</span></td>
        </tr>`).join('');
    }
}

function fmtDate(iso){
    if(!iso)return'-';
    const d=new Date(iso);
    return d.toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
}
function fmtInterest(i){
    return {interested:'Interessiert',maybe_later:'Vielleicht',not_interested:'Kein Interesse',other:'Sonstige'}[i]||i;
}
function fmtFollowup(r){
    if(r.lead_status==='outreach_sent') return '<span class="badge badge-sent">gesendet</span>';
    if(r.lead_status==='rejected') return '<span class="badge badge-failed">abgelehnt</span>';
    if(r.interest_level==='interested') return '<span class="badge badge-skipped">ausstehend</span>';
    return '-';
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>"""
