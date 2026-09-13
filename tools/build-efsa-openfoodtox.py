#!/usr/bin/env python3
"""Read EFSA's OpenFoodTox 3.0 and take the reference values for the substances of our register.

Source: OpenFoodTox 3.0, EFSA's chemical hazards database (doi:10.5281/zenodo.19388272, CC BY-ND 4.0),
downloaded once to tools/terato/openfoodtox-3.0.xlsx (git-ignored, 22 MB). The database is not
redistributed: this script keeps the values for substances the register already lists, with the EFSA
opinion they come from, and writes them to tools/efsa-openfoodtox.json.

EFSA does not classify teratogens. A value says how much of a substance European risk assessment
treats as tolerable, and which effect that figure rests on. Values whose critical effect is
developmental or reproductive are preferred when a substance has several.
Run: python3 tools/build-efsa-openfoodtox.py
"""
import json, pathlib, re

HERE = pathlib.Path(__file__).parent
XLSX = HERE / "terato" / "openfoodtox-3.0.xlsx"
OUT = HERE / "efsa-openfoodtox.json"
TERA = HERE / "teratogens.json"
DEV = re.compile(r"develop|reproduc|teratogen|fertilit|prenatal|maternal|offspring", re.I)
# health-based guidance values only: a margin of exposure, an intake estimate or a generic threshold
# of toxicological concern says nothing a family can use, so they stay out of the register.
KEEP = re.compile(r"^(acceptable daily intake|acute reference dose|tdi|twi|adi|arfd|tolerable)", re.I)
# provisional values are the ones a later opinion replaced, such as the lead PTWI EFSA set aside in 2010
PROVISIONAL = re.compile(r"provisional", re.I)


def main():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

    def sheet(name):
        ws = wb[name]; rows = ws.iter_rows(values_only=True); hdr = list(next(rows))
        return hdr, rows

    hdr, rows = sheet("REF_SUB")
    iu, ic = hdr.index("Document UUID"), hdr.index("Inventory.CASNumber")
    ref_cas = {r[iu]: str(r[ic]).strip() for r in rows if r[iu] and r[ic]}

    hdr, rows = sheet("SUB")
    iu, inm = hdr.index("Document UUID"), hdr.index("ChemicalName")
    irefs = [i for i, h in enumerate(hdr) if h and h.startswith("ReferenceSubstance")]
    sub = {}
    for r in rows:
        ref = next((r[i] for i in irefs if r[i]), None)
        sub[r[iu]] = (r[inm], ref_cas.get(ref, ""))

    hdr, rows = sheet("LIT")
    iu = hdr.index("Document UUID")
    ia, it, iy = hdr.index("GeneralInfo.Author"), hdr.index("GeneralInfo.Name"), hdr.index("GeneralInfo.ReferenceYear")
    lit = {r[iu]: {"author": r[ia] or "", "title": r[it] or "", "year": str(r[iy] or "")} for r in rows if r[iu]}

    hdr, rows = sheet("END_STUDY_REC.HumanHealth")
    iu = hdr.index("Document UUID"); ie = hdr.index("AdministrativeData.Endpoint")
    endpoint = {r[iu]: (r[ie] or "") for r in rows if r[iu]}

    ours = {e["cas"] for e in json.loads(TERA.read_text(encoding="utf-8"))["entries"] if e.get("cas")}

    hdr, rows = sheet("FLEX_SUM.ToxRefValues")
    H = {h: i for i, h in enumerate(hdr) if h}
    def g(r, h):
        i = H.get(h); return r[i] if i is not None else None

    found = {}
    for r in rows:
        name, cas = sub.get(r[3], ("", ""))
        if not cas or cas not in ours: continue
        out = []
        adi = g(r, "HumanHealthHazardCharacteristics.AcceptableDailyIntake.Adi.lowerValue")
        if adi is not None:
            out.append({"kind": "Acceptable daily intake", "value": adi,
                        "unit": g(r, "HumanHealthHazardCharacteristics.AcceptableDailyIntake.Adi.Unit") or "",
                        "endpoint": endpoint.get(g(r, "HumanHealthHazardCharacteristics.AcceptableDailyIntake.CriticalEndpoint"), ""),
                        "opinion": lit.get(g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceToEFSAOpinion"), {})})
        arfd = g(r, "HumanHealthHazardCharacteristics.AcuteReferenceDose.Arfd.lowerValue")
        if arfd is not None:
            out.append({"kind": "Acute reference dose", "value": arfd,
                        "unit": g(r, "HumanHealthHazardCharacteristics.AcuteReferenceDose.Arfd.Unit") or "",
                        "endpoint": endpoint.get(g(r, "HumanHealthHazardCharacteristics.AcuteReferenceDose.CriticalEndpoint"), ""),
                        "opinion": lit.get(g(r, "HumanHealthHazardCharacteristics.AcuteReferenceDose.AssessmentBody"), {})})
        oth = g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.lowerValue")
        if oth is not None:
            desc = g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceValueDescriptor")
            desc = (g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceValueDescriptor.Other")
                    if desc in (None, "other:") else desc) or "Reference value"
            unit = g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.Unit")
            unit = (g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.RefValue.Unit.Other") if unit in (None, "other:") else unit) or ""
            out.append({"kind": str(desc), "value": oth, "unit": str(unit),
                        "endpoint": endpoint.get(g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.CriticalEndpoint"), ""),
                        "opinion": lit.get(g(r, "HumanHealthHazardCharacteristics.OtherReferenceValues.ReferenceToEFSAOpinion"), {})})
        for v in out:
            v["name"] = name
            found.setdefault(cas, []).append(v)

    # one value per substance: a developmental effect first, then the longest-term value
    ORDER = {"Acceptable daily intake": 0, "Acute reference dose": 2}
    best = {}
    for cas, vals in found.items():
        vals = [v for v in vals if KEEP.match(str(v["kind"])) and "bw" in str(v["unit"]) and not PROVISIONAL.search(str(v["kind"]))]
        if not vals: continue
        vals.sort(key=lambda v: (0 if DEV.search(v.get("endpoint", "")) else 1, ORDER.get(v["kind"], 1)))
        best[cas] = vals[0]
        best[cas]["alternatives"] = len(vals) - 1
    OUT.write_text(json.dumps({"source": "EFSA OpenFoodTox 3.0, doi:10.5281/zenodo.19388272, CC BY-ND 4.0, read 13 September 2026",
                               "note": "Reference values for the substances of the DysNet teratogens register only; the database itself is not redistributed.",
                               "values": best}, ensure_ascii=False, indent=1), encoding="utf-8")
    dev = sum(1 for v in best.values() if DEV.search(v.get("endpoint", "")))
    print(f"{len(best)} substances of the register carry an EFSA reference value; {dev} rest on a developmental or reproductive effect")


if __name__ == "__main__":
    main()
