<!-- Zweck: Ordnet die tatsächlichen Abnahmen den Pflichtkriterien des Wochenprojekts zu. -->
# LearningSteps Evolution – Abnahmestand

Stand: 19.11.2026. Die KI-Tagesaufgabe wurde laut Nutzer bereits abgegeben.
Diese Übersicht beschreibt technische Nachweise und ist keine Kursbewertung.

| Pflichtbereich | Bestätigtes Ergebnis |
| --- | --- |
| Docker und ACR | Gehärtetes Non-root-Image, lokaler Start, Digest-Prüfung und ACR-Push. |
| Terraform | Netzwerke, AKS, private PostgreSQL-Instanz, Key Vault, Foundry und Identitäten; Entra-Remote-State. |
| Geheimnisse | Ephemere/Write-only-Verarbeitung, Runtime nur einzelnes DB-Geheimnis, kein Foundry-Key. |
| CI-Sicherheitsprüfung | Vollständige Git-Historie, Quellen, Image und Terraform; HIGH/CRITICAL brechen ab. |
| Negativnachweis | Isolierte offene SSH-Regel erzeugte zwei CRITICAL-Funde; kein Apply, kein Merge. |
| Continuous Delivery | Echter erfolgreicher Push → Scans → OIDC → ACR → Digest-Rollout → öffentliches HTTPS. |
| Kubernetes | Deployment, interne API-Service-/ConfigMap-Konfiguration und öffentliches LoadBalancer-Gateway. |
| Selbstheilung | Ersatz für entfernten API-Pod nach 17,9 Sekunden; andere ursprüngliche Instanz blieb Ready. |
| Skalierung | Echter interner HTTP-Test: 2 → 4 → 2 Ready Pods, 168488 HTTP-200-Antworten, keine gemeldeten Fehler. |
| Nutzertrennung | JWT-Prüfung und Owner-Filter; echte isolierte PostgreSQL-Tests mit zwei synthetischen Identitäten. |
| KI | Drei synthetische Notizen aus AKS per Workload Identity; angemeldete eigene gespeicherte Notiz mit HTTP 200 zusammengefasst. |
| Sicherung | AES-256-GCM-Backup, tatsächlicher isolierter Restore mit Inhaltsvergleich; nichtleeres Restore-Ziel abgelehnt. |

## Vollständiger Wiederaufbau

Alle 45 Anwendungsressourcen wurden tatsächlich durch einen gespeicherten
Terraform-Destroy-Plan abgebaut. Leerer State und gelöschte drei Anwendungsgruppen
wurden unabhängig bestätigt. Der separate Remote-State-Speicher blieb bestehen.
Die Datenbank wurde neu angelegt und der eine gesicherte Eintrag mit identischem
Datenhash restauriert. Die tatsächliche zusammengeführte Abschlussprüfung ist in
`artifacts/azure/evolution-recovery-final.json` mit `passed: true` festgehalten:
neuer Cluster, zwei bereite API-Pods, gültiges HTTPS, eingeschränkte DB-Rechte,
echter KI-Zugriff über Workload Identity und Terraform ohne Änderungen. Alle
45 verwalteten Ressourcen sind wieder vorhanden; aktuelle reguläre Secret-Werte
im State sind leer.

Der Kapazitätsfehler SkuNotAvailable betraf die feste bisherige DB-Zone 3.
Ohne feste Zonenbindung wählte Azure beim erneuten Anlegen Zone 2. Der teilweise
bereits aufgebaute State blieb erhalten; es erfolgte kein unnötiger zweiter Abbau.

## Finale Übergabe

Die vertrauenswürdige Pipeline und ihre OIDC-Föderation verwenden gemeinsam main.
Der abschließende echte main-Lauf wird in
`artifacts/github/main-delivery-final.json` festgehalten. Bericht und separate
Ablauferklärung dokumentieren diese erfolgreiche Wiederaufbauabnahme. Das
Abgabepaket enthält ausgewählte sichere Nachweise und einzeln geprüfte Hashes. Eine Wochenprojekt-Kursabgabe wurde nicht
stellvertretend eingereicht.

## Bewusste Grenzen

Prometheus/Grafana ist im Projektbrief ausdrücklich optional und wurde nicht
implementiert. Ein Gateway und die kleine Datenbank besitzen keine vollständige
Produktions-HA. HPA und Pod-Recovery beweisen Komponentenverhalten, keine
unbegrenzte Kapazität oder unterbrechungsfreie Gesamtsystemverfügbarkeit.
KI-Limits sind pro Prozess, kein globaler Kostendeckel. SQL-Kennwortrotation
muss koordiniert werden. Private Restore-Schlüssel und Backups separat behalten.

## Kosten und Pause

Die zwei AKS-Knoten haben einen ermittelten reinen VM-Listenpreis von zusammen
0,4344 EUR/Stunde; weitere Azure-Dienste und Modellverbrauch kommen hinzu.
Zum normalen Pausieren AKS und PostgreSQL gezielt stoppen. PostgreSQL startet
nach sieben Tagen automatisch wieder; Speicher, ACR, IPs und weitere Ressourcen
können weiter Kosten verursachen. Kein automatischer Stopp während der Arbeit.

## Ergänzung 20.11.2026: vollständige Kostenpause

Auf Wunsch werden alle aktiven LearningSteps-Ressourcen entfernt, einschließlich
des beim ersten Wiederaufbautest noch erhaltenen State-Speichers. Der eigene
Lifecycle-Befehl erstellt beim Wiederstart auch das Backend neu. Ein frisches
verschlüsseltes Journalbackup wurde isoliert restauriert und vollständig mit
seinem Original verglichen. Historische Abnahme am 19.11. und aktuelle Abschaltung
sind getrennte Nachweise. Aktueller Inventarbeleg: lifecycle-down-check.json;
Backend-Test: backend-recreation-check.json. Neue Sicherheits-/Wiederaufnahmetests
sind in CI integriert. Der kombinierte vollständige up-Lauf wird während der
Kostenpause nicht noch einmal gestartet; siehe die genaue Testgrenze in RECOVERY.md.
