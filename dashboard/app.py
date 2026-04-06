"""
FastAPI application serving the dashboard UI, API, and website previews.
This single app runs on Railway and handles everything.
"""

import logging
import os

from fastapi import Cookie, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("landingsmith")

app = FastAPI(title="LandingSmith Dashboard", version="1.0.0")


@app.get("/health")
def health():
    """Lightweight health endpoint for Railway — no DB dependency."""
    return JSONResponse({"status": "ok"})


@app.on_event("startup")
def startup():
    logger.info(f"Starting LandingSmith on PORT={os.environ.get('PORT', 'not set')}")
    try:
        from config.settings import settings
        logger.info(f"DB URL: {settings.db_url[:40]}...")

        from database.connection import init_db
        init_db()
        logger.info("Database initialized")

        from dashboard.api import router as api_router
        from dashboard.preview import router as preview_router
        from dashboard.webhook import router as webhook_router
        from dashboard.admin import router as admin_router
        app.include_router(api_router)
        app.include_router(preview_router)
        app.include_router(webhook_router)
        app.include_router(admin_router)
        logger.info("Routes registered (incl. webhook + admin)")
    except Exception as e:
        logger.error(f"Startup failed (non-fatal): {e}", exc_info=True)


@app.get("/", response_class=HTMLResponse)
def root(admin_token: str | None = Cookie(default=None)):
    from dashboard.admin import _is_authed
    if not _is_authed(admin_token):
        return RedirectResponse("/admin/login", status_code=303)
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WebReach Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0f172a;--card:#1e293b;--accent:#3b82f6;--green:#22c55e;
--red:#ef4444;--yellow:#eab308;--text:#e2e8f0;--muted:#94a3b8}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.app{max-width:1200px;margin:0 auto;padding:24px}
h1{font-size:1.5rem;font-weight:700;margin-bottom:24px;display:flex;align-items:center;gap:12px}
h1 span{color:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}
.stat{background:var(--card);border-radius:12px;padding:20px;text-align:center}
.stat-value{font-size:2rem;font-weight:700;color:var(--accent)}
.stat-label{font-size:.85rem;color:var(--muted);margin-top:4px}
.stat-value.green{color:var(--green)}
.stat-value.yellow{color:var(--yellow)}
.section-title{font-size:1.1rem;font-weight:600;margin-bottom:16px;color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden;margin-bottom:32px}
th{text-align:left;padding:12px 16px;background:#0f172a;color:var(--muted);font-size:.8rem;
text-transform:uppercase;letter-spacing:.5px}
td{padding:12px 16px;border-top:1px solid #334155;font-size:.9rem}
tr:hover td{background:rgba(59,130,246,.05)}
.badge{padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:600;display:inline-block}
.badge-discovered{background:#1e3a5f;color:#60a5fa}
.badge-verified{background:#14532d;color:#4ade80}
.badge-deployed{background:#422006;color:#fbbf24}
.badge-outreach_sent{background:#312e81;color:#a78bfa}
.badge-responded{background:#064e3b;color:#34d399}
.badge-converted{background:#14532d;color:#22c55e;border:1px solid #22c55e}
.badge-rejected{background:#450a0a;color:#fca5a5}
.badge-bounced{background:#450a0a;color:#f87171}
.pipeline{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:32px}
.pipe-card{background:var(--card);border-radius:10px;padding:16px;font-size:.85rem}
.pipe-card .agent{font-weight:600;color:var(--accent);margin-bottom:4px}
.pipe-card .meta{color:var(--muted);font-size:.8rem}
.link{color:var(--accent);text-decoration:none}
.link:hover{text-decoration:underline}
.refresh-btn{background:var(--accent);color:#fff;border:none;padding:8px 20px;border-radius:8px;
cursor:pointer;font-size:.9rem;font-weight:600}
.refresh-btn:hover{opacity:.9}
.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.funnel{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px}
.funnel-step{flex:1;min-width:120px;background:var(--card);border-radius:10px;padding:14px;text-align:center}
.funnel-step .count{font-size:1.5rem;font-weight:700}
.funnel-step .label{font-size:.75rem;color:var(--muted);margin-top:4px}
#loading{text-align:center;padding:40px;color:var(--muted)}
</style>
</head>
<body>
<div class="app">
    <div class="top-bar">
        <h1>&#x1f310; <span>WebReach</span> Pipeline</h1>
        <div style="display:flex;gap:8px;align-items:center">
            <a href="/admin" style="color:var(--muted);text-decoration:none;font-size:.85rem">Admin</a>
            <button class="refresh-btn" onclick="loadAll()">Refresh</button>
        </div>
    </div>
    <div id="stats" class="stats"></div>
    <p class="section-title">Pipeline Funnel</p>
    <div id="funnel" class="funnel"></div>
    <p class="section-title">Recent Pipeline Runs</p>
    <div id="pipeline" class="pipeline"></div>
    <p class="section-title">Leads</p>
    <table><thead><tr>
        <th>Business</th><th>Type</th><th>City</th><th>Status</th>
        <th>Email</th><th>Preview</th><th>Rating</th>
    </tr></thead><tbody id="leads"></tbody></table>
</div>
<script>
async function loadAll(){
    const r0=await fetch('/api/stats');
    if(r0.status===401){window.location='/admin/login';return;}
    const[stats,leads,runs]=await Promise.all([
        r0.json(),
        fetch('/api/leads?limit=100').then(r=>r.json()),
        fetch('/api/pipeline/runs').then(r=>r.json())
    ]);
    renderStats(stats);
    renderFunnel(stats.by_status);
    renderLeads(leads);
    renderPipeline(runs);
}
function renderStats(s){
    document.getElementById('stats').innerHTML=`
        <div class="stat"><div class="stat-value">${s.total_leads}</div><div class="stat-label">Total Leads</div></div>
        <div class="stat"><div class="stat-value">${s.websites_built}</div><div class="stat-label">Websites Built</div></div>
        <div class="stat"><div class="stat-value">${s.deployments_active}</div><div class="stat-label">Deployed</div></div>
        <div class="stat"><div class="stat-value">${s.emails_sent}</div><div class="stat-label">Emails Sent</div></div>
        <div class="stat"><div class="stat-value green">${s.response_rate}%</div><div class="stat-label">Response Rate</div></div>
        <div class="stat"><div class="stat-value yellow">${s.conversion_rate}%</div><div class="stat-label">Conversion</div></div>
    `;
}
function renderFunnel(byStatus){
    const order=['discovered','verified','website_ready','deployed','outreach_sent','responded','interested','converted'];
    document.getElementById('funnel').innerHTML=order.map(s=>`
        <div class="funnel-step"><div class="count">${byStatus[s]||0}</div><div class="label">${s.replace('_',' ')}</div></div>
    `).join('');
}
function renderLeads(leads){
    document.getElementById('leads').innerHTML=leads.map(l=>`<tr>
        <td><strong>${l.business_name}</strong></td>
        <td>${l.business_type||'-'}</td>
        <td>${l.city||'-'}</td>
        <td><span class="badge badge-${l.status}">${l.status}</span></td>
        <td>${l.email||'-'}</td>
        <td>${l.preview_url?`<a class="link" href="${l.preview_url}" target="_blank">View</a>`:'-'}</td>
        <td>${l.rating||'-'}</td>
    </tr>`).join('');
}
function renderPipeline(runs){
    document.getElementById('pipeline').innerHTML=runs.slice(0,6).map(r=>`
        <div class="pipe-card">
            <div class="agent">${r.agent_name}</div>
            <div>${r.leads_succeeded}/${r.leads_processed} succeeded</div>
            <div class="meta">${r.status} &middot; ${new Date(r.started_at).toLocaleString('de')}</div>
        </div>
    `).join('');
}
loadAll();setInterval(loadAll,30000);
</script>
</body>
</html>"""
