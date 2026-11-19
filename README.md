<!-- Zweck: Erklärt die Anwendung, Architektur und den Einstieg in die aktuelle Evolution-Phase. -->
# LearningSteps Evolution

LearningSteps ist ein Lerntagebuch: angemeldete Nutzer speichern ihre Arbeit
(`work`), Schwierigkeiten (`struggle`) und nächsten Schritte (`intention`).
FastAPI stellt die API bereit, PostgreSQL speichert die Einträge. Swagger unter
`/docs` ist die technische Bedienoberfläche; ein separates Benutzer-Frontend
ist bisher nicht implementiert.

## Aktueller Stand und Orientierung

- [EVOLUTION.md](EVOLUTION.md): nachgewiesene Ergebnisse und offene Projektaufgaben.
- [DATEIUEBERSICHT.md](DATEIUEBERSICHT.md): Zweck jeder eigenen Repository-Datei.
- [infra-terraform/README.md](infra-terraform/README.md): Azure-Infrastruktur und State.
- [k8s-manifests/README.md](k8s-manifests/README.md): Kubernetes und Betriebsprüfungen.
- [CI-CD.md](CI-CD.md): GitHub-Prüfungen und OIDC-Auslieferung.
- [SECURITY-SCANS.md](SECURITY-SCANS.md): Scanergebnisse und eingeordnete Fehlalarme.
- [AI-INTEGRATION.md](AI-INTEGRATION.md): Entra, Nutzertrennung und lokale KI-Abnahme.
- [tests/README.md](tests/README.md): Testumfang und Voraussetzungen.

## Architektur

Browser → HTTPS-Gateway auf AKS → interne FastAPI-API → private PostgreSQL-Datenbank.
Entra prüft die Nutzeranmeldung. Die API begrenzt Einträge auf die geprüfte
Tenant-/Nutzeridentität. Die Datenbank-URL kommt über Workload Identity und
Key Vault CSI als Datei in den API-Pod; sie steht nicht im Manifest oder Browser.

Die KI-Zusammenfassung wird serverseitig erzeugt. Die lokale Tagesaufgabe ist
nachgewiesen; die Umstellung auf Workload Identity für Foundry im Cluster ist
noch offen. Das Foundry-Modell wurde nach der Tagesaufgabe entfernt und muss
kontrolliert durch Terraform wieder eingebunden werden. Nicht als bereits
funktionierende Cloud-KI beschreiben.

## API benutzen

Cloud: https://learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com/docs

Lokal: http://localhost:8000/docs

In Swagger über **Authorize** mit Entra anmelden. `GET /me` prüft die Identität.
`POST /entries` legt eine eigene Notiz an; `GET /entries` zeigt eigene Notizen.
`GET`, `PATCH` und `DELETE /entries/{entry_id}` arbeiten auf einem eigenen Eintrag.
`DELETE /entries` löscht alle eigenen Einträge und ist kein routinemäßiger Testschritt.
`POST /me/notes/summary` fasst gespeicherte eigene Notizen zusammen, sofern das Modell
und die serverseitige Identität verfügbar sind.

## Entwicklung und Auslieferung

Azure-, Git- und Kubernetes-Schritte erfolgen im WSL-Terminal von VS Code.
Docker Desktop ist die verwendete lokale Engine. Im übergeordneten Projektordner
liegen `Start-Lokal.ps1` und `Stop-Lokal.ps1` für PowerShell. `start.sh` startet
FastAPI im lokalen Entwicklungscontainer mit der vorhandenen Python-Umgebung.
`.env` bleibt privat; `.env-sample` enthält nur lokale Beispielwerte.

GitHub Actions prüft Python, Nutzertrennung mit einer isolierten Testdatenbank,
Quellen/Images/Terraform und künftig zusätzlich die vollständige gefetchte
Git-Historie. Nur der festgelegte vertrauenswürdige Feature-Branch darf nach
bestandenen Prüfungen über OIDC unveränderte geprüfte Images nach ACR und AKS liefern.
Vor Wechsel auf `main` müssen Workflow und Entra-Föderation bewusst angepasst werden.

Terraform-Änderungen: formatieren, validieren, Plan erstellen und prüfen, dann
den geprüften Plan anwenden. Alte gespeicherte Pläne wurden entfernt; vor einer
neuen Anwendung immer neu planen. `terraform destroy` ist bis zum vorbereiteten
Backup-/Wiederaufbautest kein Routinebefehl.

## Aufbewahrung

Anwendung, Infrastruktur, Tests und reproduzierbare Betriebsprüfungen bleiben
im Repository. Aktuelle Nachweise liegen außerhalb von Git im übergeordneten
`artifacts`-Ordner. Die historische Origins-Abgabe ist dort unter `Abgabe` erhalten;
überholte anonyme Tests und die verworfene Caddy-Konfiguration sind entfernt.
Geheimnisse, Backups, State, venv und Providercache sind keine kommentierbaren
Projektquellen und werden weder veröffentlicht noch pauschal bereinigt.
