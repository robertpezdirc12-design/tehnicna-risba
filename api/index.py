import os
import sys

os.environ["MPLCONFIGDIR"] = "/tmp/mplconfig"   # Vercel: pisanje samo v /tmp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import os
import sys
import tempfile
from html import escape as _esc
from time import time

from flask import Flask, request, send_file, Response, after_this_request

import yaml

import risba

app = Flask(__name__)

REPO = os.path.join(os.path.dirname(__file__), "..")

# --- varnost (issue #5, S3/S5): enostaven omejevalnik zahtevkov ----------
# Na Vercel serverless je to NAJBOLJŠE prizadevanje (pomnilnik ni deljen
# med instancami) — za trdno omejitev dodaj še Vercel WAF / edge rate limit.
_OMEJITEV = 10          # zahtevkov na minuto na IP (POST /generiraj)
_ZAPISKI = {}           # ip -> [časovni žigi]


def _prevec_zahtevkov(ip):
    zdaj = time()
    zigi = [t for t in _ZAPISKI.get(ip, []) if zdaj - t < 60.0]
    if len(zigi) >= _OMEJITEV:
        _ZAPISKI[ip] = zigi
        return True
    zigi.append(zdaj)
    _ZAPISKI[ip] = zigi
    return False


BLOKIRANI_UA = ("sqlmap", "nikto", "masscan", "zgrab", "curl/7.0")


def _dovoljen_ua():
    ua = (request.headers.get("User-Agent") or "").strip().lower()
    if not ua:                       # S5: prazen UA ni veljaven odjemalec
        return False
    return not any(vzorec in ua for vzorec in BLOKIRANI_UA)


def nalozi_cene():
    """cene.yaml v repozitoriju (javno!) — če ne obstaja, predračun ni na voljo."""
    pot = os.path.join(REPO, "cene.yaml")
    try:
        with open(pot, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def html_napake(napake):
    # S1/S2 (issue #5): sporočila se izpišejo ESKAPIRANA (brez XSS).
    sezn = "".join(f"<li>{_esc(str(n))}</li>" for n in napake)
    return Response(
        f"""<!DOCTYPE html><html lang="sl"><head><meta charset="utf-8">
        <title>Napaka pri vnosu</title>
        <style>body{{font-family:'Segoe UI',sans-serif;background:#f4f5f7;
        max-width:640px;margin:60px auto;padding:0 20px}}
        .box{{background:#fff;border:1px solid #e2e5ea;border-left:5px solid #b00020;
        border-radius:10px;padding:20px 24px}}
        h1{{color:#b00020;font-size:1.3rem}} ul{{margin:10px 0 0 18px}}
        a{{color:#1f2a3a}}</style></head><body><div class="box">
        <h1>Napaka pri vnosu</h1><p>PDF ni bil izdelan — popravi in poskusi znova:</p>
        <ul>{sezn}</ul>
        <p><a href="/app">← nazaj na obrazec</a></p></div></body></html>""",
        mimetype="text/html")


OBLRAZEC = """<!DOCTYPE html><html lang="sl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spletni generator — vpiši mere</title><style>
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f5f7;color:#1a1a1a;
line-height:1.5;margin:0} header{background:#1f2a3a;color:#fff;padding:22px 20px;
text-align:center} header h1{font-size:1.4rem;margin:0}
main{max-width:760px;margin:24px auto;padding:0 16px}
fieldset{background:#fff;border:1px solid #e2e5ea;border-radius:10px;
padding:14px 16px;margin-bottom:14px}
legend{font-weight:600;color:#1f2a3a;padding:0 8px}
label{display:block;font-size:.85rem;margin-top:8px;color:#333}
input,select{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;
font-size:.95rem;box-sizing:border-box}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
button{background:#2e7d32;color:#fff;border:none;border-radius:8px;
padding:12px 24px;font-size:1rem;font-weight:600;cursor:pointer;width:100%}
button:hover{background:#1b5e20}
.opomba{font-size:.78rem;color:#888}
.napaka{background:#fff3f3;border:1px solid #b00020;border-radius:8px;
padding:12px;color:#b00020;margin-bottom:14px}
a{color:#1f2a3a}
</style></head><body>
<header><h1>Spletni generator tehnične risbe</h1>
<p style="color:#c9d2e0;margin:6px 0 0">Vpiši mere → PDF (risba + montažni list
+ predračun) se prenese.</p></header>
<main>
{napaka}
<form action="/generiraj" method="post">
<fieldset><legend>PROJEKT</legend>
<label>Ime projekta:<input name="ime" value="BALKONSKA OGRAJA"></label>
<div class="grid">
<div><label>Številka risbe:<input name="risba_st" value="BO-001"></label></div>
<div><label>Izdelal:<input name="izdelal" value="R. Pezdirc"></label></div>
</div>
<label>Predloga:<select name="predloga">
<option value="ograja">ograja — lamele vodoravno</option>
<option value="pokončna">pokončna — deske navpično (stebri)</option>
</select></label>
<label>Profil / model deske (WoodCore):<input name="profil" value="ROMB 67"></label>
<label>Barva lamel:<select name="barva">
{barve}
<option value="Po dogovoru">Po dogovoru</option>
</select> <span class="opomba">(odtenek vedno potrdi s vzorcem proizvajalca)</span></label>
<label>Material profilov:<input name="material" value="Aluminij (prašno barvano)"></label>
<label>Material lamel:<input name="material_lamel" value="WPC lesni kompozit"></label>
<div class="grid">
<div><label>Dobavitelj:<input name="dobavitelj" value="WoodCore"></label></div>
</div>
<div class="grid">
<div><label>Podjetje:<input name="podjetje"></label></div>
<div><label>Pregledal:<input name="pregledal"></label></div>
<div><label>Odobril:<input name="odobril"></label></div>
</div>
<div class="grid">
<div><label>Naročnik / stranka:<input name="stranka"></label></div>
<div><label>Objekt (lokacija):<input name="objekt"></label></div>
</div>
</fieldset>

<fieldset><legend>MERE (mm)</legend>
<div class="grid">
<div><label>Širina ograje:<input name="sirina" value="3000"></label></div>
<div><label>Višina od tal do vrha:<input name="visina" value="1200"></label></div>
<div><label>Globina / stranska dolžina:<input name="globina" value="1200"></label></div>
</div>
<div class="grid">
<div><label>Število lamel / desk:<input name="lamele" value="13"></label></div>
<div><label>Višina lamel oz. širina desk:<input name="lamela_v" value="60"></label></div>
<div><label>Debelina lamel / desk:<input name="debelina" value="20"></label></div>
</div>
<div class="grid">
<div><label>Odcep od tal:<input name="odcep" value="60"></label></div>
<div><label>Razmak nosilcev oz. stebrov:<input name="razmak" value="1000"></label></div>
<div><label>Vrzel med deskami (samo pokončna):<input name="vrzel" value="20"></label></div>
</div>
<div class="grid">
<div><label>Kerf (širina rezila):<input name="kerf" value="3"></label></div>
<div><label>Dolžine desk v nabavi (mm, loči z ;):<input name="dolzine_deske" value="5800; 4000"></label></div>
</div>
<p class="opomba">(višina zgornjega/spodnjega profila je 40 mm; ročaj pri
pokončni 40 mm)</p>
</fieldset>

<fieldset><legend>PRITRDITEV</legend>
<div class="grid">
<div><label>Podlaga:<input name="podlaga" placeholder="npr. beton, zid, les"></label></div>
<div><label>Način pritrditve:<select name="pritrditev">
<option value="bočno">bočno (skoz)</option>
<option value="vrh">vrh (nosilec spredaj)</option>
</select></label></div>
</div>
<div><label>Vijak lamela↔profil:<input name="vijak_lamela" placeholder="npr. RF M8×70 Inox"></label></div>
<div><label>Vijak nosilec/osnova↔podlaga:<input name="vijak_nosilec" placeholder="npr. fasadni Ø8×80 + tipli / anker M10"></label></div>
<p class="opomba">(pritrdila so prosto besedilo — izpišejo se v potrebščinah,
naročilu in detajlih)</p>
</fieldset>

<fieldset><legend>PREDRAČUN</legend>
<label><input type="checkbox" name="predracun" value="da" style="width:auto">
vključi predračun (stran 3 — cene so nastavljene pri proizvajalcu strani)</label>
</fieldset>

<button type="submit">NARIŠI RISBO — PRENESI PDF</button>
<p class="opomba">Risba NI statični izračun — nosilnost, sidranje in veterno
breme preveri usposobljen strokovnjak. Odtenek WPC potrdi s vzorcem.</p>
<p><a href="/">← domača stran</a></p>
</main></body></html>"""


@app.route("/app")
def obrazec():
    barve = "".join(f'<option value="{v}">{v}</option>'
                    for v in risba.WPC_BARVE)
    napaka = request.args.get("napaka")
    # S1/S2 (issue #5): parametar 'napaka' je uporabniški vnos — ESKAPIRAJ!
    blok = (f'<div class="napaka"><b>Napaka:</b> {_esc(napaka)}</div>'
            if napaka else "")
    html = OBLRAZEC.replace("{napaka}", blok).replace("{barve}", barve)
    return Response(html, mimetype="text/html")


def _stev(f, kljuc, privzeto):
    raw = (f.get(kljuc) or "").strip().replace(",", ".")
    if not raw:
        return privzeto
    return float(raw)


def _dolzine(raw):
    """Dolžine desk iz vpisa ('5800; 4000') — seznam števil ali None."""
    vred = []
    for x in (raw or "").replace(";", ",").split(","):
        x = x.strip().replace(",", ".")
        if not x:
            continue
        try:
            vred.append(float(x))
        except ValueError:
            continue
    return vred or None


@app.route("/generiraj", methods=["POST"])
def generiraj_web():
    # S3/S5 (issue #5): omejitev zahtevkov + filtriranje odjemalcev.
    if not _dovoljen_ua():
        return Response("Prepovedano (neveljaven User-Agent).",
                        status=403, mimetype="text/plain")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
    ip = ip.split(",")[0].strip()
    if _prevec_zahtevkov(ip):
        return Response("Preveč zahtevkov — poskusi znova čez minuto.",
                        status=429, mimetype="text/plain",
                        headers={"Retry-After": "60"})
    f = request.form
    # vsak uporabnik dobi svojo začasno datoteko (sočasni uporabniki)
    fd_pdf, pdf_pot = tempfile.mkstemp(suffix=".pdf", prefix="risba_")
    os.close(fd_pdf)
    pok = (f.get("predloga") or "ograja").strip().lower() == "pokončna"
    try:
        m = {
            "sirina": _stev(f, "sirina", 3000),
            "visina": _stev(f, "visina", 1200),
            "odcep": _stev(f, "odcep", 60),
            "globina": _stev(f, "globina", 1200),
            "profil_v": 40.0,
            "lamele": int(_stev(f, "lamele", 13)),
            "lamela_v": _stev(f, "lamela_v", 60),
            "debelina": _stev(f, "debelina", 20),
            "razmak_nosilcev": _stev(f, "razmak", 1000),
            "deska_sirina": _stev(f, "lamela_v", 100),
            "deska_debelina": _stev(f, "debelina", 20),
            "vrzel": _stev(f, "vrzel", 20),
            "rocaj_v": 40.0,
            "razmak_stebrov": _stev(f, "razmak", 1500),
            "steber_sirina": 60.0,
            "steber_debelina": 40.0,
        }
        cfg = {
            "predloga": "pokončna" if pok else "ograja",
            "ime": (f.get("ime") or "BALKONSKA OGRAJA").strip(),
            "risba_st": (f.get("risba_st") or "BO-001").strip(),
            "izdelal": (f.get("izdelal") or "").strip(),
            "podjetje": (f.get("podjetje") or "").strip() or None,
            "pregledal": (f.get("pregledal") or "").strip() or None,
            "odobril": (f.get("odobril") or "").strip() or None,
            "stranka": (f.get("stranka") or "").strip() or None,
            "objekt": (f.get("objekt") or "").strip() or None,
            "datum": "", "merilo": "auto", "format": "A3",
            "izhod": pdf_pot, "foto": "",
            "barva": f.get("barva") or "Antracit",
            "profil": (f.get("profil") or ("POLNA DESKA 100" if pok
                        else "ROMB 67")).strip(),
            "material": (f.get("material") or "Aluminij (prašno barvano)").strip(),
            "material_lamel": (f.get("material_lamel")
                               or "WPC lesni kompozit").strip(),
            "dobavitelj": (f.get("dobavitelj") or "WoodCore").strip() or None,
            "podlaga": (f.get("podlaga") or "").strip() or None,
            "pritrditev": (f.get("pritrditev") or "bočno").strip(),
            "vijak_lamela": (f.get("vijak_lamela") or "").strip() or None,
            "vijak_nosilec": (f.get("vijak_nosilec") or "").strip() or None,
            "kerf": _stev(f, "kerf", 3.0),
            "dolzine_deske": _dolzine(f.get("dolzine_deske", "")),
            "deli": None, "opombe": None, "revizije": None,
            "mere": m,
        }
        if f.get("predracun") == "da":
            cene = nalozi_cene()
            if cene:
                cfg["cene"] = cene

        napake = risba.preveri_cfg(cfg)
        if napake:
            return html_napake(napake)

        risba.generiraj(cfg, dpi_png=80)
        varno = "".join(ch for ch in cfg["risba_st"]
                        if ch.isalnum() or ch in "-_") or "risba"
        # stranski izhodi (png/csv/txt) uporabnik prek spleta ne dobi —
        # po pošiljanju PDF jih počistimo iz /tmp
        osnova = os.path.splitext(pdf_pot)[0]
        brisi = [osnova + kon for kon in
                 ("-montazni-list.png", "-predracun.png", "-nalepke.png",
                  "-kosovnica.csv", "-narocilo.txt", ".png")]
        brisi = [p for p in brisi if os.path.isfile(p)]

        @after_this_request
        def pocisti(resp):
            for p in brisi:
                try:
                    os.remove(p)
                except OSError:
                    pass
            return resp

        return send_file(pdf_pot, mimetype="application/pdf",
                         as_attachment=True, download_name=f"{varno}.pdf")
    except ValueError as e:
        return html_napake([str(e)])
    except Exception as e:
        return html_napake([f"Nepričakovana napaka: {e}"])


@app.route("/")
def domaca():
    with open(os.path.join(REPO, "index.html"), encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")
