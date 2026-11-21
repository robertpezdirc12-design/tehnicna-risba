# Plan 4 — Teme (ttkbootstrap) + temni način

## Vir (raziskava)
- ttkbootstrap: tematska plast za tkinter BREZ prepisa — `bootstyle`
  ključne besede, svetle/temne teme, preklop med tekom aplikacije.

## Spremembe
- `vmesnik.py`: ob zagonu poskusi `import ttkbootstrap` in uporabi temo
  `bootstrap-light`; gumb **◐ Tema** preklopi `bootstrap-dark` ↔
  `bootstrap-light`. **Brez paketa aplikacija deluje naprej** z
  privzetim videzom in poštenim sporočilom v statusu.
- `requirements.txt`: +ttkbootstrap (označeno kot neobvezno).

## Pasti, ki so se pokazale med testiranjem
- ttkbootstrap 2.x ima **singleton `Style`**, ki drži referenco na root
  okno; po uničenju prvega okna (testi!) drugo okno dobi `TclError:
  application has been destroyed`. Rešitev: `_nastavi_temo()` pred
  ustvarjanjem ponovno veže singleton (`Style.instance = None`).
- `Style(self, ...)` NI veljaven klic — prvi pozicioni argument je
  `theme`, ne `master` (2.x podpis nima masterja).
- Imena tem: uporabljena 2.0 para (`bootstrap-light/dark`); legacy imena
  (`litera`, `darkly`) sprožajo DeprecationWarning.

## Zunaj obsega (iskreno)
- Teme stilirajo **ttk gradnike**. Risarski canvas in `tk.Label` (npr.
  status) imajo fiksne barve — namerno: berljivost tehnične risbe ne
  sme biti odvisna od teme.
- Sistemski „temni način po operacijskem sistemu“ in shranjevanje
  izbire uporabnika — ločeno.

## Verifikacija
- `tests/test_vmesnik.py::test_preklop_teme`: preklop v temno in nazaj;
  če paket manjka, status pošteno javi namestitev; aplikacija deluje
  v obeh primerih. 6 zelenih v datoteki.