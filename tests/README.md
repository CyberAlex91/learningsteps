<!-- Zweck: Erklärt die aktuellen Tests und ihre Voraussetzungen sowie Aussagegrenzen. -->
# Tests für die aktuelle authentifizierte API

`test_identity.py` prüft JWT-/Entra-Validierung; `test_summary.py` die sichere
serverseitige Zusammenfassung. `test_runtime.py` prüft Konfiguration und Probes,
`test_ci_delivery.py` die Grenzen der automatischen Auslieferung.
Diese Unit-Tests verwenden keine echten Azure-Zugangsdaten oder Modellaufrufe.

`test_notes_isolation.py` verwendet eine eigene neu erzeugte PostgreSQL-Testdatenbank
und zwei synthetische Identitäten. Es prüft die Nutzertrennung über HTTP und SQL;
die normale Lernjournal-Datenbank wird nicht geleert. Der Test benötigt einen
lokalen Benutzer mit CREATEDB, nicht den eingeschränkten Cloud-App-Benutzer.
`ci_tests.py` erzwingt die dafür vorgesehene isolierte GitHub-Testdatenbank.

`check_container_smoke.py` prüft im gebauten Image nicht privilegierten Start,
OpenAPI und Ablehnung anonymer geschützter API-Anfragen.
`check_foundry_connection.py` ist ein expliziter echter Modellverbindungstest und
kann Modellkosten verursachen. `check_secret_exposure.py` prüft Quellmuster und
bekannte synthetische Notizinhalte im lokalen API-Log, ohne Trefferwerte auszugeben.

Konkrete lokale Auth-/KI-Testbefehle: [AI-INTEGRATION.md](../AI-INTEGRATION.md).
Automatische CI-Ausführung: [CI-CD.md](../CI-CD.md).
Cloud-Betriebsprüfungen: [k8s-manifests/README.md](../k8s-manifests/README.md).

`DATABASE_URL_FILE` und `DATABASE_URL` dürfen nicht gleichzeitig gesetzt sein.
Konfiguration wird beim API-Start gelesen; nach Geheimnisrotation Pods neu ausrollen.
Liveness greift nicht auf DB oder KI zu; Readiness prüft Tabellenlesezugriff mit
kurzem Timeout. Die entfernten anonymen Origins-Tests gehören nicht zur aktuellen
API-Abnahme; der historische Code liegt im finalen Origins-Abgabepaket.
