import os
import tempfile

import yaml

from risba import generiraj


def _stevilo_strani_pdf(pot):
    with open(pot, "rb") as f:
        data = f.read()
    # Enostaven preštevek strani brez dodatnih odvisnosti:
    # /Type /Page (posamezna stran) vs /Type /Pages (koren drevesa strani).
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")


def test_generiraj_pdf_ni_prazen_in_ima_strani():
    with open("projekt_primer.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with tempfile.TemporaryDirectory() as d:
        izhod = os.path.join(d, "smoke-test.pdf")
        cfg["izhod"] = izhod
        pot_pdf, pot_png, dodatni, kolicine = generiraj(cfg)
        assert os.path.isfile(pot_pdf), "PDF ni bil ustvarjen"
        assert os.path.getsize(pot_pdf) > 0, "PDF je prazen (0 B)"
        strani = _stevilo_strani_pdf(pot_pdf)
        assert strani >= 2, f"Pričakovane vsaj 2 strani, dobljeno: {strani}"
        # pri uspešnem montažnem listu mora obstajati kosovnica/nalepke
        assert kolicine and kolicine.get("kosovnica"), "Manjka kosovnica"
        assert any(p.endswith("-kosovnica.csv") for p in dodatni), "Manjka CSV kosovnica"
        assert any(p.endswith("-nalepke.png") for p in dodatni), "Manjka PNG nalepk"


if __name__ == "__main__":
    test_generiraj_pdf_ni_prazen_in_ima_strani()
    print("SMOKE OK")
