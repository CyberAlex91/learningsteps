<!-- Zweck: Erklärt die aktuelle Terraform-Infrastruktur, ihre Schutzgrenzen und den kontrollierten Betrieb. -->
# Azure-Infrastruktur mit Terraform

## Verwalteter Umfang

| Bereich | Ressourcen und Aufgabe |
| --- | --- |
| rg-learningsteps-evolution, Germany West Central | AKS, ACR Basic, öffentliche Web-IP, Key Vault, Dienstidentitäten und AKS-Netz. |
| rg-learningsteps-data, West Europe | Private PostgreSQL-Instanz, Datenbank, NSG, VNet und private DNS. |
| rg-learningsteps-ai, Germany West Central | Foundry-Konto, gpt-5-mini-Deployment und Inferenzrechte. |
| rg-learningsteps-tfstate | Separat eingerichteter Remote-State-Speicher; bewusst NICHT im Anwendungs-State. |

AKS hat zwei D4s_v6-Systemknoten in Zonen 2/3. Die API ist mit zwei Replikaten
und HPA 2–4 eingerichtet. Der Cluster nutzt Entra/Azure RBAC, Workload Identity,
CSI und deaktivierte lokale Admin-Anmeldung. Entwicklerzugriff auf die AKS-API
bleibt auf die aktuelle öffentliche /32 begrenzt. GitHub-Runner benötigen durch
Run Command keine pauschale Firewallfreigabe.

AKS-VNet 10.60.0.0/16 und Daten-VNet 10.62.0.0/16 sind gepeert.
Die Datenbank liegt im delegierten Subnetz 10.62.1.0/24, ist nicht öffentlich
zugänglich und verlangt TLS mit Hostnamen-/CA-Prüfung. Der früh vorgesehene
Germany-Datenbank-Subnetzbereich ist weiterhin deklarativ vorhanden; der reale
Datenbankserver liegt wegen der bestätigten Subscription-Beschränkung in West Europe.

Key Vault verwendet RBAC, Purge Protection und eine Netzwerk-Allowlist.
Kennwörter werden ephemer erzeugt und über Write-only-Argumente gespeichert.
Die API darf nur ihr einzelnes Verbindungsgeheimnis lesen; Adminzugriff wurde
explizit verweigert getestet. SQL verwendet eine eingeschränkte App-Rolle.
Die API-Identität hat zusätzlich nur das erforderliche Foundry-Inferenzrecht.
Keine Zugangsschlüssel als Terraform-Outputs.

## State und private Eingaben

Backend: lsstatealex0ad5f630 / tfstate / evolution.terraform.tfstate.
Entra-Anmeldung, gemeinsame Speicherschlüssel deaktiviert, Blob-Versionierung
und sieben Tage Löschschutz. `backend.tf` enthält nur öffentliche Konfiguration.
Die lokale nicht versionierte Variablendatei enthält Entwickler-Objekt-ID und
aktuelle IP. State, Caches und gespeicherte Pläne gehören weder in Git noch Abgabe.
Die Provider-Prüfsummen `.terraform.lock.hcl` werden dagegen versioniert.

## Reguläre Änderung

**Ort: WSL-Terminal in VS Code**, übergeordneter LearningSteps-Ordner.

```bash
az account show --query '{Subscription:name,Status:state}' -o json
terraform -chdir=app/infra-terraform fmt -check
terraform -chdir=app/infra-terraform validate
terraform -chdir=app/infra-terraform plan -out=reviewed.tfplan
# Vollständigen Plan lesen und prüfen, dann:
terraform -chdir=app/infra-terraform apply reviewed.tfplan
terraform -chdir=app/infra-terraform plan
```

Die Subscription muss Alexander Plank - Sub sein. Das Ende einer gewöhnlichen
Änderung ist ein Plan ohne Unterschiede. Nach Quelländerungen oder einem
fehlgeschlagenen Apply einen neuen Plan erzeugen; alte Pläne nicht blind wiederholen.
`refresh_developer_access.py` prüft einen IP-Wechsel und bereitet mit --prepare
nur die eng begrenzte /32-Änderung vor. Niemals 0.0.0.0/0 als schnelle Reparatur.

Azure setzt den Tag created-on per Richtlinie. Unsere Tags werden aus stabilen
lokalen Werten gebildet; nur dieser externe Zeitstempel wird ignoriert. Dadurch
verändert ein später eingelesener Resource-Group-Tag keinen laufenden Plan mehr.

## Wiederaufbau und Kapazität

Siehe [RECOVERY.md](../RECOVERY.md). Der tatsächliche Test umfasst einen
vollständigen Abbau aller 45 Anwendungsressourcen, Neuaufbau und Datenrestore.
Der separate State-Speicher bleibt erhalten. Softgelöschter Foundry-Account und
purgegeschützter Key Vault werden kontrolliert wiederhergestellt.

Im Wiederaufbautest lehnte Azure die zuvor erfolgreiche feste Datenbankzone 3
mit SkuNotAvailable ab. `database.tf` verwendet deshalb keine feste Zone mehr;
Azure darf die verfügbare Zone für den einzelnen Laborserver auswählen.
Eine SKU-Auflistung ist keine verbindliche Kapazitätszusage. Bei einem Teilfehler
zuerst den State und die tatsächliche Ressource prüfen, dann ausschließlich die
fehlenden Teile neu planen. Keinen zweiten vollständigen Abbau starten.

Die drei `prevent_destroy`-Sperren für Datenbank und übernommene Foundry-Ressourcen
werden ausschließlich nach verifizierten Backups für den kontrollierten Abbau
vorübergehend aufgehoben und anschließend wieder gesetzt. Der finale Plan muss
wieder ohne Änderungen sein. Automatische SQL-Kennwortrotation, Datenbank-HA und
Gateway-HA sind nicht implementiert.
