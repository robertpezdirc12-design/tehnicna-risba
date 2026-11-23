# -*- coding: utf-8 -*-
"""F1 — kontrola dokumenta (validate): popolnost, reference, standardi, enote, gating.

``preveri(dok)`` vrne poročilo, ki gre naravnost v JSON
(``json.dumps(porocilo, ensure_ascii=False)``) in ima človeško berljiv izpis
(``pripis_clovek``). Vse napake so eksplicitne — nobene tihe domneve.

Gating (docs/f0-specifikacija.md):

- ``complete``    → detajl dovoljen;
- ``incomplete``  → detajl blokiran; v sestavu le z eksplicitnim placeholderjem
  (``item.placeholder: true`` ali ``item.overrides.placeholder: true``);
- ``placeholder`` → vidno označen (ne nadomešča manjkajoče geometrije).

Uporaba z ukazno vrstico::

    python -m mechanical.kontrola mechanical/examples/vijacnik.yaml
    python -m mechanical.kontrola --json mechanical/examples/vijacnik.yaml
"""
import json
import sys

import yaml

from .bom import NapakaBOM, izpelji_bom
from .resolver import PROFILI, NapakaKataloga, razresi

DOVOLJENI_STATUSI = ("complete", "incomplete", "placeholder")

# status → dovoljenje detajla (gating matrika iz F0)
GATING_PO_STATUSU = {
    "complete": "dovoljen",
    "incomplete": "blokiran",
    "placeholder": "oznacen",
}


def nalozi_dokument(pot):
    """Naloži YAML dokument (F0 shema) v slovar."""
    with open(pot, encoding="utf-8") as dat:
        return yaml.safe_load(dat) or {}


# ---------- posamezne kontrole ----------

def _kontrola_geometrije(del_, id_, naziv, status, napake, opozorila):
    """Kontrola ``GeometryDef`` custom dela; vrne ugotovljena manjkajoča polja."""
    najdeno: list = []
    geometrija = del_.get("geometry")
    if not isinstance(geometrija, dict):
        if status == "complete":
            napake.append(
                "del %s (%s): status complete, a manjka `geometry`" % (id_, naziv))
        else:
            najdeno.extend(("gabariti", "datum/csys"))
        return najdeno
    parametri = geometrija.get("parametri") or {}
    if not isinstance(parametri, dict) or not parametri:
        najdeno.append("gabariti")
        if status == "complete":
            napake.append(
                "del %s (%s): status complete, a `parametri` so prazni" % (id_, naziv))
    else:
        for ime, parameter in parametri.items():
            if not isinstance(parameter, dict) or parameter.get("vrednost") is None:
                napake.append(
                    "del %s (%s): parameter %r nima `vrednost`" % (id_, naziv, ime))
                continue
            enota = parameter.get("enota")
            if not enota:
                napake.append(
                    "del %s (%s): parameter %r nima `enota` (zahtevano mm)"
                    % (id_, naziv, ime))
            elif enota != "mm":
                napake.append(
                    "del %s (%s): parameter %r ima enoto %r — pričakovana mm"
                    % (id_, naziv, ime, enota))
    if geometrija.get("datum") is None and geometrija.get("csys") is None:
        najdeno.append("datum/csys")
    return najdeno


def _kontrola_standarda(del_, id_, naziv, profil_dok, napake, opozorila, standardi):
    """Kontrola ``StandardRef``: razrešitev preko resolverja, dolžina, ključ."""
    ref = del_.get("standard_ref")
    zap = {"standard": None, "designation": None, "profil": None,
           "razreseno": False, "dimenzije": None, "provenenca": None}
    standardi[id_] = zap
    if not isinstance(ref, dict):
        napake.append("del %s (%s): standardni del nima `standard_ref`" % (id_, naziv))
        return
    standard = ref.get("standard")
    designation = ref.get("designation")
    zap["standard"], zap["designation"] = standard, designation
    if not standard or not designation:
        napake.append(
            "del %s (%s): `standard_ref` potrebuje `standard` in `designation`"
            % (id_, naziv))
        return
    profil = ref.get("profil") or profil_dok
    zap["profil"] = profil
    if not profil:
        napake.append(
            "del %s (%s): manjka profil kataloga (`standard_ref.profil` ali "
            "`document_set.profil_kataloga`)" % (id_, naziv))
        return
    if ref.get("profil") and profil_dok and ref["profil"] != profil_dok:
        napake.append(
            "del %s (%s): profil %r se ne ujema z `document_set.profil_kataloga` %r "
            "(profila `iso` in `legacy_din` se ne mešata)"
            % (id_, naziv, ref["profil"], profil_dok))
        return
    try:
        vrstica = razresi(designation, standard, profil)
    except NapakaKataloga as napaka:
        napake.append("del %s (%s): standard ni razrešen — %s" % (id_, naziv, napaka))
        return
    zap["razreseno"] = True
    zap["dimenzije"] = vrstica["dimenzije"]
    zap["provenenca"] = vrstica["provenenca"]
    dolzina = ref.get("length")
    dolzina_katalog = vrstica.get("length_mm")
    if dolzina is not None and dolzina_katalog is not None and dolzina != dolzina_katalog:
        napake.append(
            "del %s (%s): `standard_ref.length` %s ne ustreza katalogu (%s)"
            % (id_, naziv, dolzina, dolzina_katalog))
    kljuc = ref.get("catalog_key")
    if kljuc:
        pricakovano = "%s/%s/%s" % (profil, str(standard).replace(" ", "_"), designation)
        if kljuc != pricakovano:
            opozorila.append(
                "del %s (%s): `catalog_key` %r se ne ujema s konvencijo %r"
                % (id_, naziv, kljuc, pricakovano))


def _kontrola_sestava(dok, po_id, napake):
    """Kontrola ``AssemblyDef``: reference, količine, pozicije, placeholder marking."""
    sestav = dok.get("assembly")
    if not isinstance(sestav, dict) or not sestav.get("items"):
        napake.append("dokument nima sestava (`assembly.items`)")
        return {}
    if not sestav.get("id"):
        napake.append("assembly: manjka `id`")
    zasedene_pozicije: dict = {}
    for item in sestav["items"]:
        instanca = item.get("instance_id") or "?"
        ref = str(item.get("part_ref"))
        if ref not in po_id:
            napake.append("instanca %s: `part_ref` %r ne obstaja" % (instanca, ref))
            continue
        kolicina = item.get("quantity")
        if not isinstance(kolicina, int) or isinstance(kolicina, bool) or kolicina < 1:
            napake.append(
                "instanca %s: `quantity` mora biti celo število ≥ 1" % instanca)
        find_no = item.get("find_no")
        if not isinstance(find_no, int) or isinstance(find_no, bool):
            napake.append("instanca %s: `find_no` mora biti celo število" % instanca)
        else:
            prejsnji = zasedene_pozicije.setdefault(find_no, ref)
            if prejsnji != ref:
                napake.append(
                    "instanca %s: `find_no` %s je že uporabljen za del %r"
                    % (instanca, find_no, prejsnji))
        del_ = po_id[ref]
        status = del_.get("status")
        if status == "placeholder":
            continue  # del je sam po sebi vidno označen
        if status == "incomplete":
            oznaceno = item.get("placeholder") is True or \
                (item.get("overrides") or {}).get("placeholder") is True
            if not oznaceno:
                napake.append(
                    "instanca %s (poz. %s, %s): status incomplete brez eksplicitnega "
                    "placeholderja (`placeholder: true` ali `overrides.placeholder: true`)"
                    % (instanca, find_no, del_.get("naziv")))
    return sestav


def _kontrola_listov(dok, napake, opozorila):
    """Kontrola ``DrawingSheet``: številke listov in sklici na BOM."""
    listi = dok.get("drawing_sheets")
    if listi is None:
        return
    if not isinstance(listi, list):
        napake.append("drawing_sheets: pričakovan seznam listov")
        return
    bom = dok.get("bom")
    bom_id = bom.get("id") if isinstance(bom, dict) else None
    for list_ in listi:
        oznaka = list_.get("id") or "?"
        st = list_.get("sheet_no")
        skupaj = list_.get("sheet_total")
        if not isinstance(st, int) or not isinstance(skupaj, int):
            napake.append("list %s: `sheet_no`/`sheet_total` morata biti celi števili"
                          % oznaka)
        elif not (1 <= st <= skupaj):
            napake.append("list %s: številka %s je zunaj 1…%s" % (oznaka, st, skupaj))
        bom_ref = (list_.get("tables") or {}).get("bom_ref")
        if bom_ref:
            if bom_id is None:
                opozorila.append(
                    "list %s: `bom_ref` %r ni preverljiv — `bom.id` manjka"
                    % (oznaka, bom_ref))
            elif bom_ref != bom_id:
                napake.append(
                    "list %s: `bom_ref` %r ne ustreza `bom.id` %r"
                    % (oznaka, bom_ref, bom_id))


# ---------- glavna kontrola ----------

def preveri(dok):
    """Preveri dokument F0 sheme in vrni poročilo (JSON-prijazno).

    Poročilo: ``ok``, ``dokument``, ``napake``, ``opozorila``, ``deli``
    (status / manjkajoča polja / dovoljenje detajla), ``standardi``
    (rezultat resolverja + provenenca) in ``gating``.
    """
    napake: list = []
    opozorila: list = []
    deli_poro: dict = {}
    standardi: dict = {}
    gating: dict = {"detajl_dovoljen": [], "detajl_blokiran": [],
                    "oznaceni_placeholder": []}

    if not isinstance(dok, dict) or not dok:
        napake.append("dokument je prazen ali ni YAML objekt")
        return _sestavi_porocilo(None, {}, napake, opozorila, deli_poro,
                                 standardi, gating)

    ds = dok.get("document_set") or {}
    profil_dok = ds.get("profil_kataloga")
    if not ds.get("stevilka"):
        napake.append("document_set: manjka `stevilka`")
    if not ds.get("revizija"):
        napake.append("document_set: manjka `revizija`")
    if not profil_dok:
        napake.append("document_set: manjka `profil_kataloga`")
    elif profil_dok not in PROFILI:
        napake.append(
            "document_set: neznan `profil_kataloga` %r (dovoljena: %s)"
            % (profil_dok, ", ".join(PROFILI)))

    deli = dok.get("parts")
    if not isinstance(deli, list) or not deli:
        napake.append("dokument nima delov (`parts`)")
        deli = []
    po_id = {}
    for del_ in deli:
        if not isinstance(del_, dict) or not del_.get("id"):
            napake.append("del brez `id` ni dopusten")
            continue
        id_ = str(del_["id"])
        if id_ in po_id:
            napake.append("del %s: dvojen `id`" % id_)
            continue
        po_id[id_] = del_

    for id_, del_ in po_id.items():
        naziv = del_.get("naziv") or ""
        status = del_.get("status")
        vir = del_.get("source")
        if status not in DOVOLJENI_STATUSI:
            napake.append("del %s (%s): neveljaven `status` %r (dovoljeni: %s)"
                          % (id_, naziv, status, ", ".join(DOVOLJENI_STATUSI)))
        if vir not in ("custom", "standard"):
            napake.append(
                "del %s (%s): `source` mora biti `custom` ali `standard` (dano: %r)"
                % (id_, naziv, vir))
        najdeno: list = []
        if vir == "custom":
            najdeno = _kontrola_geometrije(del_, id_, naziv, status,
                                          napake, opozorila)
        elif vir == "standard":
            _kontrola_standarda(del_, id_, naziv, profil_dok,
                                napake, opozorila, standardi)
        naroceno = list(del_.get("manjkajoce") or [])
        for polje in najdeno:
            if polje not in naroceno and status == "complete":
                opozorila.append(
                    "del %s (%s): status complete, a manjka %s "
                    "(ni navedeno v `manjkajoce`)" % (id_, naziv, polje))
        if status == "incomplete" and not naroceno and not najdeno:
            opozorila.append(
                "del %s (%s): status incomplete brez navedenih manjkajočih polj"
                % (id_, naziv))
        detajl = GATING_PO_STATUSU.get(str(status), "blokiran")
        deli_poro[id_] = {
            "naziv": naziv,
            "status": status,
            "manjkajoce": naroceno,
            "ugotovljeno": [p for p in najdeno if p not in naroceno],
            "detajl": detajl,
        }
        if detajl == "dovoljen":
            gating["detajl_dovoljen"].append(id_)
        else:
            gating["detajl_blokiran"].append(id_)
        if status in ("incomplete", "placeholder"):
            gating["oznaceni_placeholder"].append(id_)

    sestav = _kontrola_sestava(dok, po_id, napake)

    bom = dok.get("bom")
    if isinstance(bom, dict):
        sestav_ref = bom.get("source_assembly_ref")
        if sestav and sestav_ref and sestav_ref != sestav.get("id"):
            napake.append(
                "bom: `source_assembly_ref` %r ne ustreza sestavu %r"
                % (sestav_ref, sestav.get("id")))
    elif bom is not None:
        napake.append("bom: pričakovan objekt (ali brez bloka)")

    _kontrola_listov(dok, napake, opozorila)

    # konsistenca: izpeljani BOM proti ročno zapisanemu (če je zapisan)
    if isinstance(bom, dict) and bom.get("rows") is not None and sestav:
        try:
            izpeljan = izpelji_bom(dok)
        except NapakaBOM as napaka:
            napake.append("bom: izpeljava ni mogoča — %s" % napaka)
        else:
            if izpeljan["rows"] != bom["rows"]:
                opozorila.append(
                    "bom: ročno zapisane vrstice se ne ujemajo z izpeljanimi "
                    "(priporočeno: uporabi izpeljani BOM)")

    for kljuc in ("detajl_dovoljen", "detajl_blokiran", "oznaceni_placeholder"):
        gating[kljuc] = _uredi(gating[kljuc])
    return _sestavi_porocilo(ds, dok, napake, opozorila, deli_poro, standardi, gating)


def _uredi(oznake):
    """Naravni vrstni red oznak ("2" pred "10")."""
    return sorted(oznake, key=lambda o: (len(o), o))


def _sestavi_porocilo(ds, dok, napake, opozorila, deli_poro, standardi, gating):
    ds = ds or {}
    return {
        "ok": not napake,
        "dokument": {
            "stevilka": ds.get("stevilka"),
            "revizija": ds.get("revizija"),
            "profil_kataloga": ds.get("profil_kataloga"),
            "sestav": (dok.get("assembly") or {}).get("id") if isinstance(dok, dict)
                      else None,
        },
        "napake": napake,
        "opozorila": opozorila,
        "deli": deli_poro,
        "standardi": standardi,
        "gating": gating,
    }


# ---------- človeško berljiv izpis ----------

def pripis_clovek(porocilo):
    """Človeško berljiv izpis poročila :func:`preveri`."""
    dok = porocilo["dokument"]
    vrstice = [
        "Kontrola dokumenta %s rev. %s — profil kataloga: %s"
        % (dok.get("stevilka") or "?", dok.get("revizija") or "?",
           dok.get("profil_kataloga") or "?"),
        "napake: %d | opozorila: %d"
        % (len(porocilo["napake"]), len(porocilo["opozorila"])),
        "",
    ]
    if porocilo["deli"]:
        vrstice.append("deli:")
        for id_, zap in porocilo["deli"].items():
            vrstice.append("  %s %s [%s] — detajl: %s"
                           % (id_, zap["naziv"], zap["status"],
                              zap["detajl"].upper()))
            if zap["manjkajoce"]:
                vrstice.append("     manjka: %s" % ", ".join(zap["manjkajoce"]))
            if zap["ugotovljeno"]:
                vrstice.append("     ugotovljeno manjkajoče: %s"
                               % ", ".join(zap["ugotovljeno"]))
        vrstice.append("")
    if porocilo["standardi"]:
        vrstice.append("standardi:")
        for id_, zap in porocilo["standardi"].items():
            stanje = "razrešeno" if zap["razreseno"] else "NI razrešeno"
            viri = ", ".join(v.get("name") or "?" for v in (zap.get("provenenca") or []))
            vrstice.append("  %s %s %s (%s): %s%s"
                           % (id_, zap["standard"], zap["designation"], zap["profil"],
                              stanje, (" — vir: " + viri) if viri else ""))
        vrstice.append("")
    gating = porocilo["gating"]
    vrstice.append("gating:")
    vrstice.append("  detajl dovoljen: %s"
                   % (", ".join(gating["detajl_dovoljen"]) or "—"))
    vrstice.append("  detajl blokiran: %s"
                   % (", ".join(gating["detajl_blokiran"]) or "—"))
    vrstice.append("  placeholder (označeno): %s"
                   % (", ".join(gating["oznaceni_placeholder"]) or "—"))
    vrstice.append("")
    vrstice.append("napake: %s" % ("; ".join(porocilo["napake"]) or "(ni)"))
    vrstice.append("opozorila: %s" % ("; ".join(porocilo["opozorila"]) or "(ni)"))
    return "\n".join(vrstice)


# angleška sopomenka po terminologiji specifikacije F1
validate = preveri


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Kontrola F0 dokumenta (popolnost, reference, standardi, gating).")
    parser.add_argument("dokument", help="pot do YAML dokumenta (npr. vijacnik.yaml)")
    parser.add_argument("--json", action="store_true",
                        help="izpiši poročilo v JSON namesto v berljivi obliki")
    argumenti = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # dosleden UTF-8 izpis tudi na Windows
    try:
        porocilo = preveri(nalozi_dokument(argumenti.dokument))
    except (OSError, yaml.YAMLError, NapakaBOM) as napaka:
        sys.stderr.write("NAPAKA: %s\n" % napaka)
        sys.exit(2)
    if argumenti.json:
        sys.stdout.write(json.dumps(porocilo, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(pripis_clovek(porocilo) + "\n")
    sys.exit(0 if porocilo["ok"] else 1)