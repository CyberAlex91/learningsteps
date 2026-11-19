<!-- Zweck: Beschreibt Sicherung, kontrollierten Infrastruktur-Abbau und Wiederherstellung einschließlich der absichtlich erhaltenen Schutzmechanismen. -->
# Evolution sichern und vollständig wiederherstellen

## Umfang und Voraussetzungen

Die Anwendung nutzt eine öffentliche Tabelle `entries`. Die logische Sicherung
enthält alle Spalten und Zeilen einschließlich JSON-Inhalt, Nutzerkennungen und
Zeitstempeln. Sie ist kein allgemeines PostgreSQL-Clusterbackup: Schema und Rollen
kommen aus `database_setup.sql` und `configure_cloud_database.py`. Zusätzliche
öffentliche Tabellen lassen den Export vorsorglich abbrechen.

Alle folgenden Befehle: **WSL-Terminal in VS Code**, Projektordner LearningSteps.
Benötigt: angemeldete Azure CLI, GitHub CLI, Terraform, kubectl/kubelogin,
Docker Desktop sowie Python mit `cryptography` und `PyYAML`. Die Python-Module
sind auf diesem PC vorhanden; unter Ubuntu lassen sie sich als `python3-cryptography`
und `python3-yaml` installieren. API-Paketabhängigkeiten bleiben separat gesperrt.

```bash
export PATH="$HOME/.local/share/learningsteps-tools/bin:$PATH"
export KUBECONFIG="$HOME/.kube/learningsteps-evolution.yaml"
```

## Sicherung vor jeder Zerstörung

```bash
python3 app/scripts/cloud_data_backup.py backup
python3 app/scripts/cloud_data_backup.py check --manifest PFAD_ZUM_AUSGEGEBENEN_MANIFEST
python3 app/scripts/recovery.py prepare --backup PFAD_ZUM_AUSGEGEBENEN_MANIFEST
```

Der erste Schritt liest alle Anwendungsdaten über verifiziertes TLS in einen
kurzlebigen Diagnose-Pod und verschlüsselt sie lokal mit AES-256-GCM. Kennwörter
bleiben in Arbeitsspeicher/Standardinput. Der Schlüssel liegt nur unter
`.secrets/backups`, das Chiffrat unter `artifacts/backups`. Die Windows-ACL des
Schlüsselordners ist auf den Benutzer, SYSTEM und Administratoren beschränkt.
Schlüssel und verschlüsselte Sicherung getrennt und außerhalb der Abgabe behalten.

Der zweite Schritt restauriert in eine neue zufällig benannte Datenbank,
vergleicht alle Inhalte per SHA-256 und entfernt ausschließlich diese Testdatenbank.
Die reguläre Datenbank wird dabei nicht beschrieben. `prepare` sichert zusätzlich
die ausgelieferten API-/Gateway-Images mit Digests und verschlüsselt den privaten
ACME-/Zertifikatszustand. Die Wiederherstellung setzt das Vorhandensein dieser
lokalen Dateien voraus: Terraform allein enthält keine Anwendungsdaten oder Images.

## Abbau und Infrastruktur wieder anlegen

Vor dem Abbau die API in ein Wartungsfenster nehmen und mit `verify-current`
den aktuellen Tabelleninhalt nochmals gegen die getestete Sicherung vergleichen.
Es dürfen während des Abbaus keine neuen Notizen entstehen. Gateway-Service und
Gateway-PVC kontrolliert vor AKS entfernen, damit Azure LoadBalancer und Disk
ordnungsgemäß freigegeben werden.

```bash
python3 app/scripts/recovery.py plan-destroy
```

Dieser Schritt verlangt geprüfte Daten-, Image- und Zertifikatssicherungen,
speichert die ursprünglichen Terraform-Schutzdefinitionen und deaktiviert nur die
drei bisherigen `prevent_destroy`-Übernahmesperren. Er erzeugt einen gespeicherten
Destroy-Plan und eine Liste der betroffenen Projektressourcen. Der State-Speicher
`rg-learningsteps-tfstate` ist ausdrücklich nicht im verwalteten Anwendungs-State.
Den vollständigen Plan prüfen, bevor er angewendet wird.

```bash
terraform -chdir=app/infra-terraform apply evolution-destroy.tfplan
terraform -chdir=app/infra-terraform state list
python3 app/scripts/recovery.py infrastructure
python3 app/scripts/recovery.py bootstrap
python3 app/scripts/recovery.py restore-guards
terraform -chdir=app/infra-terraform plan
```

`infrastructure` verlangt nach dem vollständigen Abbau einen leeren State.
Es erstellt die Foundry-Ressourcengruppe, stellt das absichtlich softgelöschte
Foundry-Konto über Azure CLI wieder her, importiert es in Terraform und führt
den vollständigen Terraform-Apply aus. Der Key Vault wird vom Provider aus
Soft-Delete wiederhergestellt. Purge Protection bleibt aktiviert; es gibt keinen
Versuch, Schutzfristen zu umgehen. Damit sind geschützte Serviceidentitäten
wiederhergestellt statt unwiederbringlich gepurgt. Der Modellstand und beide
Modellzugriffsrollen werden wieder durch Terraform verwaltet.

`bootstrap` stellt die archivierten Images in ACR wieder her und vergleicht die
AMD64-Manifeste, aktualisiert die dedizierte kubeconfig, richtet das DB-Schema
und eingeschränkte App-Rechte ein und restauriert nur in eine leere Zieltabelle.
Vorhandene Einträge lassen den Restore abbrechen; kein DELETE/TRUNCATE im Restore.
Anschließend werden SA/CSI, API, HPA, Gateway und Zertifikatsvolume aufgebaut.
Der gespeicherte private Zertifikatszustand wird verschlüsselt transportiert und
vor dem Gateway-Start restauriert. Der TLS-Router wird erst nach stabiler
öffentlicher HTTP-Erreichbarkeit dynamisch aktiviert. Neue Zertifikatsbeantragung
ist für diesen Wiederherstellungslauf nicht erforderlich. HTTPS bleibt CA-geprüft.
Die öffentliche GitHub-Client-ID wird auf die neu erzeugte CI-Identität aktualisiert.

`restore-guards` setzt die ursprünglichen Schutzsperren wieder ein. Der abschließende
Plan soll `No changes` melden. Anschließend API-/Identitätsprüfungen und echte
KI-Anfrage ausführen sowie die eigene restaurierte Notiz im Browser prüfen.
Erst die protokollierte tatsächliche Ausführung beweist den Neuaufbau; Skripte
allein sind noch kein Wiederherstellungsnachweis.

## Kosten und normale Pausen

Für eine normale Pause nicht die gesamte Infrastruktur löschen. AKS und PostgreSQL
können gestoppt werden; PostgreSQL startet nach sieben Tagen automatisch wieder.
Storage, ACR, DNS, öffentliche IP und gegebenenfalls LoadBalancer/Disks verursachen
weiterhin Restkosten. Den Modellzugriff bei Bedarf über einen neuen geprüften Plan
mit `enable_ai_summary=false` entfernen; ein gewöhnlicher späterer Plan aktiviert
wegen des Defaultwerts das Modell wieder. Nach einer Änderung der öffentlichen IP
zuerst `refresh_developer_access.py` verwenden, keine Zugangsbereiche auf /0 öffnen.
