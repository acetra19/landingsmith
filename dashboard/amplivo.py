"""
Amplivo.net landing page served via FastAPI.
Detected by Host header so it works on the same Railway app.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


def is_amplivo_host(request: Request) -> bool:
    host = request.headers.get("host", "")
    return "amplivo" in host.lower()


@router.get("/", response_class=HTMLResponse)
def amplivo_home(request: Request):
    if not is_amplivo_host(request):
        return None
    return AMPLIVO_HTML


AMPLIVO_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Amplivo - Moderne Websites fuer Ihr Unternehmen</title>
<meta name="description" content="Amplivo erstellt moderne, professionelle Websites fuer kleine und mittelstaendische Unternehmen. Kostenlose Erstberatung.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#050a18;
  --surface:rgba(255,255,255,0.04);
  --glass:rgba(255,255,255,0.06);
  --border:rgba(255,255,255,0.08);
  --text:#e8eaf0;
  --muted:#8892a8;
  --accent:#6366f1;
  --accent2:#06b6d4;
  --gradient:linear-gradient(135deg,#6366f1,#06b6d4);
  --gradient2:linear-gradient(135deg,#6366f1,#a855f7,#06b6d4);
}
html{scroll-behavior:smooth}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);
  overflow-x:hidden;line-height:1.6}

/* Animated background */
.bg-grid{position:fixed;inset:0;z-index:0;
  background-image:radial-gradient(rgba(99,102,241,0.08) 1px,transparent 1px);
  background-size:40px 40px}
.bg-glow{position:fixed;z-index:0;border-radius:50%;filter:blur(120px);opacity:0.3;pointer-events:none}
.bg-glow-1{width:600px;height:600px;background:#6366f1;top:-200px;right:-100px;animation:float 20s ease-in-out infinite}
.bg-glow-2{width:500px;height:500px;background:#06b6d4;bottom:-200px;left:-100px;animation:float 25s ease-in-out infinite reverse}
.bg-glow-3{width:400px;height:400px;background:#a855f7;top:50%;left:50%;transform:translate(-50%,-50%);animation:float 18s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-40px) scale(1.1)}}

.container{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:0 24px}

/* Nav */
nav{position:fixed;top:0;left:0;right:0;z-index:100;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  background:rgba(5,10,24,0.7);border-bottom:1px solid var(--border)}
nav .inner{max-width:1100px;margin:0 auto;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.logo{font-size:1.4rem;font-weight:800;background:var(--gradient);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;letter-spacing:-0.5px}
.nav-links{display:flex;gap:32px;list-style:none}
.nav-links a{color:var(--muted);text-decoration:none;font-size:.9rem;font-weight:500;
  transition:color .2s}
.nav-links a:hover{color:#fff}
.nav-cta{background:var(--gradient);color:#fff;padding:8px 22px;border-radius:8px;
  text-decoration:none;font-weight:600;font-size:.9rem;transition:opacity .2s}
.nav-cta:hover{opacity:.85}

/* Hero */
.hero{min-height:100vh;display:flex;align-items:center;padding:120px 0 80px}
.hero-content{max-width:700px}
.hero-badge{display:inline-flex;align-items:center;gap:8px;
  background:var(--glass);border:1px solid var(--border);border-radius:50px;
  padding:6px 18px;font-size:.8rem;color:var(--accent2);font-weight:500;margin-bottom:24px}
.hero-badge .dot{width:8px;height:8px;background:var(--accent2);border-radius:50%;
  animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.hero h1{font-size:clamp(2.5rem,6vw,4rem);font-weight:900;line-height:1.1;
  letter-spacing:-1.5px;margin-bottom:20px}
.hero h1 .gradient{background:var(--gradient2);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent}
.hero p{font-size:1.15rem;color:var(--muted);max-width:540px;margin-bottom:36px;line-height:1.7}
.hero-actions{display:flex;gap:16px;flex-wrap:wrap}
.btn-primary{background:var(--gradient);color:#fff;padding:14px 32px;border-radius:12px;
  text-decoration:none;font-weight:700;font-size:1rem;border:none;cursor:pointer;
  transition:transform .2s,box-shadow .2s;
  box-shadow:0 4px 30px rgba(99,102,241,0.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 40px rgba(99,102,241,0.4)}
.btn-secondary{background:var(--glass);color:var(--text);padding:14px 32px;border-radius:12px;
  text-decoration:none;font-weight:600;font-size:1rem;border:1px solid var(--border);
  transition:background .2s}
.btn-secondary:hover{background:rgba(255,255,255,0.1)}

/* Stats bar */
.stats-bar{display:flex;gap:48px;margin-top:60px;padding-top:40px;border-top:1px solid var(--border)}
.stat-item .num{font-size:2rem;font-weight:800;background:var(--gradient);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-item .label{font-size:.8rem;color:var(--muted);margin-top:2px}

/* Section shared */
section{padding:100px 0}
.section-label{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:2px;
  color:var(--accent);margin-bottom:12px}
.section-title{font-size:clamp(1.8rem,4vw,2.5rem);font-weight:800;letter-spacing:-1px;margin-bottom:16px}
.section-desc{color:var(--muted);max-width:560px;font-size:1.05rem;margin-bottom:48px}

/* Services */
.services-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.service-card{background:var(--glass);border:1px solid var(--border);border-radius:16px;
  padding:32px;transition:transform .3s,border-color .3s,background .3s;position:relative;overflow:hidden}
.service-card:hover{transform:translateY(-4px);border-color:rgba(99,102,241,0.3);
  background:rgba(99,102,241,0.06)}
.service-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--gradient);opacity:0;transition:opacity .3s}
.service-card:hover::before{opacity:1}
.service-icon{width:48px;height:48px;border-radius:12px;background:var(--gradient);
  display:flex;align-items:center;justify-content:center;font-size:1.4rem;margin-bottom:20px}
.service-card h3{font-size:1.15rem;font-weight:700;margin-bottom:10px}
.service-card p{color:var(--muted);font-size:.92rem;line-height:1.6}

/* Process */
.process-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px;counter-reset:step}
.step{position:relative;background:var(--glass);border:1px solid var(--border);
  border-radius:16px;padding:32px 24px;text-align:center;counter-increment:step}
.step::before{content:counter(step);font-size:3rem;font-weight:900;
  background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  opacity:.3;display:block;margin-bottom:12px}
.step h3{font-size:1rem;font-weight:700;margin-bottom:8px}
.step p{font-size:.85rem;color:var(--muted)}

/* CTA */
.cta-section{text-align:center;padding:100px 0}
.cta-box{background:var(--glass);border:1px solid var(--border);border-radius:24px;
  padding:60px 40px;position:relative;overflow:hidden}
.cta-box::before{content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(99,102,241,0.1),rgba(6,182,212,0.1));z-index:0}
.cta-box>*{position:relative;z-index:1}
.cta-box h2{font-size:clamp(1.8rem,4vw,2.5rem);font-weight:800;letter-spacing:-1px;margin-bottom:16px}
.cta-box p{color:var(--muted);font-size:1.05rem;max-width:480px;margin:0 auto 32px}
.cta-email{font-size:1.2rem;font-weight:700;color:var(--accent2)}
.cta-email a{color:var(--accent2);text-decoration:none}
.cta-email a:hover{text-decoration:underline}

/* Footer */
footer{border-top:1px solid var(--border);padding:40px 0;text-align:center;
  color:var(--muted);font-size:.85rem}
footer .logo-sm{font-weight:700;background:var(--gradient);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;font-size:1rem;margin-bottom:8px}

/* Mobile */
@media(max-width:768px){
  .nav-links{display:none}
  .stats-bar{flex-wrap:wrap;gap:24px}
  .hero h1{font-size:2.2rem}
  .hero-actions{flex-direction:column}
  .btn-primary,.btn-secondary{text-align:center}
}

/* Fade-in animation */
.fade-up{opacity:0;transform:translateY(30px);transition:opacity .6s ease,transform .6s ease}
.fade-up.visible{opacity:1;transform:translateY(0)}
</style>
</head>
<body>

<div class="bg-grid"></div>
<div class="bg-glow bg-glow-1"></div>
<div class="bg-glow bg-glow-2"></div>
<div class="bg-glow bg-glow-3"></div>

<nav>
  <div class="inner">
    <div class="logo">amplivo</div>
    <ul class="nav-links">
      <li><a href="#services">Services</a></li>
      <li><a href="#process">Ablauf</a></li>
      <li><a href="#contact">Kontakt</a></li>
    </ul>
    <a href="mailto:james@amplivo.net" class="nav-cta">Kontakt</a>
  </div>
</nav>

<section class="hero">
  <div class="container">
    <div class="hero-content">
      <div class="hero-badge"><span class="dot"></span> Jetzt kostenlos starten</div>
      <h1>Ihre <span class="gradient">digitale Praesenz</span> beginnt hier.</h1>
      <p>Wir erstellen moderne, professionelle Websites fuer kleine und mittelstaendische Unternehmen — schnell, unkompliziert und auf den Punkt.</p>
      <div class="hero-actions">
        <a href="mailto:james@amplivo.net" class="btn-primary">Kostenlose Beratung</a>
        <a href="#services" class="btn-secondary">Mehr erfahren</a>
      </div>
    </div>
    <div class="stats-bar">
      <div class="stat-item"><div class="num">50+</div><div class="label">Websites erstellt</div></div>
      <div class="stat-item"><div class="num">100%</div><div class="label">Zufriedenheit</div></div>
      <div class="stat-item"><div class="num">48h</div><div class="label">Lieferzeit</div></div>
    </div>
  </div>
</section>

<section id="services">
  <div class="container">
    <div class="fade-up">
      <div class="section-label">Services</div>
      <h2 class="section-title">Alles fuer Ihren Online-Auftritt</h2>
      <p class="section-desc">Von der ersten Idee bis zur fertigen Website — wir begleiten Sie auf dem gesamten Weg.</p>
    </div>
    <div class="services-grid">
      <div class="service-card fade-up">
        <div class="service-icon">&#x1f310;</div>
        <h3>Website-Erstellung</h3>
        <p>Moderne, responsive Websites die auf jedem Geraet perfekt aussehen. Schnell geladen, SEO-optimiert und individuell gestaltet.</p>
      </div>
      <div class="service-card fade-up">
        <div class="service-icon">&#x1f517;</div>
        <h3>Domain-Beratung</h3>
        <p>Wir finden die perfekte Domain fuer Ihr Unternehmen — einpraegsam, verfuegbar und passend zu Ihrer Marke.</p>
      </div>
      <div class="service-card fade-up">
        <div class="service-icon">&#x1f680;</div>
        <h3>Hosting & Wartung</h3>
        <p>Zuverlaessiges Hosting mit automatischen Updates. Ihre Website bleibt schnell, sicher und immer online.</p>
      </div>
      <div class="service-card fade-up">
        <div class="service-icon">&#x1f4c8;</div>
        <h3>Google-Sichtbarkeit</h3>
        <p>Werden Sie von Ihren Kunden gefunden. Wir optimieren Ihre Website fuer lokale Google-Suchen und Maps.</p>
      </div>
    </div>
  </div>
</section>

<section id="process">
  <div class="container">
    <div class="fade-up">
      <div class="section-label">So funktioniert's</div>
      <h2 class="section-title">In 4 Schritten online</h2>
      <p class="section-desc">Kein Technik-Wissen noetig. Wir kuemmern uns um alles.</p>
    </div>
    <div class="process-steps fade-up">
      <div class="step">
        <h3>Erstgespraech</h3>
        <p>Wir lernen Ihr Unternehmen kennen und besprechen Ihre Wuensche.</p>
      </div>
      <div class="step">
        <h3>Design & Inhalt</h3>
        <p>Unser Team erstellt einen massgeschneiderten Entwurf fuer Sie.</p>
      </div>
      <div class="step">
        <h3>Ihr Feedback</h3>
        <p>Sie pruefen die Website und wir passen alles nach Ihren Wuenschen an.</p>
      </div>
      <div class="step">
        <h3>Live schalten</h3>
        <p>Ihre neue Website geht online — mit eigener Domain und Hosting.</p>
      </div>
    </div>
  </div>
</section>

<section id="contact" class="cta-section">
  <div class="container">
    <div class="cta-box fade-up">
      <h2>Bereit fuer Ihre neue Website?</h2>
      <p>Schreiben Sie uns — die Erstberatung ist kostenlos und unverbindlich.</p>
      <a href="mailto:james@amplivo.net" class="btn-primary" style="display:inline-block;margin-bottom:20px">
        Jetzt anfragen
      </a>
      <div class="cta-email"><a href="mailto:james@amplivo.net">james@amplivo.net</a></div>
    </div>
  </div>
</section>

<footer>
  <div class="container">
    <div class="logo-sm">amplivo</div>
    <p>&copy; 2026 Amplivo. Alle Rechte vorbehalten.</p>
  </div>
</footer>

<script>
const obs = new IntersectionObserver((entries) => {
  entries.forEach(e => { if(e.isIntersecting) e.target.classList.add('visible') });
}, {threshold: 0.1});
document.querySelectorAll('.fade-up').forEach(el => obs.observe(el));
</script>
</body>
</html>"""
