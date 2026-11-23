# -*- coding: utf-8 -*-
"""F1 — izpeljava BOM iz sestava in delov (docs/f1-specifikacija.md, razdelek 3).

Vir: ``AssemblyDef.items`` + ``PartDef`` (polja po F0: ``mechanical/examples``).

Pravila izpeljave:

- vrstica = del (``part_ref``); količina = vsota instanc tega dela;
- ``find_no`` = pozicija instance; isti del z različnima pozicijama je
  nedvoumen → napaka (BOM se ne ugiba);
- vrstni red: izdelani (``custom``) → standardni, znotraj po ``find_no``;
- stolpci: poz. / kos / naziv / material / standard / opomba / masa;
- oznake: ``incomplete``/``placeholder`` → ``"placeholder/incomplete"``,
  standardni deli → ``"ob razrešitvi"``, izdelani → ``notes`` dela dobesedno.
"""


class NapakaBOM(Exception):
    """Sestav/deli so nepopolni ali nedvoumni — BOM se ne ugiba."""


def _deli_po_id(dok):
    """Indeks delov po ``id``; dvojniki ali deli brez id-ja so napaka."""
    deli = dok.get("parts")
    if not isinstance(deli, list) or not deli:
        raise NapakaBOM("dokument nima delov (`parts`)")
    po_id = {}
    for del_ in deli:
        if not isinstance(del_, dict) or not del_.get("id"):
            raise NapakaBOM("del brez `id` ni dopusten (BOM ga ne more navesti)")
        id_ = str(del_["id"])
        if id_ in po_id:
            raise NapakaBOM("dvojen `id` dela: %s" % id_)
        for obvezno in ("naziv", "source", "status"):
            if not del_.get(obvezno):
                raise NapakaBOM("del %s: manjka obvezno polje `%s`" % (id_, obvezno))
        po_id[id_] = del_
    return po_id


def _stolpec_standard(del_, id_):
    """Za standardni del: ``"<standard> <designation>"``; za izdelanega ``None``."""
    if del_.get("source") == "custom":
        return None
    ref = del_.get("standard_ref")
    if not isinstance(ref, dict) or not ref.get("standard") or not ref.get("designation"):
        raise NapakaBOM(
            "del %s: standardni del nima `standard_ref` (standard + designation)" % id_)
    return "%s %s" % (ref["standard"], ref["designation"])


def _stolpec_opomba(del_):
    """Oznaka vrstice po pravilih iz specifikacije (razdelek 3)."""
    if del_.get("status") in ("incomplete", "placeholder"):
        return "placeholder/incomplete"
    if del_.get("source") == "standard":
        return "ob razrešitvi"
    return del_.get("notes")


def izpelji_bom(dok):
    """Izpelji BOM iz ``parts`` + ``assembly.items``.

    Vrne ``{"source_assembly_ref": ..., "rows": [...]}``; vsaka vrstica ima
    polja ``find_no, part_ref, qty, name, material, standard, note, mass``.
    """
    po_id = _deli_po_id(dok)
    sestav = dok.get("assembly")
    if not isinstance(sestav, dict) or not sestav.get("items"):
        raise NapakaBOM("dokument nima sestava z instancami (`assembly.items`)")
    skupine: dict = {}
    for item in sestav["items"]:
        instanca = item.get("instance_id") or "?"
        ref = item.get("part_ref")
        if str(ref) not in po_id:
            raise NapakaBOM("instanca %s: `part_ref` %r ne obstaja" % (instanca, ref))
        kolicina = item.get("quantity")
        if not isinstance(kolicina, int) or isinstance(kolicina, bool) or kolicina < 1:
            raise NapakaBOM(
                "instanca %s: `quantity` mora biti celo število ≥ 1" % instanca)
        find_no = item.get("find_no")
        if not isinstance(find_no, int) or isinstance(find_no, bool):
            raise NapakaBOM("instanca %s: `find_no` mora biti celo število" % instanca)
        skupina = skupine.setdefault(str(ref), {"find_no": find_no, "qty": 0})
        if skupina["find_no"] != find_no:
            raise NapakaBOM(
                "del %s nastopa z različnima pozicijama (%s in %s) — BOM je nedvoumen"
                % (ref, skupina["find_no"], find_no))
        skupina["qty"] += kolicina

    def _vrstni_red(par):
        ref, skupina = par
        del_ = po_id[ref]
        return (del_.get("source") != "custom", skupina["find_no"])

    vrstice = []
    for ref, skupina in sorted(skupine.items(), key=_vrstni_red):
        del_ = po_id[ref]
        vrstice.append({
            "find_no": skupina["find_no"],
            "part_ref": ref,
            "qty": skupina["qty"],
            "name": del_.get("naziv"),
            "material": del_.get("material"),
            "standard": _stolpec_standard(del_, ref),
            "note": _stolpec_opomba(del_),
            "mass": del_.get("masa"),
        })
    return {"source_assembly_ref": sestav.get("id"), "rows": vrstice}


# angleška sopomenka po terminologiji specifikacije F1
derive_bom = izpelji_bom