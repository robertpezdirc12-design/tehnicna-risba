"""photo_fence_proposal — informativni izračun materiala, kosovnica in razrez.

SAMOSTOJNO: ne uvaža razrez.py/risba.py (issue #8 prepoveduje posege in
odvisnost od notranjosti obstoječega programa). Preprost, dokumentiran
hevristični razrez — informativne narave.

Pravilo poštenosti: če so mere NEZNANE, so tudi količine označene kot
INFORMATIVNE (status najšibkejše vpletene mere) — nikoli potrjene številke
iz negotovih vhodov.
"""
from __future__ import annotations

import math

from model import (PostavkaKosovnice, Rezultat, NEZNANO, OCENJENO, IZMERJENO, IZRACUNANO)

DOLZINA_PALICE_MM = 6000.0   # standardna nakupna dolžina WPC/alu palice
KERF_MM = 3.0                # širina reza (ocena)
MIN_OSTANKA_MM = 100.0       # ostanek pod to mejo se šteje za odpad


def _status_skupaj(*statusi: str) -> str:
    """Najšibkejši status vpletenih mer (NEZNANO > OCENJENO > ...)."""
    vrstni_red = [NEZNANO, OCENJENO, IZMERJENO, IZRACUNANO]
    for s in vrstni_red:
        if s in statusi:
            return s
    return NEZNANO


def izracunaj_material(rezultat: Rezultat) -> Rezultat:
    """Izpolni kosovnico, razrez in opozorila rezultata (na mestu)."""
    param = rezultat.parametri
    mere = rezultat.mere

    dolzina = mere.get("dolzina_ograje")
    visina = mere.get("visina_ograje")
    dolzina_mm = dolzina.vrednost_mm if dolzina else None
    visina_mm = visina.vrednost_mm if visina else None

    st_polj = mere.get("stevilo_polj")
    n_polj = int(st_polj.vrednost_mm) if st_polj and st_polj.vrednost_mm else None

    # --- lamel / desk ---
    if dolzina and visina and dolzina_mm and visina_mm:
        if param.tip == "wpc_vodoravne_lamele":
            korak = param.sirina_lamele_mm + param.razmak_mm
            st_lamel = max(1, int((visina_mm - 2 * param.sirina_lamele_mm)
                                  / korak) + 2)
            dolzina_kosa = dolzina_mm
        else:  # wpc_pokoncne_deske
            korak = param.sirina_lamele_mm + param.razmak_mm
            st_lamel = max(1, int(dolzina_mm / korak))
            dolzina_kosa = visina_mm
        status = _status_skupaj(dolzina.status, visina.status,
                                OCENJENO)  # širina lamele = ocenjena
        rezultat.kosovnica.append(PostavkaKosovnice(
            naziv="WPC lamela/deska", material="WPC lesni kompozit",
            dimenzija=f"{dolzina_kosa:.0f} mm", kolicina=float(st_lamel),
            enota="kos", status_mer=status,
            opomba=f"širina lamele {param.sirina_lamele_mm:.0f} mm = ocenjena"))
    else:
        rezultat.kosovnica.append(PostavkaKosovnice(
            naziv="WPC lamela/deska", material="WPC lesni kompozit",
            dimenzija="??", kolicina=0.0, enota="kos", status_mer=NEZNANO,
            opomba="mere ograje niso znane — količine ni mogoče izračunati"))
        rezultat.opozorila.append(
            "Količina lamel ni izračunana: dolžina in višina ograje nista "
            "znani (potrebna kalibracija ali ročni vnos).")

    # --- stebri ---
    if dolzina and dolzina_mm:
        # dolzina je tu zmeraj prisotna (dolzina_mm izhaja iz nje)
        # iz razmaka, če je znan, sicer iz dolžine/2000 mm hevristike
        razmak = mere.get("razmak_stebrov")
        if razmak and razmak.vrednost_mm:
            n_stebrov = n_polj + 1 if n_polj else max(
                2, int(math.ceil(dolzina_mm / razmak.vrednost_mm)) + 1)
            status_stebrov = _status_skupaj(razmak.status)
        else:
            n_stebrov = max(2, int(math.ceil(dolzina_mm / 2000.0)) + 1)
            status_stebrov = _status_skupaj(dolzina.status, OCENJENO)
        vis_stebra = (visina_mm + 200.0) if visina_mm else None
        # najšibkejši status: višina stebra je izpeljana iz višine ograje —
        # če višina ni znana, je tudi dimenzija stebra NEZNANA
        status_stebrov = _status_skupaj(
            status_stebrov,
            visina.status if (visina and vis_stebra is not None) else NEZNANO,
            OCENJENO)  # +200 mm betoniranje = ocena
        rezultat.kosovnica.append(PostavkaKosovnice(
            naziv="Steber", material="aluminij 60×40",
            dimenzija=f"{vis_stebra:.0f} mm" if vis_stebra else "??",
            kolicina=float(n_stebrov), enota="kos", status_mer=status_stebrov,
            opomba="višina stebra = višina ograje + 200 mm (betoniranje) — "
                   "ocena, če višina ni potrjena"))
    else:
        rezultat.kosovnica.append(PostavkaKosovnice(
            naziv="Steber", material="aluminij 60×40", dimenzija="??",
            kolicina=0.0, enota="kos", status_mer=NEZNANO,
            opomba="dolžina ograje ni znana"))

    # --- pritrdila (preprosto pravilo: 2 vijaka na stik lamele s stebrom) ---
    if dolzina and dolzina_mm and n_polj:
        # število stikov = število lamel × število polj (NE število vrstic
        # kosovnice — to je bil hrošč: množilo se je z 1)
        st_lamel_vijaki = int(next((p.kolicina for p in rezultat.kosovnica
                                    if p.naziv == "WPC lamela/deska"), 0))
        if st_lamel_vijaki > 0:
            vijaki = st_lamel_vijaki * n_polj * 2
            status_vijakov = _status_skupaj(
                dolzina.status,
                visina.status if (visina and visina.vrednost_mm) else NEZNANO,
                st_polj.status if st_polj else NEZNANO, OCENJENO)
            opomba_vijakov = ("2 vijaka na stik lamele s stebrom — "
                              "informativno pravilo")
        else:
            vijaki = 0
            status_vijakov = NEZNANO
            opomba_vijakov = ("število lamel ni znano (višina ograje) — "
                              "števila vijakov ni mogoče izračunati")
        rezultat.kosovnica.append(PostavkaKosovnice(
            naziv="Vijaki M8×70", material="inox", dimenzija="M8×70",
            kolicina=float(vijaki), enota="kos",
            status_mer=status_vijakov, opomba=opomba_vijakov))

    # --- razrez lamel na standardne palice (preprost FFD) ---
    if dolzina_mm and visina_mm:
        if param.tip == "wpc_vodoravne_lamele":
            dolz_kosa = dolzina_mm
        else:
            dolz_kosa = visina_mm
        st_lamel = next((int(p.kolicina) for p in rezultat.kosovnica
                         if p.naziv == "WPC lamela/deska"), 0)
        if dolz_kosa > DOLZINA_PALICE_MM:
            # kos ne gre v eno palico — enostavni model razreza ni veljaven;
            # NE izračunamo negativnega odpada, ampak pošteno opozorimo
            rezultat.opozorila.append(
                f"Kos {dolz_kosa:.0f} mm je daljši od standardne palice "
                f"{DOLZINA_PALICE_MM:.0f} mm — potrebno spajanje palic; "
                "informativni razrez in odpad nista izračunana.")
        elif st_lamel > 0:
            palice, odpad = _razrez_palic(st_lamel, dolz_kosa)
            rezultat.razrez = [{"palica_mm": DOLZINA_PALICE_MM,
                                "kosov": n, "dolzina_kosa_mm": dolz_kosa}
                               for n in palice]
            rezultat.odpad_mm = odpad
            rezultat.opozorila.append(
                f"Razrez je informativen (model reza: {dolz_kosa:.0f} mm + "
                f"{KERF_MM:.0f} mm kerf); dejanski razrez potrdi v proizvodnji.")

    if not rezultat.vse_kljucne_mere_potrjene:
        rezultat.opozorila.append(
            "Dokument NI pripravljen za izdelavo: ključne mere (dolžina/"
            "višina ograje) niso potrjene. Vse količine so informativne.")
    return rezultat


def _razrez_palic(st_kosov: int, dolzina_kosa: float
                  ) -> tuple[list[int], float]:
    """Koliko kosov gre v vsako palico (enake dolžine) + skupni odpad.

    Enostaven model: n kosov zasede n·dolžina + (n−1)·kerf; zadnji rez je na
    koncu palice in ne porabi materiala. Ves ostanek palic se šteje v odpad
    (informativno — del ostankov je lahko še uporaben).
    """
    if st_kosov <= 0:
        return [], 0.0
    if dolzina_kosa > DOLZINA_PALICE_MM:
        # kos daljši od palice: enostavni model bi dal NEGATIVEN odpad
        raise ValueError(
            f"Kos {dolzina_kosa:.0f} mm je daljši od palice "
            f"{DOLZINA_PALICE_MM:.0f} mm — potrebno spajanje palic")
    zmogljivost = int((DOLZINA_PALICE_MM + KERF_MM)
                      // (dolzina_kosa + KERF_MM))
    if zmogljivost < 1:
        zmogljivost = 1
    polne = st_kosov // zmogljivost
    ostanek_kosov = st_kosov % zmogljivost
    palice = [zmogljivost] * polne
    if ostanek_kosov:
        palice.append(ostanek_kosov)
    poraba = sum(n * dolzina_kosa + max(0, n - 1) * KERF_MM for n in palice)
    skupna_dolzina = len(palice) * DOLZINA_PALICE_MM
    odpad = skupna_dolzina - poraba
    return palice, odpad