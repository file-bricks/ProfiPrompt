# Bibliothek nach einem Lesefehler

ProfiPrompt bricht Änderungen und Bibliotheksexporte ab, wenn eine benötigte
Bibliotheksdatei nicht vollständig gelesen werden kann. Das gilt für fehlende
Dateien, Zugriffsfehler, ungültiges UTF-8, beschädigtes JSON sowie ungültige
Listen und verschachtelte Einträge. Beschädigte Dateien werden nicht automatisch
als leere Bibliothek überschrieben. Ein vorhandener Bibliotheksexport bleibt
bei einem solchen Ladefehler erhalten.

Die Anzeige kann bei einem Ladefehler weiterhin leer bleiben. Leere Anzeige ist
kein Beleg für eine leere Bibliothek. Beim Speichern erscheint eine Fehlermeldung;
der Dialog bleibt geöffnet und die eingegebenen Änderungen bleiben verfügbar.

Prüfen Sie die angegebene Datei und ihre Zugriffsrechte. Sichern Sie beschädigte
Originaldateien, bevor Sie sie bewusst reparieren oder aus einer Sicherung
wiederherstellen. Eine Änderung lässt sich nach der Reparatur erneut versuchen.

Beim Löschen eines Prompts oder einer Version werden Prompt- und Board-Datei
vor dem ersten Schreiben gelesen. Ein Prozess hält Änderungen desselben
Storage-Objekts über einen gemeinsamen Lock zusammen. Zwei getrennte JSON-Dateien
bilden damit keine gemeinsame Transaktion: Ein späterer Schreibfehler kann eine
teilweise ausgeführte Löschung hinterlassen. Gleichzeitige Änderungen anderer
Storage-Objekte oder Prozesse und Ausfälle des Rechners sind nicht abgesichert.

Diese Änderung erstellt keine neue EXE und ersetzt keine Geräte-, Browser- oder
Store-Abnahme. Tests verwenden ausschließlich eigene temporäre Bibliotheken.
