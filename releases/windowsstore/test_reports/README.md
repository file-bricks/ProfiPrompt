# WACK-Reports - ProfiPrompt

Dieses Verzeichnis ist für exportierte XML-Reports aus dem Windows App
Certification Kit reserviert.

Konvention:

- Dateiname: `wack_YYYYMMDD_HHMMSS.xml`
- Ablage: nur die neuesten relevanten Reports behalten
- Prüfung: `python scripts/check_store_readiness.py review-wack-report`
- Lokales Paketprotokoll: `python scripts/check_store_readiness.py write-test-protocol`
  schreibt `store_readiness_YYYYMMDD_HHMMSS.md` mit MSIX-SHA256,
  Materialstatus und offenem WACK-Gate.

Solange hier keine `wack_*.xml` liegt, meldet der Store-Preflight den
WACK-Lauf bewusst als offenen Blocker.
