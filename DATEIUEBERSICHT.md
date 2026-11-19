<!-- Zweck: Erklärt jede eigene Datei des aktiven Repositorys einschließlich kommentarfreier Formate. -->
# Dateiübersicht – aktive LearningSteps-Quellen

Die Dateien bleiben an ihren bisherigen Pfaden, damit Importe, Terraform und Skripte weiter zusammenpassen.
JSON-Dateien erlauben keine Kommentare. Erzeugte Sperrdateien, private Eingaben, Caches und externe Pakete werden nicht nachträglich kommentiert.

| Datei | Aufgabe |
| --- | --- |
| [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) | Konfiguriert den VS-Code-Entwicklungscontainer und seine Werkzeuge. |
| [.devcontainer/docker-compose.yml](.devcontainer/docker-compose.yml) | Startet lokale Entwicklungs- und PostgreSQL-Container mit persistentem Datenvolume. |
| [.devcontainer/install-azure-cli.sh](.devcontainer/install-azure-cli.sh) | Installiert die Azure CLI für die lokale schlüssellose Entwicklungsanmeldung. |
| [.dockerignore](.dockerignore) | Begrenzt den Docker-Buildkontext auf benötigte API-Dateien und schließt Geheimnisse aus. |
| [.env-sample](.env-sample) | Zeigt ausschließlich Beispielwerte für die lokale PostgreSQL-Konfiguration. |
| [.gitattributes](.gitattributes) | Legt die Behandlung von Textdateien und Zeilenenden durch Git fest. |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | Prüft Quellen, Tests, Historie und Image und liefert nur geprüfte Images über OIDC aus. |
| [.gitignore](.gitignore) | Schließt lokale Geheimnisse, State, Buildpläne, Umgebungen und Caches aus Git aus. |
| [.vscode/launch.json](.vscode/launch.json) | Konfiguriert den Python-Debugger für den lokalen FastAPI-Start. |
| [AI-INTEGRATION.md](AI-INTEGRATION.md) | Erklärt Entra-Anmeldung, Nutzertrennung und die nachgewiesene lokale KI-Integration. |
| [CI-CD.md](CI-CD.md) | Beschreibt die GitHub-Prüfungen, OIDC-Auslieferung und deren tatsächliche Nachweise. |
| [Dockerfile](Dockerfile) | Baut das gehärtete, nicht privilegierte API-Image aus dem festgelegten Python-Basisimage. |
| [EVOLUTION.md](EVOLUTION.md) | Dokumentiert bestätigte Ergebnisse und noch offene Abnahmepunkte des Wochenprojekts. |
| [README.md](README.md) | Erklärt die Anwendung, Architektur und den Einstieg in die aktuelle Evolution-Phase. |
| [SECURITY-SCANS.md](SECURITY-SCANS.md) | Hält Scannerstände, Fehlalarme und akzeptierte beziehungsweise verworfene Image-Kandidaten fest. |
| [api/__init__.py](api/__init__.py) | Exportiert die zentralen Bausteine der LearningSteps-API. |
| [api/database_config.py](api/database_config.py) | Liest die Datenbank-URL aus Umgebung oder Geheimnisdatei und verhindert Mehrdeutigkeit. |
| [api/main.py](api/main.py) | Startet FastAPI und bindet Anmeldung, Notizrouten, KI und Probes ein. |
| [api/models/__init__.py](api/models/__init__.py) | Kennzeichnet das Paket mit den Datenmodellen der API. |
| [api/models/entry.py](api/models/entry.py) | Validiert Eingaben und Ausgaben der Lerntagebuch-Einträge. |
| [api/models/summary.py](api/models/summary.py) | Definiert das Antwortformat einer KI-Zusammenfassung. |
| [api/repositories/__init__.py](api/repositories/__init__.py) | Kennzeichnet das Paket für Datenbankzugriffe. |
| [api/repositories/interface_repository.py](api/repositories/interface_repository.py) | Definiert die gemeinsame Schnittstelle zum Speichern und Lesen von Einträgen. |
| [api/repositories/postgres_repository.py](api/repositories/postgres_repository.py) | Speichert und liest PostgreSQL-Einträge begrenzt auf den angemeldeten Nutzer. |
| [api/requirements.lock](api/requirements.lock) | Fixiert die vollständigen Python-Paketversionen für reproduzierbare Installationen. |
| [api/requirements.txt](api/requirements.txt) | Listet die direkt benötigten Python-Abhängigkeiten der API auf. |
| [api/routers/__init__.py](api/routers/__init__.py) | Kennzeichnet das Paket für die HTTP-Endpunkte. |
| [api/routers/health_router.py](api/routers/health_router.py) | Liefert minimale Liveness- und Readiness-Antworten für Kubernetes. |
| [api/routers/journal_router.py](api/routers/journal_router.py) | Stellt authentifizierte HTTP-Endpunkte zum Verwalten eigener Einträge bereit. |
| [api/routers/summary_router.py](api/routers/summary_router.py) | Erzeugt serverseitig eine KI-Zusammenfassung eigener gespeicherter Notizen. |
| [api/security/__init__.py](api/security/__init__.py) | Kennzeichnet das Paket für die Entra-Zugriffskontrolle. |
| [api/security/dependencies.py](api/security/dependencies.py) | Stellt die geprüfte Nutzeridentität als FastAPI-Abhängigkeit bereit. |
| [api/security/entra.json](api/security/entra.json) | Enthält öffentliche Entra-IDs für Tokenprüfung und Swagger-Anmeldung; keine Geheimnisse. |
| [api/security/foundry.json](api/security/foundry.json) | Enthält den öffentlichen Foundry-Endpunkt, Deploymentnamen und derzeit lokalen Anmeldemodus. |
| [api/security/identity.py](api/security/identity.py) | Validiert Entra-Zugriffstokens und extrahiert eine vertrauenswürdige Nutzeridentität. |
| [api/services/__init__.py](api/services/__init__.py) | Kennzeichnet das Paket für die Anwendungslogik. |
| [api/services/entry_service.py](api/services/entry_service.py) | Verarbeitet Notizoperationen zwischen HTTP-Routen und Repository. |
| [api/services/summary_service.py](api/services/summary_service.py) | Fasst eigene Notizen serverseitig zusammen und behandelt Notizinhalte als Daten. |
| [database/cloud_access.sql](database/cloud_access.sql) | Vergibt eingeschränkte Datenrechte an die Cloud-Anwendungsrolle. |
| [database/migrations/20261117_add_entry_owners.sql](database/migrations/20261117_add_entry_owners.sql) | Ergänzt bestehende Einträge additiv um Nutzerzuordnung und passende Indizes. |
| [database_setup.sql](database_setup.sql) | Erstellt die Eintragstabelle und Nutzerzuordnung für eine neue Datenbank. |
| [infra-terraform/.terraform.lock.hcl](infra-terraform/.terraform.lock.hcl) | Speichert automatisch erzeugte Provider-Prüfsummen; nicht manuell bearbeiten. |
| [infra-terraform/README.md](infra-terraform/README.md) | Beschreibt Terraform-Betrieb, Architekturentscheidungen und Infrastruktur-Nachweise. |
| [infra-terraform/aks.tf](infra-terraform/aks.tf) | Erstellt AKS mit Entra-Zugriff, Netzwerk, Workload Identity und Container-Registry-Rechten. |
| [infra-terraform/application-identity.tf](infra-terraform/application-identity.tf) | Bindet den API-ServiceAccount an eine Azure-Identität mit eng begrenztem Geheimniszugriff. |
| [infra-terraform/backend.tf](infra-terraform/backend.tf) | Verbindet Terraform mit dem geschützten Azure-Blob-Remote-State. |
| [infra-terraform/database-credentials.tf](infra-terraform/database-credentials.tf) | Verwaltet Datenbankkennwörter und Verbindungsgeheimnis mit ephemeren beziehungsweise schreibenden Werten. |
| [infra-terraform/database-network.tf](infra-terraform/database-network.tf) | Erstellt privates Datenbanknetz, DNS, Netzregeln und Peering zu AKS. |
| [infra-terraform/database.tf](infra-terraform/database.tf) | Erstellt die private PostgreSQL-Instanz und Datenbank mit erzwungenem TLS. |
| [infra-terraform/foundry.tf](infra-terraform/foundry.tf) | Verwaltet die übernommene Foundry-Ressourcengruppe und das schlüssellos konfigurierte Konto. |
| [infra-terraform/github-actions.tf](infra-terraform/github-actions.tf) | Vergibt OIDC-Föderation und begrenzte Azure-/Kubernetes-Auslieferungsrechte an GitHub Actions. |
| [infra-terraform/key-vault.tf](infra-terraform/key-vault.tf) | Erstellt Key Vault mit rollenbasiertem Zugriff und Netzbeschränkungen. |
| [infra-terraform/network.tf](infra-terraform/network.tf) | Erstellt die Evolution-Ressourcengruppe sowie VNet und Subnetze. |
| [infra-terraform/providers.tf](infra-terraform/providers.tf) | Konfiguriert AzureRM und die Erzeugung beziehungsweise Verwendung von Zufallswerten. |
| [infra-terraform/public-access.tf](infra-terraform/public-access.tf) | Erstellt die öffentliche feste IP und den DNS-Namen für HTTPS. |
| [infra-terraform/registry.tf](infra-terraform/registry.tf) | Erstellt die Azure Container Registry ohne aktiviertes Administratorkonto. |
| [infra-terraform/variables.tf](infra-terraform/variables.tf) | Definiert die Eingaben für AKS-Verwaltung und erlaubten Entwicklerzugang. |
| [infra-terraform/versions.tf](infra-terraform/versions.tf) | Legt die benötigten Terraform- und Provider-Versionen fest. |
| [k8s-manifests/README.md](k8s-manifests/README.md) | Erklärt Kubernetes-Ressourcen sowie Betriebs- und Abnahmeprüfungen. |
| [k8s-manifests/configmap.yaml](k8s-manifests/configmap.yaml) | Stellt öffentliche API-Konfiguration und den Pfad zur Geheimnisdatei bereit. |
| [k8s-manifests/deployment.yaml](k8s-manifests/deployment.yaml) | Definiert die API-Pods mit Probes, Ressourcenlimits und CSI-Geheimnismount. |
| [k8s-manifests/diagnostics/db-login-check.yaml](k8s-manifests/diagnostics/db-login-check.yaml) | Definiert einen kurzlebigen Diagnose-Pod für kontrollierte Datenbank-Anmeldetests. |
| [k8s-manifests/diagnostics/db-network-check.yaml](k8s-manifests/diagnostics/db-network-check.yaml) | Prüft privates Datenbank-DNS, TCP und TLS ohne SQL-Anmeldung. |
| [k8s-manifests/diagnostics/workload-access-check.yaml](k8s-manifests/diagnostics/workload-access-check.yaml) | Definiert einen Diagnose-Pod für Workload Identity und den eingeschränkten CSI-Mount. |
| [k8s-manifests/gateway/README.md](k8s-manifests/gateway/README.md) | Erklärt HTTPS-Gateway, Zertifikatsvolume, Betrieb und verbleibende Neuaufbaugrenzen. |
| [k8s-manifests/gateway/traefik.yaml](k8s-manifests/gateway/traefik.yaml) | Definiert das öffentliche HTTPS-Gateway samt Zertifikatsvolume und LoadBalancer. |
| [k8s-manifests/hpa.yaml](k8s-manifests/hpa.yaml) | Skaliert die API CPU-abhängig zwischen zwei und vier Replikaten. |
| [k8s-manifests/namespace.yaml](k8s-manifests/namespace.yaml) | Erstellt den Anwendungsnamespace mit eingeschränkten Pod-Sicherheitsregeln. |
| [k8s-manifests/service.yaml](k8s-manifests/service.yaml) | Erreichbar macht die API ausschließlich innerhalb des Clusters über einen Service. |
| [k8s-manifests/workload-access.json](k8s-manifests/workload-access.json) | Enthält wiederverwendbaren ServiceAccount und CSI-Konfiguration mit öffentlichen IDs. |
| [scripts/check_aks_vm_price.py](scripts/check_aks_vm_price.py) | Fragt öffentliche Azure-Listenpreise für die gewählte AKS-VM-Größe ab. |
| [scripts/check_api_rollout.py](scripts/check_api_rollout.py) | Prüft API-Replikate, interne Erreichbarkeit, Authentifizierung und HPA-Messwerte lesend. |
| [scripts/check_hpa_scaling.py](scripts/check_hpa_scaling.py) | Erzeugt begrenzte HTTP-Last und prüft Hochskalierung sowie Rückkehr zu zwei API-Pods. |
| [scripts/check_https_access.py](scripts/check_https_access.py) | Prüft öffentliches HTTPS mit gültigem Zertifikat und geschützten Notizendpunkten. |
| [scripts/check_pod_recovery.py](scripts/check_pod_recovery.py) | Entfernt einen API-Pod und weist dessen automatische bereite Ersatzinstanz nach. |
| [scripts/check_postgres_price.py](scripts/check_postgres_price.py) | Fragt öffentliche Preispositionen für die PostgreSQL-Kostenplanung ab. |
| [scripts/check_private_db_login.py](scripts/check_private_db_login.py) | Prüft private Datenbankanmeldung über TLS mit einem temporären Diagnose-Pod. |
| [scripts/check_workload_access.py](scripts/check_workload_access.py) | Prüft CSI-Geheimniszugriff, App-Datenbankanmeldung und Ablehnung des Admin-Geheimnisses. |
| [scripts/ci_deploy.py](scripts/ci_deploy.py) | Liefert in vertrauenswürdigen GitHub-Läufen einen geprüften Image-Digest über AKS Run Command aus. |
| [scripts/ci_tests.py](scripts/ci_tests.py) | Führt CI-Tests ausschließlich gegen die vorgesehene isolierte Testdatenbank aus. |
| [scripts/configure_cloud_database.py](scripts/configure_cloud_database.py) | Richtet Cloud-Datenbankschema und eingeschränkte App-Rolle ohne Notizlöschung ein. |
| [scripts/configure_https_login.py](scripts/configure_https_login.py) | Prüft und ergänzt gezielt den öffentlichen Swagger-Rückruf in Entra. |
| [scripts/deploy_https_gateway.sh](scripts/deploy_https_gateway.sh) | Prüft den Gateway-Image-Digest und liefert das HTTPS-Manifest nach AKS aus. |
| [scripts/prepare_aks_local.py](scripts/prepare_aks_local.py) | Ermittelt einmalig lokale Entra-Nutzer-ID und öffentliche Entwickler-IP ohne Azure-Schreibzugriff. |
| [scripts/prove_security_gate.py](scripts/prove_security_gate.py) | Erzeugt einen isolierten unsicheren Test-Commit zum Nachweis des CI-Sicherheitsabbruches. |
| [scripts/refresh_developer_access.py](scripts/refresh_developer_access.py) | Prüft die aktuelle Entwickler-IP und bereitet optional einen eng begrenzten Terraform-Zugangsplan vor. |
| [scripts/scan_gateway.sh](scripts/scan_gateway.sh) | Prüft das festgelegte Gateway-Image auf HIGH-/CRITICAL-Schwachstellen ohne Bereitstellung. |
| [scripts/scan_git_history.py](scripts/scan_git_history.py) | Prüft alle lokal verfügbaren Git-Verweise auf Geheimnisse, ohne lokale Arbeitsgeheimnisse einzubinden. |
| [scripts/scan_iac.sh](scripts/scan_iac.sh) | Prüft eine temporäre Kopie der Terraform-Quellen auf HIGH-/CRITICAL-Fehlkonfigurationen. |
| [security/gitleaks-reviewed-fingerprints.txt](security/gitleaks-reviewed-fingerprints.txt) | Erlaubt ausschließlich einzeln geprüfte historische Docker-Tag-Fehlalarme. |
| [start.sh](start.sh) | Startet FastAPI für die lokale Entwicklung mit der vorhandenen Python-Umgebung. |
| [tests/README.md](tests/README.md) | Erklärt die aktuellen Tests und ihre Voraussetzungen sowie Aussagegrenzen. |
| [tests/check_container_smoke.py](tests/check_container_smoke.py) | Prüft gehärteten Containerstart und Ablehnung anonymer geschützter API-Anfragen. |
| [tests/check_foundry_connection.py](tests/check_foundry_connection.py) | Prüft ausdrücklich eine echte Foundry-Modellantwort ohne Tokenausgabe. |
| [tests/check_secret_exposure.py](tests/check_secret_exposure.py) | Prüft Quellmuster und lokale Logs auf Geheimnisse beziehungsweise bekannte Testnotizinhalte. |
| [tests/test_ci_delivery.py](tests/test_ci_delivery.py) | Prüft Auslieferungsgrenzen und sichere Fehlerbehandlung mit simulierten Cloud-Antworten. |
| [tests/test_identity.py](tests/test_identity.py) | Prüft Entra-Tokenvalidierung einschließlich Ablehnung ungültiger Identitäten. |
| [tests/test_notes_isolation.py](tests/test_notes_isolation.py) | Prüft echte HTTP-/SQL-Nutzertrennung in einer eigenen lokalen Testdatenbank. |
| [tests/test_runtime.py](tests/test_runtime.py) | Prüft Konfigurationsquellen sowie sichere Liveness- und Readiness-Antworten. |
| [tests/test_summary.py](tests/test_summary.py) | Prüft Zusammenfassungslogik und sichere Begrenzung der Modellanfragen. |

Diese Übersicht ist selbst die Erklärung der Dateizwecke. Nicht im Quellenkatalog: `.git`, `venv`, `.terraform`, private `.env`/lokale `.tfvars.json`. Diese verwalteten beziehungsweise privaten Dateien bleiben unverändert.

## Abschluss und Wiederherstellung

| Datei | Aufgabe |
| --- | --- |
| [RECOVERY.md](RECOVERY.md) | Beschreibt Sicherung, Abbau, Wiederherstellung und Aussagegrenzen. |
| [scripts/cloud_data_backup.py](scripts/cloud_data_backup.py) | Verschlüsselt alle Anwendungsdaten und prüft isolierten beziehungsweise leeren Restore. |
| [scripts/recovery.py](scripts/recovery.py) | Sichert Images/Zertifikate und orchestriert den kontrollierten Wiederaufbau. |

## Abschluss und Abgabe

| Datei | Aufgabe |
| --- | --- |
| scripts/check_recovery_final.py | Bündelt tatsächliche Neuaufbau-, Datenhash-, HTTPS- und KI-Abnahme. |
| scripts/build_reports.py | Erzeugt Bericht und separate Ablauferklärung als Red-Blue-PDF und Markdown. |
| scripts/package_submission.py | Packt versionierte Quellen und ausgewählte sichere Nachweise mit Prüfsummen. |
| docs/LearningSteps-Evolution-Projektbericht.md | Editierbare Quelle des finalen technischen Berichts. |
| docs/LearningSteps-Evolution-Ablauf.md | Editierbare Quelle der separaten verständlichen Anleitung. |
