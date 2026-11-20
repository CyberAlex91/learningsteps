<!-- Zweck: Erklärt die Anwendung, Architektur und den Einstieg in die aktuelle Evolution-Phase. -->
# LearningSteps Evolution

Aktueller Betriebsmodus ab 20.11.2026: vollständiger Cloud-Abbau einschließlich
Remote-State-Speicher. Vorhandene Notizen, genaue Images und Zertifikate sind
privat lokal gesichert. Die folgende Architektur beschreibt den nachgewiesenen,
bei Bedarf wiederherstellbaren Betrieb, keine aktuell laufende Website.

**Ort: WSL-Terminal, übergeordneter LearningSteps-Ordner.**

```bash
python3 app/scripts/lifecycle.py up      # wiederherstellen, danach laufende Kosten
python3 app/scripts/lifecycle.py down    # sichern und vollständig abbauen
python3 app/scripts/lifecycle.py check   # rein lokale Sicherungsprüfung
```

Alternativ aus PowerShell: `app/scripts/LearningSteps.ps1 -Action up`.
Details und private Voraussetzungen: [RECOVERY.md](RECOVERY.md).
Git und das Abgabe-ZIP enthalten die privaten Notizbackups und Schlüssel nicht.


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
- [RECOVERY.md](RECOVERY.md): geprüfte Daten-/Release-Sicherung und kontrollierter Wiederaufbau.
- [CI-CD.md](CI-CD.md): GitHub-Prüfungen und OIDC-Auslieferung.
- [SECURITY-SCANS.md](SECURITY-SCANS.md): Scanergebnisse und eingeordnete Fehlalarme.
- [AI-INTEGRATION.md](AI-INTEGRATION.md): Entra, Nutzertrennung und lokale KI-Abnahme.
- [tests/README.md](tests/README.md): Testumfang und Voraussetzungen.

## Architektur

Browser → HTTPS-Gateway auf AKS → interne FastAPI-API → private PostgreSQL-Datenbank.
Entra prüft die Nutzeranmeldung. Die API begrenzt Einträge auf die geprüfte
Tenant-/Nutzeridentität. Die Datenbank-URL kommt über Workload Identity und
Key Vault CSI als Datei in den API-Pod; sie steht nicht im Manifest oder Browser.

Die KI-Zusammenfassung wird serverseitig erzeugt. Das Modell und das eingeschränkte
Zugriffsrecht sind in Terraform verwaltet. Die API verwendet im Cluster ausdrücklich
Workload Identity. Ein echter Modellaufruf aus AKS mit drei synthetischen Notizen
ist nachgewiesen. Auch der angemeldete Cloud-Aufruf hat die gespeicherte eigene
Notiz erfolgreich zusammengefasst. Die lokale KI-Tagesaufgabe ist bereits nachgewiesen.

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
Quellen/Images/Terraform und die vollständige gefetchte Git-Historie. Nur ein
Push auf `main` im festgelegten Repository darf nach bestandenen Prüfungen über
OIDC unveränderte geprüfte Images nach ACR und AKS liefern. Die exakte Föderation
und der Workflow verwenden denselben Branch.

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
