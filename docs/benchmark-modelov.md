# Ocenjevanje modelov za kodiranje — skriptni pristop (brez AI-žirije)

*Namen: meriti kakovost kodiranja **deterministično**, tako da sodbo izda
izvajanje testov, ne model. Vsak rezultat je ponovljiv, sledljiv in
preverljiv brez človeške ali modelske presoje.*

Stanje: `benchmark/` + 27 testov. V tem koraku **noben model ni bil
klican** — ocenjevalnik je validiran s *ponarejenimi agenti*
(`benchmark/ponarejeni_agent.py`), ki izzovejo vsak razred izida.

---

## 1. Kaj smo prevzeli iz javnih praks

| Vir | Pravilo, ki smo ga uporabili |
|---|---|
| SWE-bench, `docs/guides/evaluation.md` in `harness/run_evaluation.py` (GitHub, obiskano 2026-11-23): <https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md> | Popravek se uporabi na **pripetem** izhodišču, nato se zaženejo testi; uspeh = **FAIL_TO_PASS** zeleni **in PASS_TO_PASS** nespremenjeni. |
| OpenAI, *Introducing SWE-bench Verified* (2024-08-13): <https://openai.com/index/introducing-swe-bench-verified/> | **Testi se agentu ne pokažejo.** Oboji (ciljni in zaščitni) morajo uspeti, sicer popravek ni rešitev. |
| SWE-bench, arXiv:2310.06770 (članek): <https://arxiv.org/html/2310.06770v3> | Ocena = delež rešenih nalog po izvedbi testov; patch mora biti uporabljiv. |
| Aider polyglot benchmark, `benchmark/README.md`: <https://github.com/Aider-AI/aider/blob/main/benchmark/README.md> | Zapis ponovitve mora vsebovati **nastavitve in različico repozitorija** (git hash), da je rezultat ponovljiv. |
| CodePress, *Aider Polyglot — how the benchmark actually works*: <https://codepress.dev/benchmarks/aider-polyglot> | **Prekoračitev časa šteje kot neuspeh**; javne naloge so onesnažene (rešitve so v istem repozitoriju) — zato canary in opozorilo o onesnaženju. |
| Chen idr. (HumanEval), opisano v <https://dmxsf.com/en/wiki/evaluation/eval-statistics/> | **Nepristranski pass@k**: `1 − C(n−c, k)/C(n, k)`, povprečeno po nalogah. |
| coding.sh, *How evals are computed*: <https://coding.sh/docs/eval-methods> | Parni bootstrap (10 000 vzorcev, seme), **McNemar** na neskl adjenih parih, znakovni test za majhne serije. |
| *Establishing Best Practices for Building Rigorous Agentic Benchmarks*, arXiv:2507.02825: <https://arxiv.org/pdf/2507.02825v5> | Izolacija od resnice (ground truth), čiščenje stanja med nalogami, zamrznjeno okolje. |
| Coder, *Runtime contamination and agent eval sandboxes*: <https://coder-eval.com/blog/strict-agent-eval-sandbox> | **Canary žeton** v skriti rešitvi/testih; najdba v izhodu pomeni uhajanje. |
| *Beyond the Leaderboard: How to Build a Coding-Agent Eval You Can Trust*: <https://patrickroch.dev/posts/agent-evals-you-can-trust/> | Naloga se začne na pripetem commitu; poziv ne sme razkriti popravka; skriti testi tolerirajo legitimne variantne rešitve; negotovost naj upošteva gručenje po repozitoriju. |

## 2. Protokol (kaj ocenjevalnik dejansko naredi)

1. **Svež prostor iz predloge.** Delovni prostor se vedno ustvari iz
   `benchmark/primeri/...`, nikoli iz živega repozitorija. Stanje se po
   nalogi pobriše (`tempfile` + `rmtree`).
2. **Agent dobi le poziv.** Skriti testi v prostoru še ne obstajajo.
3. **Canary.** Po agentu se pregležejo vse tekstovne datoteke prostora in
   izhod agenta. Če se pojavi canary žeton iz skritega testa, je rezultat
   `onesnazeno` — tudi če so testi zeleni.
4. **Skriti testi šele zdaj.** Kopirajo se v **ločen** imenik
   (`osnovni/skriti_testi`), pytest teče z `-c` svežo ini datoteko,
   `-o addopts=` in `--confcutdir`, da agent ne more podtakniti
   `conftest.py`/`pytest.ini`. Agentova morebitna mapa `skriti_testi` se
   zavrže.
5. **Razvrstitev:** `resen` (oba seznama), `ni_resen`, `pokvarjen`
   (regresija), `prekoracen_cas`, `napaka_okolja`, `onesnazeno`.
6. **Zapis:** JSON z vsemi izvedbami, zrnom, časi in sporočili ter z
   **okoljem izvedbe** (`okolje`): git hash, oznaka umazanega delovnega
   drevesa, različica Pythona, platforma — po zahtevi Aider metodologije
   za ponovljivost.

Nabor trenutno vsebuje tri naloge: `vsota` (ena datoteka), `razlika`
(ena datoteka, zaščita obstoječe funkcije) in `orodja`
(**večdatotečni** popravek z zaščito v drugi datoteki).

## 3. Metrike

- **Delež uspeha** + **Wilsonov interval** (za majhen n).
- **pass@k** (nepristranska oblika) — pri več ponovitvah na nalogo.
- **Primerjava dveh modelov:** parni bootstrap za razliko B − A (95 %
  interval, seme), točni **znakovni test** in **McNemar**, kadar so
  naloge binarne. Razlika je *dokazana* le, če interval ne vsebuje 0.

## 4. Zagon

```bash
# seznam nalog
python -m benchmark.tek --seznam

# validacija ocenjevalnika brez modela (ponarejeni agent)
python -m benchmark.tek \
  --agent "python benchmark/ponarejeni_agent.py --nacin ok" \
  --ponovitve 3 --izhod rezultati.json

# primerjava dveh rezultatov (izbirno tudi v JSON)
python -m benchmark.tek --primerjaj a.json b.json --izhod primerjava.json
```

Priklop pravega agenta je poljubna predloga ukaza; oznake `{prostor}`,
`{poziv}`, `{naloga}` in `{python}` se zamenjajo. Zgled:

```bash
python -m benchmark.tek --ponovitve 3 --zrno 7 \
  --agent 'opencode run --model deepseek/deepseek-v4.1-flash "{poziv}"' \
  --izhod flash.json
```

V rezultat zapiši še model, nastavitve in git hash — to zahteva Aider
metodologija za ponovljivost.

## 5. Dodajanje naloge

```
benchmark/naloge/<id>/task.yaml
benchmark/naloge/<id>/skriti_testi/test_*.py
```

```yaml
id: vsota
opis: |
  <poziv agentu — brez razkritja rešitve>
predloga: ../primeri/knjiznica
fail_to_pass: [test_vsota_osnovno]
pass_to_pass: [test_obstojeca_funkcija]
canary: [SKRIVNI-KANAR-VSOTA-7f3a]
cas_s: 20
```

Preverjanje zavrne: neznana polja, prazen `fail_to_pass`, test v obeh
seznamih, neveljaven `cas_s`, podvojene `id`.

## 6. Omejitve (iskreno)

- **Ni varnostni sandbox.** Agent z dostopom do lupine lahko pobegne iz
  prostora; za nezaupanja vredne agente uporabi VM/container.
- **Nabor nalog je majhen in ilustrativen** — intervali zaupanja so
  široki, rezultat ni lestvica. Za resno primerjavo potrebuješ 30+
  nalog iz več repozitorijev in gručenje po repozitoriju v negotovosti.
- **Javne naloge so lahko v učnih podatkih.** Canary zazna le uhajanje
  med izvajanjem, ne kontaminacije učnega nabora. Za to so potrebne
  sveže/analogne naloge.
- **Presoja kakovosti rešitve** (berljivost, arhitektura) ni merjena —
  merjeno je le vedenje, ki ga testi pokrijejo.
- V tem koraku noben model ni bil klican; vsi rezultati so iz
  ponarejenih agentov in služijo kot dokaz, da ocenjevalnik deluje.
