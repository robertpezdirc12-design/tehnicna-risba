# -*- coding: utf-8 -*-
"""Podatkovni razredi ocenjevalnika (brez vedenja, le struktura)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Statusi izida posamezne naloge — imena so del zapisa rezultatov,
# zato jih ne preimenujemo brez migracije.
RESEN = "resen"                        # FAIL_TO_PASS + PASS_TO_PASS OK
NI_RESEN = "ni_resen"                  # FAIL_TO_PASS ni uspelo
POKVARJEN = "pokvarjen"                # PASS_TO_PASS je regresiral
PREKORACEN_CAS = "prekoracen_cas"       # agent ali testi so presegli čas
NAPAKA_OKOLJA = "napaka_okolja"        # naloge ni bilo mogoče izvesti
ONESNAZENO = "onesnazeno"              # canary zadet → rezultat ni veljaven

STATUSI = (RESEN, NI_RESEN, POKVARJEN, PREKORACEN_CAS, NAPAKA_OKOLJA,
           ONESNAZENO)


@dataclass(frozen=True)
class Naloga:
    """Ena merljiva naloga: poziv + skriti testi + pričakovani prehod."""

    id: str
    opis: str
    predloga: str                      # imenik delovnega prostora (relativno)
    fail_to_pass: tuple[str, ...]      # testi, ki morajo postati zeleni
    pass_to_pass: tuple[str, ...]      # testi, ki morajo ostati zeleni
    cas_s: float = 120.0
    canary: tuple[str, ...] = ()
    ukaz_testov: tuple[str, ...] = ()  # privzeto: pytest skriti_testi
    opombe: str = ""


@dataclass
class RezultatNaloge:
    """Izid ene naloge: vse, kar je mogoče preveriti strojno."""

    naloga: str
    status: str
    fail_to_pass_ok: list[str] = field(default_factory=list)
    fail_to_pass_napaka: list[str] = field(default_factory=list)
    pass_to_pass_ok: list[str] = field(default_factory=list)
    pass_to_pass_napaka: list[str] = field(default_factory=list)
    manjkajoci_testi: list[str] = field(default_factory=list)
    canary_zadet: list[str] = field(default_factory=list)
    cas_agenta_s: float = 0.0
    cas_testov_s: float = 0.0
    izhod_agenta: int | None = None
    sporočilo: str = ""

    @property
    def uspesna(self) -> bool:
        return self.status == RESEN

    def v_slovar(self) -> dict[str, Any]:
        return {
            "naloga": self.naloga,
            "status": self.status,
            "uspesna": self.uspesna,
            "fail_to_pass_ok": self.fail_to_pass_ok,
            "fail_to_pass_napaka": self.fail_to_pass_napaka,
            "pass_to_pass_ok": self.pass_to_pass_ok,
            "pass_to_pass_napaka": self.pass_to_pass_napaka,
            "manjkajoci_testi": self.manjkajoci_testi,
            "canary_zadet": self.canary_zadet,
            "cas_agenta_s": round(self.cas_agenta_s, 3),
            "cas_testov_s": round(self.cas_testov_s, 3),
            "izhod_agenta": self.izhod_agenta,
            "sporočilo": self.sporočilo,
        }

    @classmethod
    def iz_slovarja(cls, podatek: dict[str, Any]) -> RezultatNaloge:
        return cls(
            naloga=str(podatek.get("naloga", "")),
            status=str(podatek.get("status", NAPAKA_OKOLJA)),
            fail_to_pass_ok=list(podatek.get("fail_to_pass_ok") or []),
            fail_to_pass_napaka=list(podatek.get("fail_to_pass_napaka") or []),
            pass_to_pass_ok=list(podatek.get("pass_to_pass_ok") or []),
            pass_to_pass_napaka=list(podatek.get("pass_to_pass_napaka") or []),
            manjkajoci_testi=list(podatek.get("manjkajoci_testi") or []),
            canary_zadet=list(podatek.get("canary_zadet") or []),
            cas_agenta_s=float(podatek.get("cas_agenta_s") or 0.0),
            cas_testov_s=float(podatek.get("cas_testov_s") or 0.0),
            izhod_agenta=podatek.get("izhod_agenta"),
        )


@dataclass
class RezultatSerije:
    """Rezultati ene ponovitve za en »agent« (model + nastavitve)."""

    agent: str
    ponovitev: int
    zrno: int
    rezultati: list[RezultatNaloge] = field(default_factory=list)

    def v_slovar(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "ponovitev": self.ponovitev,
            "zrno": self.zrno,
            "rezultati": [r.v_slovar() for r in self.rezultati],
        }
