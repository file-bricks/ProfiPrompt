# ProfiPrompt – Windows Store Build-Anleitung

Stand: 2026-10-07

Die verbindlichen Einreichungsgates stehen in der .SOFTWARE-Pipeline unter
`_STORE/WINDOWS_STORE_BUGFIX_POLICY.md`, Abschnitt 7a.

## Build

Ein isoliertes Python-Environment mit `requirements.txt`, PyInstaller und den
Testabhängigkeiten verwenden. `python` im PATH muss auf dieses Environment zeigen.
`build_exe.bat` ruft `scripts/build_release.py` auf: zuerst den zentralen
`build_exclude_scanner.py`, dann einen vollständigen Onedir-Build.

```powershell
python scripts/gen_store_icons.py
.\build_exe.bat
python "$env:OneDrive\.TOPICS\.SOFTWARE\_STORE\icon_consistency_check.py" .
& "$env:OneDrive\.TOPICS\.SOFTWARE\_STORE\msstore_build_msix.ps1" -ProjectRoot (Get-Location).Path -ExePath ".\dist\ProfiPrompt\ProfiPrompt.exe" -OutputMsix ".\releases\windowsstore\v1.0.2\ProfiPrompt.msix"
```

Für bestehende Materialprüfungen kann dasselbe Paket zusätzlich unter
`releases/ProfiPrompt.msix` abgelegt werden. Beide Dateien müssen dieselbe SHA256 haben.

## Tests und Paketprüfung

Die vollständige Pytest-Suite und der Übersetzungscheck müssen bestanden sein.
Das gebaute MSIX erneut mit `icon_consistency_check.py --package` prüfen.
Das Paket in einen frischen Ordner entpacken und **dessen EXE** mit
`--release-smoke <frischer Ausgabeordner>` starten. Screenshots müssen unter der
nativen Windows-Plattform entstehen; Runtime, Qt-Plug-ins und Versionsdaten
müssen vollständig sein.

`python scripts/check_store_readiness.py write-test-protocol` schreibt einen
ergänzenden Materialbericht unter `releases/windowsstore/test_reports`.
Der ältere Readiness-Checker meldet einen fehlenden WACK-Report weiterhin als
Warnung. WACK ist nach der aktuellen zentralen Pipeline ein optionaler
Qualitätsnachweis und ersetzt kein Paketgate.

## Einreichung

Eine Icon-Collage aus dem gebauten Paket erzeugen, auf den OneDrive-Desktop
legen und nach `.USR` kopieren. Erst das dokumentierte Sicht-OK des Users
erlaubt die Einreichung. Die Freigabe und alle Testnachweise müssen an die
SHA256 des tatsächlich hochgeladenen MSIX gebunden sein.

Deutsch und Englisch vorbereitete Neuigkeiten gehören in das Feld
`baseListing.releaseNotes` der Store-Listings. Nach dem Update diese Felder
und den Einreichungsstatus über die Store-API zurücklesen.
Der Store signiert das Paket; lokal wird es dafür nicht signiert.

Preis: kostenlos.
