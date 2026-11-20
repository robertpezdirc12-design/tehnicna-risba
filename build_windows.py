# -*- coding: utf-8 -*-
"""Ponovljiv Windows build za TehnicnaRisba (issue #6, §9).

Uporaba:
    python build_windows.py            # zgradi dist/TehnicnaRisba.exe
    python build_windows.py --smoke    # zgradi + funkcionalni smoke test

Postopek (vsakič enak, dokumentiran):
  1. preveri različice orodja (Python, PyInstaller, PyInstaller spec),
  2. počisti prejšnje izide in zgradi EXE iz TehnicnaRisba.spec
     (onefile; UPX se uporabi, če je nameščen — sicer ga PyInstaller preskoči),
  3. izračuna SHA-256 in velikost izida,
  4. z --smoke zažene EXE v neinteraktivnem načinu
     (``--brez-zaslona``) z začasno konfiguracijo in preveri,
     da je PDF nastal in vsebuje pričakovano število strani.

IZDAJA NI DEL TEGA SKRIPTE: EXE ostane v dist/ in ga je treba
objaviti šele po potrditvi rešitve (issue #6, korak 10).

Ponovljivost: postopek in različice so zapisani v build-zapisnik.json.
Bit-identičen izid ni zagotovljen (PyInstaller v PE zapisuje časovne
žige) — ponovljivost pomeni: isti koraki + iste različice → delujoč EXE
z enako funkcionalnostjo; razliko v hashu povzročajo časovni žigi.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

KOREN = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(KOREN, "TehnicnaRisba.spec")
DIST = os.path.join(KOREN, "dist")
EXE = os.path.join(DIST, "TehnicnaRisba.exe")
ZAPISNIK = os.path.join(KOREN, "build-zapisnik.json")

SMOKE_CFG = {
    "ime": "BUILD SMOKE", "risba_st": "SMOKE-001",
    "izhod": "",  # zapolni se ob zagonu
    "predloga": "ograja", "barva": "Antracit", "profil": "ROMB 67",
    "dolzina_deske": 5800, "dolzina_palice": 6000, "kerf": 3.0,
    "uporabi_ostanke": False,
    "mere": {"sirina": 2500, "visina": 1850, "globina": 40, "odcep": 250,
             "lamela_v": 120, "lamele": 11, "vrzel": 30, "profil_v": 80,
             "rocaj_v": 40, "debelina": 21, "steber_sirina": 60,
             "steber_debelina": 60, "deska_sirina": 100, "deska_debelina": 21,
             "razmak_nosilcev": 1000, "razmak_stebrov": 1200},
}


def git_stanje():
    """Commit/veja/dirty — sledljivost artefakta (issue #6, pod-agent 4)."""
    def _pozeni(*arg):
        try:
            return subprocess.run(arg, cwd=KOREN, capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    return {"commit": _pozeni("git", "rev-parse", "HEAD"),
            "veja": _pozeni("git", "rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_pozeni("git", "status", "--porcelain"))}


def razlicice():
    import PyInstaller
    return {
        "python": sys.version.split()[0],
        "pyinstaller": PyInstaller.__version__,
        "platform": sys.platform,
        "upx": bool(__import__("shutil").which("upx")),
    }


def sha256(pot):
    h = hashlib.sha256()
    with open(pot, "rb") as f:
        for delcek in iter(lambda: f.read(1 << 20), b""):
            h.update(delcek)
    return h.hexdigest()


def zgradi():
    if not os.path.isfile(SPEC):
        sys.exit(f"Spec ni najden: {SPEC}")
    ukaz = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", SPEC]
    print("Gradim:", " ".join(ukaz))
    subprocess.run(ukaz, check=True, cwd=KOREN)
    if not os.path.isfile(EXE):
        sys.exit("EXE ni nastal.")
    return {"exe": EXE, "velikost_b": os.path.getsize(EXE), "sha256": sha256(EXE)}


def smoke():
    """Funkcionalni preizkus zgrajenega programa (neinteraktivni način)."""
    delo = tempfile.mkdtemp(prefix="tr_smoke_")
    pdf = os.path.join(delo, "smoke.pdf")
    cfg = dict(SMOKE_CFG, izhod=pdf)
    cfg_pot = os.path.join(delo, "smoke.json")
    with open(cfg_pot, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)
    # hermetično: podatke (ostanki ipd.) v začasno mapo, ne v uporabniško
    env = dict(os.environ, TEHNICNA_RISBA_HEADLESS="1",
               TEHNICNA_RISBA_DATA=os.path.join(delo, "data"))
    # 1) preklop prek okoljske spremenljivke (kot zahteva §9)
    koda = subprocess.run([EXE, cfg_pot], env=env, cwd=delo,
                          capture_output=True, text=True, timeout=300).returncode
    if koda != 0:
        sys.exit(f"Smoke (env način) ni uspel, izhodna koda {koda}.")
    # 2) preklop prek stikala
    koda = subprocess.run([EXE, "--brez-zaslona", cfg_pot], env=env, cwd=delo,
                          capture_output=True, text=True, timeout=300).returncode
    if koda != 0:
        sys.exit(f"Smoke (--brez-zaslona) ni uspel, izhodna koda {koda}.")
    if not os.path.isfile(pdf):
        sys.exit("Smoke: PDF ni nastal.")
    from pypdf import PdfReader
    strani = len(PdfReader(pdf).pages)
    # privzeta konfiguracija (brez 'cene') daje 3 strani: risba, montažni, nalepke
    if strani != 3:
        sys.exit(f"Smoke: PDF ima {strani} strani (pričakovano 3).")
    return {"pdf": pdf, "strani": strani, "velikost_b": os.path.getsize(pdf),
            "nacini": ["TEHNICNA_RISBA_HEADLESS=1", "--brez-zaslona"]}


if __name__ == "__main__":
    zac = time.time()
    zapisnik = {"zapisnik_verzija": 1,
                "zacetek": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " UTC",
                "razlicice": razlicice(), "git": git_stanje(),
                "spec_sha256": sha256(SPEC),
                "ukaz": "python build_windows.py --smoke"}
    zapisnik["build"] = zgradi()
    if "--smoke" in sys.argv:
        zapisnik["smoke"] = smoke()
    zapisnik["trajanje_s"] = round(time.time() - zac, 1)
    with open(ZAPISNIK, "w", encoding="utf-8") as f:
        json.dump(zapisnik, f, ensure_ascii=False, indent=2)
    print(json.dumps(zapisnik, ensure_ascii=False, indent=2))