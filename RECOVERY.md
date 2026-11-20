<!-- Zweck: Erklärt den vollständigen kostenfreien Abbau und den Wiederaufbau mit einem Befehl einschließlich State-Backend und Datensicherung. -->
# LearningSteps vollständig abbauen und wiederherstellen

Stand: 20.11.2026. Maßgeblich ist jetzt `scripts/lifecycle.py`.
Der am 19.11. nachgewiesene erste Neuaufbau ließ den State-Speicher bestehen.
Der neue vollständige Abbau entfernt auch diesen Speicher und seine Ressourcengruppe.

## Ein Befehl – Ort: WSL-Terminal in VS Code

Im übergeordneten LearningSteps-Projektordner:

```bash
python3 app/scripts/lifecycle.py down
python3 app/scripts/lifecycle.py up
```

`down` sichert und löscht die Cloud. `up` erstellt sie bei Bedarf wieder und
verursacht dann erneut Azure-Kosten. Nicht beide unmittelbar nacheinander
aufrufen, wenn die Umgebung abgeschaltet bleiben soll.

Nur lesend beziehungsweise ohne Cloud-Zugriff:

```bash
python3 app/scripts/lifecycle.py status
python3 app/scripts/lifecycle.py check
```

`status` liest Azure und zeigt vorhandene Projektressourcen. `check` prüft lokal
Chiffrate, Schlüssel und Prüfsummen; es startet keine Cloud-Ressourcen.

## Alternativ ein Befehl – Ort: PowerShell

Im LearningSteps-Projektordner:

```powershell
.\app\scripts\LearningSteps.ps1 -Action up
.\app\scripts\LearningSteps.ps1 -Action down
```

Ohne Aktionsangabe liest das PowerShell-Werkzeug nur den Status. Es führt alle
Azure-Schritte in WSL aus. Benutzer ist standardmäßig cyberalex. Der Python-Ablauf
setzt den eigenen Werkzeugpfad und die dedizierte kubeconfig selbst.

## Voraussetzungen

- Lokaler Projektordner mit unveränderten privaten Wiederherstellungsdateien.
- Azure CLI in WSL, angemeldet in Alexander Plank - Sub im richtigen Tenant.
- GitHub CLI in WSL für Lieferfreigabe und öffentliche Client-ID-Variablen.
- Terraform, kubectl/kubelogin sowie Python mit cryptography und PyYAML in WSL.
- Docker Desktop für Imagearchive. Das Werkzeug startet ihn bei Bedarf lokal
  im Hintergrund; eventuell erforderliche Anmeldedialoge bleiben Benutzeraufgabe.
- Bestehende Entra-Registrierungen für API und Swagger. Diese bleiben erhalten
  und sind keine laufenden Azure-Rechenressourcen.

Die Scripts verwenden die festen Projektgruppen. Andere Projekte, Ressourcen
oder Subscriptions werden nicht gelöscht. Geänderte Quoten, Kapazitäten oder
abgelaufene Anmeldungen können einen späteren Neuaufbau anhalten. Der Ablauf
lockert dafür keine Firewall auf 0.0.0.0/0 und umgeht keine TLS-Prüfung.

## Was down tatsächlich macht

1. Automatische Cloud-Auslieferung über die GitHub-Variable
   LEARNINGSTEPS_CLOUD_ENABLED=false sperren und aktive Läufe ausschließen.
2. Docker und nötigenfalls kurz AKS/PostgreSQL starten, damit eine AKTUELLE
   Sicherung entsteht. Die öffentliche Entwickler-IP wird gezielt als /32 aktualisiert.
3. HPA entfernen und API auf null skalieren: keine weiteren Notizänderungen über
   die API während der Sicherung. Bestehende Notizen werden nicht gelöscht.
4. Alle Spalten/Zeilen der einzigen öffentlichen Tabelle entries exportieren,
   lokal mit AES-256-GCM verschlüsseln und tatsächlich in eine isolierte neue
   Testdatenbank restaurieren. Vollständigen Datenhash vergleichen und nur die
   Testdatenbank entfernen. Danach den unveränderten Originalinhalt erneut prüfen.
5. Genau ausgelieferte API-/Gateway-Images lokal archivieren und Digests prüfen.
   Privaten Zertifikatszustand nur im Speicher lesen und sofort verschlüsseln.
6. Terraform-State zusätzlich lokal verschlüsselt sichern. Gateway-Service,
   Deployment und Zertifikatsvolume geordnet entfernen, damit Azure Netzwerk
   und Disk freigibt.
7. Die drei bekannten prevent_destroy-Sperren vorübergehend öffnen. Einen neuen
   vollständigen Destroy-Plan erstellen, auf die exakten Projektgruppen begrenzen,
   seine Prüfsumme kontrollieren und anwenden. Danach leeren State nachweisen.
8. Leeren State ebenfalls lokal verschlüsselt sichern, Schutzsperren wieder setzen
   und verbleibende eigene Gruppen einschließlich rg-learningsteps-tfstate löschen.
9. Subscription auf aktive LearningSteps-Ressourcen und alle fünf Projektgruppen
   prüfen. Erst null Ressourcen und fünf fehlende Gruppen gelten als abgeschaltet.

Gestoppte Dienste können für die Sicherung also kurz laufen. Der Zielzustand ist
anschließend vollständiger Abbau, nicht nur Stopped mit weiter bestehendem Speicher.
Vergangener Verbrauch kann verzögert in der Azure-Abrechnung erscheinen.
Standard-Key-Vault- und Foundry-Löschschutz wird nicht umgangen; softgelöschte
Objekte können bis zum Ende der Schutzfrist sichtbar bleiben.

## Was up tatsächlich macht

1. Lokale Daten-, Image- und Zertifikatssicherungen entschlüsseln/prüfen.
2. State-Ressourcengruppe, Storagekonto und privaten Blobcontainer neu erstellen:
   Entra-Anmeldung, HTTPS, keine Shared Keys, kein öffentlicher Blobzugriff,
   Versionierung und sieben Tage Blob-/Container-Löschschutz.
3. Terraform neu mit dem Backend verbinden. Bei einem neuen leeren Backend nur
   den verifiziert LEEREN State zurückspielen. Den alten Ressourcen-State vor dem
   Abbau nie als vermeintlich noch vorhandene Infrastruktur hochladen.
4. Aktuelle Entwickler-IP aufnehmen und den nicht destruktiven Wiederaufbauplan
   anwenden. Softgelöschtes Foundry-Konto kontrolliert übernehmen; nach Ablauf
   seiner Aufbewahrung kann Terraform es neu erstellen. Teilstände bleiben erhalten.
5. Gesicherte Images nach ACR übertragen, kubeconfig und Dienstidentitäten
   aktualisieren, Schema und eingeschränkte SQL-Rolle einrichten und Notizen nur
   in eine leere Tabelle restaurieren. Daten werden nicht durch DELETE/TRUNCATE ersetzt.
6. API, HPA, Service, CSI und Gateway aufbauen. Verschlüsselten Zertifikatszustand
   vor dem Gateway-Start restaurieren und öffentliches HTTPS verifiziert prüfen.
7. Öffentliche GitHub-Client-ID auf die neue Lieferidentität aktualisieren.
   Datenhash, neuen Cluster, API, Admin-Geheimnis-Verweigerung und echte KI prüfen.
   Terraform muss ohne Änderungen enden. Erst danach Cloud-Auslieferung freigeben.

Ein neuer Zyklus entfernt alte Erfolgsmarkierungen genau einmal. Ein wiederholter
Bootstrap im selben Zyklus vergleicht bereits restaurierte Daten nur noch mit
ihrem Hash. Er löscht keine vorhandenen Notizen, um einen Restore erneut zu erzwingen.
Die Fortschritte liegen in .state/lifecycle.json. Ein zweiter gleichzeitig
laufender Ablauf wird gesperrt. Eine verwaiste Terraform-Sperre nach einem
Prozessabbruch muss nach Prüfung laufender Prozesse gezielt behandelt werden;
sie wird nicht pauschal automatisch aufgehoben.

## Diese privaten Dateien unbedingt behalten

- .state/lifecycle.json und .state/evolution-release.json: aktueller Zyklus,
  Phasen und genaue Pfade zu den Sicherungen.
- artifacts/backups: verschlüsselte Journaldatei und zugehöriges Manifest.
- .secrets/backups: passender Entschlüsselungsschlüssel und verschlüsselte States.
- artifacts/recovery: genaue Imagearchive und verschlüsselter Zertifikatszustand;
  neuere Zyklen haben eigene Unterordner und überschreiben ältere Archive nicht.
- app/infra-terraform/aks.local.auto.tfvars.json: lokale öffentliche IDs/IP-Eingaben.

Das öffentliche Abgabe-ZIP und Git enthalten diese privaten Daten NICHT. Für die
Wiederherstellung vorhandener Notizen reicht ein Git-Clone allein nicht aus.
Die privaten Dateien zusätzlich geschützt außerhalb dieses PCs aufbewahren.
Schlüssel nicht mit dem Abgabepaket oder mit Screenshots weitergeben.

## Nachweise und Grenzen

- Vollständiger realer Anwendungs-Neuaufbau mit unveränderter Notiz am 19.11.:
  artifacts/history/20261119/evolution-recovery-final.json.
- Aktueller vollständiger Abbau und Azure-Inventar:
  artifacts/azure/lifecycle-down-check.json.
- Prüfung der neuen Backend-Erstellung:
  artifacts/azure/backend-recreation-check.json.
- Neue lokale Sicherheits-/Wiederaufnahmeprüfungen: tests/test_lifecycle.py;
  sie werden zusätzlich in GitHub CI ausgeführt.

Nur vorhandene protokollierte Ergebnisse sind tatsächliche Ausführungsnachweise.
Die spätere up-Aktion wird beim Abschluss dieses Kostenabbaus bewusst nicht für
einen erneuten kompletten AKS-Aufbau ausgeführt. Dieser würde die gerade
entfernten laufenden Kosten wieder einschalten. Die Komponentenwiederherstellung
ist aus dem vorherigen echten Neuaufbau belegt; die neue Backend-Erstellung
wird gesondert tatsächlich getestet und anschließend ebenfalls wieder entfernt.
Die Secret-Konfiguration enthält ein Ablaufdatum; vor einem späteren Betrieb
nach diesem Datum müssen Ablauf und Rotation mit der SQL-Rolle abgestimmt werden.
