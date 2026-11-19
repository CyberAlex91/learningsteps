<!-- Zweck: Erklärt Entra-Anmeldung, Nutzertrennung und die nachgewiesene lokale KI-Integration. -->
# DEVSECOPS 15 Ex 2 – sichere KI-Zusammenfassung

## Cloud identity rollout (2026-11-19; backend delivery pending)

The backend now accepts the explicit server-side environment setting
FOUNDRY_CREDENTIAL_TYPE=workload_identity. It requires the expected tenant plus
AZURE_CLIENT_ID and AZURE_FEDERATED_TOKEN_FILE injected by the AKS webhook.
It uses WorkloadIdentityCredential without falling back to CLI or other identities.
The local default in foundry.json stays azure_cli. No key/client secret is added.
Eleven summary boundary/credential-mode tests passed offline.

User applied foundry-runtime.tfplan: 2 added, 0 changed, 0 destroyed.
It adds the gpt-5-mini 2025-08-07 GlobalStandard capacity1 deployment and the API's
account-scoped Cognitive Services OpenAI User role. enable_ai_summary defaults to
true for rebuild; deliberately setting false removes the model and its runtime
role, not the Foundry account or journal data. Standard requests can incur usage
charges. No provisioned/reserved throughput deployment is requested.

Bootstrap deployment.yaml now declares the environment setting. Existing CI
delivery changes only the image; after applying the infrastructure and delivering
the new backend code, set this one environment value on the live deployment and
wait for rollout. Do not reapply the old bootstrap image just to change an env var.
Actual Workload Identity inference and authenticated cloud summary remain pending.

## Implementierung und aktueller Status

Die API besitzt Entra-Anmeldung, nutzerbezogene Datenbankabfragen und den
Endpunkt `POST /me/notes/summary`. Der Benutzer wird aus einem signaturgeprüften
Entra-Zugriffstoken bestimmt. Der Client darf keine fremde Nutzerkennung,
Notiztexte, Modelladresse oder eigenen Prompt für die Zusammenfassung vorgeben.

Am 17.11.2026 bestanden 29 isolierte Tests und 27 PostgreSQL-/HTTP-Prüfungen
gegen eine eigens erzeugte Testdatenbank. Ein echter SDK-Aufruf aus dem
Entwicklungscontainer mit drei synthetischen, nicht gespeicherten Texten war
erfolgreich. Anschließend meldete der Nutzer eine erfolgreiche Migration,
echten Swagger-Login und drei erfolgreiche gespeicherte Testnotizen. Die
tatsächliche KI-Antwort vom 17.11.2026, 15:42:18 UTC, umfasst alle drei
gespeicherten Themen, Schwierigkeiten und nächsten Schritte, mit
`note_count=3` und `ai_generated=true`. Der Nutzer bestätigte am 17.11.2026,
dass Text und Screenshot eingereicht wurden. Die Kursbewertung und der
endgültig eingereichte Screenshot wurden nicht unabhängig geprüft.

## Lokale Umgebung

Projektarbeit und Azure CLI laufen im WSL-Terminal von VS Code. Die vorhandenen
Projektcontainer liegen dagegen auf Docker Desktop. Der Befehl `docker` in WSL
zeigt auf eine separate Ubuntu-Engine. Die richtige CLI wird ausdrücklich so
ausgewählt:

```bash
docker_desktop="/mnt/c/Users/Administrator/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
```

Die Python-Laufzeit der API ist `/workspaces/venv/bin/python` im Container
`learningsteps-origins-devcontainer-1`. Azure CLI wird für die lokale
Entwickleranmeldung separat unter `/opt/learningsteps-azure-cli` installiert:

```bash
"$docker_desktop" exec --user root learningsteps-origins-devcontainer-1 \
  bash /workspaces/.devcontainer/install-azure-cli.sh
```

Die interaktive Azure-Anmeldung im Container wird vom Nutzer selbst ausgeführt.
Keine Anmeldecodes, Tokens oder CLI-Caches in Repository oder Nachweise kopieren.
CLI-Cache und Laufzeitanmeldung gehören nicht in ein veröffentlichtes Image.
Bei einem Cloud-Rollout ist diese lokale Entwickleridentität durch eine
dedizierte Managed-/Workload-Identity zu ersetzen.

## Öffentliche Konfiguration

`api/security/entra.json` enthält ausschließlich Tenant-, API- und Swagger-IDs.
`api/security/foundry.json` enthält den festen serverseitigen Endpunkt und
Deploymentnamen. Diese Konfigurationen enthalten keine Schlüssel oder Tokens.

Foundry-Ressource: `learningsteps-ai-alex-709d408c` in `rg-learningsteps-ai`,
Region `germanywestcentral`, Deployment `learningsteps-summary`, Modell
`gpt-5-mini`, Version `2025-08-07`, GlobalStandard, Kapazität 1.
Schlüsselauthentifizierung ist deaktiviert. Die Entwickleridentität erhält
`Cognitive Services OpenAI User` an der konkreten Ressource. Kapazität ist kein
Euro-Ausgabenlimit; GlobalStandard garantiert keine Verarbeitung nur in Deutschland.

## Anmeldung und Datenzuordnung

Swagger lokal über **http://localhost:8000/docs** öffnen. Die registrierte
Rückleitungsadresse lautet `http://localhost:8000/docs/oauth2-redirect`.
Die Anmeldung verwendet Authorization Code mit PKCE und kein Client Secret.
Nur das LearningSteps-Zugriffstoken gelangt zum Browser, kein Foundry-Token.

Die API prüft RS256-Signatur, festen Issuer, Tenant, API-Audience, Gültigkeit,
v2-Tokenformat, delegierten Scope und zugelassenen Swagger-Client. Der
Eigentümerschlüssel ist das geprüfte Paar `(tid, oid)`. Die JWT-Signaturschlüssel
werden nur von einer fest konfigurierten Microsoft-JWKS-Adresse geladen.

Vor Änderung einer bestehenden Datenbank einen aktuellen Backup-/Restore-Test
durchführen. Anschließend die additive Migration
`database/migrations/20261117_add_entry_owners.sql` ausdrücklich anwenden.
Sie ergänzt zwei nullable UUID-Spalten und einen Index. Alte Inhalte, IDs und
Zeitstempel bleiben erhalten. Alte Notizen ohne eindeutige Eigentümerzuordnung
werden nicht automatisch einem Login zugewiesen und sind über die
nutzerspezifischen Routen nicht sichtbar. Eine spätere Übernahme erfordert eine
separate verifizierte Zuordnung.

Alle sechs CRUD-Routen sind geschützt und im Repository nach Eigentümer
gefiltert. Auch `DELETE /entries` betrifft nur eigene Einträge. Fremde IDs
liefern 404. Eigentümerfelder aus Client-JSON werden nicht akzeptiert.

## Zusammenfassung

Nach dem Login neue synthetische Notizen über `POST /entries` speichern.
`GET /entries` zeigt ausschließlich den eigenen zugeordneten Bestand.
`POST /me/notes/summary` akzeptiert keinen Body oder ein leeres JSON-Objekt `{}`.
Es liest den vollständigen eigenen Bestand und liefert:

```json
{
  "summary": "Tatsächlicher KI-Antworttext",
  "note_count": 3,
  "ai_generated": true,
  "generated_at": "UTC-Zeitpunkt"
}
```

Leerer Bestand: verständliche Antwort mit `ai_generated=false`, ohne
Modellaufruf. Der lokale Nutzer-Limiter erlaubt einen nichtleeren
Zusammenfassungsversuch pro Minute und API-Prozess. Kein verstecktes Retry.
Bei mehr als 24000 Zeichen serialisiertem Quelleninhalt gibt es einen
ausdrücklichen Größenfehler; es werden keine Notizen heimlich abgeschnitten.

Die Anwendung sendet nur ID und die drei Notizfelder an das feste Deployment.
Die eigenen Entra-/Datenbank-Zugangsdaten und Nutzerkennungen werden nicht in
den Modellkontext aufgenommen. Ein neuer zustandsloser Request wird mit
`store=false` und `tools=[]` erzeugt. Modellantworten lösen keine Werkzeuge,
Netzwerkabrufe oder Datenänderungen aus. Unerwartete Tool-Ausgaben,
unvollständige oder leere Antworten werden abgewiesen.

Notizen sind JSON-kodierte Daten unter einer festen vertrauenswürdigen
Aufgabenanweisung. Prompt-Injection bleibt ein zusätzlich zu prüfendes Risiko;
der Schutz beruht insbesondere auf fehlenden Werkzeugen und der bereits vor
dem Modellaufruf durchgesetzten Datenzuordnung. Texttreue ist separat anhand
der tatsächlich gespeicherten synthetischen Quellen zu beurteilen.

Keine Prompt-/Antworttexte oder Authorization-Header in Betriebslogs.
Fehlerantworten enthalten keine rohen SDK-/Datenbankausnahmen. Die
Swagger-Antwort wird als Text/JSON angezeigt, nicht als aktives HTML.

## Tests und Nachweise

Aus dem LearningSteps-Projektordner in WSL:

```bash
"$docker_desktop" exec learningsteps-origins-devcontainer-1 \
  /workspaces/venv/bin/python -m unittest discover -s /workspaces/tests -p 'test_*.py' -v

"$docker_desktop" exec learningsteps-origins-devcontainer-1 \
  /workspaces/venv/bin/python /workspaces/tests/test_notes_isolation.py
```

Der zweite Test erzeugt ausschließlich seine eigene zufällig benannte
Testdatenbank und entfernt nur diese anschließend wieder. Die ursprüngliche
LearningSteps-Datenbank wird nur zur Verbindung und zum Vergleich der
Zeilenanzahl verwendet. Zwei synthetische RSA-signierte Identitäten prüfen
Nutzertrennung, fremde IDs, Eigentümermanipulation, Migration und Auswahl der
Modellquellen. Der Modelltransport ist dabei gemockt. Es gibt keinen
produktiven Test-Header und keine Login-Umgehung.

`tests/check_foundry_connection.py` ist ein **ausdrücklicher kostenpflichtiger
Live-Test** mit RAM-Testtexten, kein regulärer Unit-Test. Der erfolgreiche
Aufruf ersetzt nicht die Abnahme mit gespeicherten Benutzer-Notizen.

Für die Submission: Screenshot der echten Zusammenfassung in LearningSteps
mit sichtbarer Notizanzahl, Vergleich mit mehreren gespeicherten synthetischen
Quellen und eine Beschreibung von Nutzertrennung, serverseitigem Entra-Zugriff,
fehlenden Modellwerkzeugen und Geheimnisschutz. Keine Tokens oder
Anmeldecodes im Screenshot. Ein echter Zwei-Konten-Browsertest ist ohne zweites
Kontrollkonto nicht bestätigt; isolierte Mehrbenutzertests sind davon zu trennen.

Die alten Origins-Abnahmeskripte setzen teilweise anonyme CRUD-Routen voraus.
Sie sind historische Nachweise und dürfen nicht unverändert als aktuelle
Auth-/KI-Abnahme ausgegeben werden. Evolution-Rollout, Terraform, AKS und
Cloud-Managed-Identity sind gesonderte nächste Arbeiten.
