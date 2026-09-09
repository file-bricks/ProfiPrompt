# WACK-Protokoll - ProfiPrompt

Stand: offen
Status: Für das aktuelle Paket liegt noch kein frischer `wack_*.xml`-Report unter `releases/windowsstore/test_reports/` vor.

## Nächster Lauf

1. Windows App Certification Kit gegen `releases/ProfiPrompt.msix` ausführen.
2. XML-Bericht als `releases/windowsstore/test_reports/wack_YYYYMMDD_HHMMSS.xml` speichern.
3. Danach die Repo-Nachbereitung fahren:

```bash
python scripts/check_store_readiness.py review-wack-report
python scripts/check_store_readiness.py write-wack-protocol
python scripts/check_store_readiness.py
```

Sobald ein echter XML-Report vorliegt, wird dieses Dokument aus dem neuesten Report neu erzeugt und überschrieben.
