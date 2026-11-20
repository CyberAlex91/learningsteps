<!-- Zweck: Technischer Projektbericht des LearningSteps-Evolution-Projekts mit tatsächlichen Nachweisen. -->
# LearningSteps Evolution

Alexander Plank | 20.11.2026 | Finale Projektfassung

## Ergebnis und Geltungsbereich

LearningSteps wurde von einer manuell betriebenen Anwendung zu einem durch Terraform verwalteten Cloud-System mit automatischer Auslieferung weiterentwickelt. FastAPI läuft in gehärteten Containern auf AKS. PostgreSQL ist privat erreichbar; Nutzer melden sich über Entra an. Eine serverseitige KI fasst ausschließlich die gespeicherten eigenen Notizen zusammen.

Der vollständige Wiederaufbau ist nachgewiesen. Dieser Betriebsnachweis stammt vom 19.11.2026. Aktuell ist die Cloud auf Wunsch vollständig abgebaut, einschließlich State-Speicher. Der Abbau wurde am 20.11.2026 gesondert geprüft; die folgende Architektur beschreibt den wiederherstellbaren Betriebsstand.

| Abnahme | Tatsächlicher Nachweis |
| --- | --- |
| Öffentliche Anwendung | Vertrauenswürdiges HTTPS, Entra-Anmeldung sowie Anlage und Abruf einer eigenen Cloud-Notiz. |
| Continuous Delivery | Codeänderung über GitHub-Prüfungen, OIDC, ACR und AKS bis zur öffentlichen API ausgeliefert. |
| Sicherheitsabbruch | Absichtlich offene SSH-Regel: zwei CRITICAL-Befunde, Scanner-Exitcode 1. |
| Selbstheilung und Skalierung | API-Ersatzpod nach 17,9 Sekunden; Lasttest mit 2 → 4 → 2 bereiten Pods. |
| Cloud-KI | Drei synthetische RAM-Notizen per Workload Identity; anschließend gespeicherte eigene Notiz mit HTTP 200 zusammengefasst. |

Die optionale Prometheus-/Grafana-Erweiterung wurde nicht implementiert. Die Datenbankrechte sind auf die Anwendung begrenzt; die Trennung einzelner Nutzer erfolgt in der API und wurde mit synthetischen Identitäten getestet. Dieser Bericht beschreibt einen kontrollierten Lernprojektstand, keine uneingeschränkte Produktionsfreigabe.

## Vollständiger Kostenabbau und Wiederstart

Stand 20.11.2026: Das Azure-Inventar meldet null aktive LearningSteps-Ressourcen. Alle fünf Projektgruppen einschließlich rg-learningsteps-tfstate wurden entfernt. Die Website ist deshalb aktuell offline. Historische Abnahmen bleiben gültige Nachweise des zuvor laufenden Systems.

| Aktion | Bedeutung |
| --- | --- |
| up | Backend, Infrastruktur, Images, Notizen und HTTPS wiederherstellen; danach entstehen erneut Azure-Kosten. |
| down | Frische geprüfte Sicherung erzeugen und sämtliche eigenen Azure-Ressourcen einschließlich Backend entfernen. |
| check | Sicherungen lokal entschlüsseln und prüfen; keine Cloud-Ressourcen starten. |
| status | Azure-Inventar nur lesen; nichts neu anlegen. |

Ort: WSL-Terminal in VS Code, Projektordner LearningSteps. Für eine spätere Nutzung genügt der erste Befehl. Der zweite ist für den erneuten vollständigen Abbau nach der Nutzung vorgesehen:

```bash
python3 app/scripts/lifecycle.py up
python3 app/scripts/lifecycle.py down
```

Alternativ startet scripts/LearningSteps.ps1 die gewünschte Aktion aus PowerShell und führt Azure weiterhin in WSL aus. Docker Desktop wird bei Bedarf lokal gestartet. Angemeldete Azure-/GitHub-CLI und die privaten Wiederherstellungsdateien bleiben Voraussetzungen. Ein Git-Clone oder das öffentliche Abgabe-ZIP allein enthält deine gesicherten Notizen und Schlüssel nicht.

Die frische Datensicherung wurde tatsächlich isoliert restauriert und vollständig verglichen. Der neue Backend-Aufbau wird separat geprüft und anschließend wieder entfernt. Der gesamte Anwendungs-Neuaufbau ist aus dem realen Lauf vom 19.11. belegt; ein erneuter kompletter up-Lauf am Ende des Kostenabbaus wurde bewusst nicht ausgeführt, weil er wieder laufende Ressourcen anlegen würde.

Die Automatik speichert ihren Fortschritt und setzt alte Restore-Markierungen nur einmal je neuem Zyklus zurück. Nach erfolgreicher Wiederherstellung wird die Cloud-Auslieferung wieder freigegeben; während des Abbaus bleibt LEARNINGSTEPS_CLOUD_ENABLED=false. Prüfungen können weiter laufen, ohne Azure neu zu befüllen.

Nachweise: artifacts/azure/lifecycle-down-check.json und backend-recreation-check.json. Details und Voraussetzungen: RECOVERY.md. Entra-Anmelderegistrierungen bleiben erhalten. Softgelöschte Standarddienste können noch als Wiederherstellungsobjekte sichtbar sein; vergangene Abrechnung kann verzögert erscheinen.

## Architektur und Kommunikationswege

Browser
Entra-Anmeldung â†’ Traefik
öffentliches HTTPS â†’ FastAPI auf AKS
interner Service â†’ PostgreSQL
privates Netz

Der Browser erreicht nur das HTTPS-Gateway. Traefik entschlüsselt HTTPS und leitet an den internen ClusterIP-Service der API weiter. Die API prüft das Entra-Zugriffstoken und führt Datenbankoperationen mit einer eingeschränkten SQL-Rolle aus. PostgreSQL besitzt keinen öffentlichen Datenzugang.

Der AKS-Cluster und sein VNet liegen in Germany West Central. Für PostgreSQL war die Bereitstellung in dieser Subscription dort eingeschränkt; deshalb liegt die private Datenumgebung in West Europe. Die beiden VNets sind durch Peering verbunden. Die dokumentierte Einschränkung betrifft die geprüfte Subscription und ist keine allgemeine Aussage über die Region.

| Netzbereich | Aufgabe |
| --- | --- |
| 10.60.0.0/16 | Evolution-VNet; AKS-Subnetz 10.60.0.0/22. |
| 10.62.0.0/16 | Daten-VNet in West Europe; delegiertes DB-Subnetz 10.62.1.0/24. |
| 10.61.0.0/16 | Interne Kubernetes-Serviceadressen; keine direkt aus dem Internet erreichbaren API-Pods. |
| Port 80 und 443 | ACME/HTTPS-Weiterleitung und öffentlicher HTTPS-Zugriff am Gateway. |
| Port 5432 | PostgreSQL über das private Netz und verifiziertes TLS. |

Das einzelne Gateway mit Recreate-Strategie und RWO-Zertifikatsdisk ist bewusst keine hochverfügbare Eingangsschicht. Mehrere API-Pods schützen den Anwendungsbetrieb vor dem Ausfall eines einzelnen API-Pods; sie beseitigen nicht diese Gateway-Einschränkung.

## Werkzeuge und reproduzierbare Quellen

Azure CLI, Terraform, Git und Kubernetes-Befehle werden im WSL-Terminal von VS Code ausgeführt. Docker Desktop ist die verwendete lokale Container-Engine. Die native WSL-Docker-Engine war eine getrennte Umgebung und zeigte deshalb anfangs die bestehenden Projektcontainer nicht an.

| Quellbereich | Verantwortung |
| --- | --- |
| api/ | FastAPI, Datenmodelle, Nutzerprüfung, Datenbankzugriff und Zusammenfassungslogik. |
| infra-terraform/ | Netze, AKS, ACR, PostgreSQL, Key Vault, Identitäten, Rollen und Modell. |
| k8s-manifests/ | API, Probes, Ressourcenlimits, Services, HPA, CSI und HTTPS-Gateway. |
| scripts/ und tests/ | Auslieferung, betriebliche Abnahmen, Sicherung und Wiederherstellung. |
| .github/workflows/ci.yml | Automatische Prüfungen und vertrauenswürdige Auslieferung. |
| docs/ und RECOVERY.md | Bericht, Ablauferklärung und ausführbare Betriebsanleitung. |

Nach der Bereinigung tragen eigene kommentierbare Quelldateien kurze Zweckhinweise. JSON-Dateien, erzeugte Sperrdateien und unveränderte Messprotokolle werden nicht durch ungültige Kommentare verändert; ihre Aufgaben sind in DATEIUEBERSICHT.md beschrieben.

Git enthält Quellcode und öffentliche Konfiguration. Private .env-Dateien, Terraform-Pläne und State, lokale Schlüssel, Backups, Zertifikatsmaterial und Python-Umgebungen bleiben außerhalb der veröffentlichten Quellen. Der historische Origins-Abschluss ist als finales Paket und PDF erhalten; überholte lose VM-Skripte wurden entfernt.

## Terraform und Infrastrukturzustand

Terraform beschreibt die gewünschte Infrastruktur und vergleicht sie mit Azure. Der Remote State liegt in einem getrennten Azure-Storagekonto mit Entra-Anmeldung, deaktivierten Shared Keys, HTTPS, Versionierung sowie sieben Tagen Blob-/Container-Löschaufbewahrung. Das Backend bleibt beim Anwendungs-Neuaufbautest bewusst erhalten. Auch die bestehenden Entra-Registrierungen für API und Swagger bleiben als dokumentierte Anmeldevoraussetzungen bestehen; der Test rekonstruiert die 45 verwalteten Anwendungsressourcen, keinen leeren Entra-Tenant.

Vor jeder Änderung werden Formatierung, Validierung und der tatsächliche Plan geprüft. Der Foundry-Lauf ergänzte beispielsweise genau Modell und API-Recht: zwei neue Ressourcen, keine Änderung und keine Löschung. Der nachfolgende Plan meldete No changes. Bestehende Ressourcen und das manuelle Entwickler-Modellrecht wurden kontrolliert importiert.

```bash
terraform -chdir=app/infra-terraform fmt
terraform -chdir=app/infra-terraform validate
terraform -chdir=app/infra-terraform plan -out=reviewed.tfplan
terraform -chdir=app/infra-terraform apply reviewed.tfplan
```

Eine Azure-Richtlinie ergänzte das Tag created-on während der Bereitstellung. Die Übernahme von veränderlichen Ressourcengruppen-Tags in abhängige Ressourcen verursachte einen inkonsistenten Provider-Plan. Statische Projekt-Tags und das gezielte Ignorieren allein dieses extern gepflegten Metadatenfelds behoben den Fehler, ohne andere Infrastrukturänderungen zu verdecken.

Temporäre prevent_destroy-Sperren schützen Datenbank und Foundry während der Einrichtung. Für den vollständigen Abnahmetest werden nur diese drei bekannten Sperren nach geprüften Sicherungen kontrolliert geöffnet und anschließend wiederhergestellt. Soft-Delete und Purge Protection bleiben aktiv; der Wiederaufbau berücksichtigt sie ausdrücklich.

## Container und Schwachstellenprüfung

Das API-Image verwendet Python 3.12 auf einem festgelegten Alpine-Basisdigest. Direkte und transitive Python-Versionen sind in requirements.lock fixiert. Das Image aktualisiert Alpine-Pakete beim Build, installiert binäre Python-Pakete und läuft als Benutzer 10001. Kubernetes erzwingt ein schreibgeschütztes Rootdateisystem, entfernte Linux-Capabilities, keine Privilegienerhöhung und RuntimeDefault-Seccomp.

Dockerfile und .dockerignore begrenzen den Buildkontext auf die erforderlichen API-Dateien. Lokale Geheimnisse, private Schlüssel, Caches und Entwicklungsumgebungen gelangen nicht in das Produktionsimage. Die Azure CLI ist dort nicht installiert; die Cloud-KI verwendet Workload Identity.

| Prüfbereich | Entscheidung und Beleg |
| --- | --- |
| Debian-Kandidaten | Bookworm und Trixie wurden wegen HIGH-Befunden verworfen; keine pauschale Ausnahme. |
| Alpine-Anwendung | Paketkorrekturen, Dependency-Check, gehärteter Start und selektierter HIGH/CRITICAL-Scan bestanden. |
| Caddy-Kandidat | Zwei HIGH-Befunde im Go-Binary; nicht bereitgestellt, Konfiguration entfernt. |
| Traefik | Geprüftes v2.11.61-Image; null HIGH/CRITICAL zum Scanzeitpunkt. AMD64-Manifest und ACR-Digest verifiziert. |

Trivy prüft das tatsächlich gebaute und exportierte Image. Zwischen Scan und Auslieferung findet kein zweiter Build statt. Ein erfolgreicher Scan ist eine Aussage zum verwendeten Prüfzeitpunkt und Schweregrad, keine Garantie für die Abwesenheit aller heutigen oder zukünftigen Schwachstellen.

## Identitäten und minimale Rechte

Nutzer
Entra-Token â†’ API
prüft Identität â†’ API-ServiceAccount
Workload Identity â†’ Key Vault / Foundry
gezielte Rechte

Nutzeranmeldung und Dienstanmeldung sind zwei getrennte Grenzen. Das signaturgeprüfte Nutzer-Token bestimmt Tenant und Nutzer der angeforderten Notizen. Der Kubernetes-ServiceAccount authentifiziert dagegen die API gegenüber Azure. Eine Nutzerkennung aus einem frei wählbaren Request-Body darf diese Auswahl nicht ersetzen.

| Identität | Begrenzte Aufgabe |
| --- | --- |
| Entwickler | Terraform-Verwaltung und kontrollierte lokale Werkzeuge; Entra statt veröffentlichter Schlüssel. |
| AKS-Kubelet | Images mit AcrPull aus der Projektregistry laden. |
| API-Workload | Nur das DB-URL-Geheimnis lesen und am Foundry-Konto Modellinferenz ausführen. |
| GitHub-Auslieferung | AcrPush plus AKS Run Command; Deployment-Datenaktionen nur im Namespace learningsteps. |
| Gateway | Keine Azure-Identität, keine DB-Konfiguration, keine Token- oder Notiz-Accesslogs. |

Die API liest den Admin-Datenbankschlüssel nicht. Ein echter Workload-Test bestätigte sowohl App-Anmeldung über TLS als auch ForbiddenByRbac beim Versuch, das Admin-Geheimnis zu lesen. Das schließt eine bloße Übernahme von Entwicklerrechten als Testersatz aus.

## Automatische Auslieferung mit GitHub

Git-Push â†’ Tests und Scans â†’ geprüftes Image â†’ OIDC und ACR â†’ AKS-Rollout

Jeder Push startet drei voneinander unabhängige Prüfbereiche. Der Qualitätsjob installiert gesperrte Abhängigkeiten, prüft Python-Konstrukte und führt Unit- sowie echte PostgreSQL-Nutzertrennungstests aus. Die Testdatenbank ist kurzlebig und enthält ausschließlich synthetische Daten. Zielprüfung und separate Datenbanknamen verhindern eine Verwechslung mit dem Journal.

Der Quellenjob prüft aktuelle Dateien und die vollständig gefetchte Git-Historie auf Geheimnisse sowie Terraform auf HIGH-/CRITICAL-Fehlkonfigurationen. Der Imagejob baut das Produktionsimage, prüft nicht privilegierten Start und anonyme Zugriffsablehnung und scannt das identische Imagearchiv. Erst alle drei erfolgreichen Jobs erlauben die gesonderte Auslieferung.

Das Imagearchiv, seine SHA-256-Prüfsumme und die Imagekennung wechseln als Artefakt desselben Workflow-Laufs in den Lieferjob. Dieser prüft Archiv und Inhalt vor der Azure-Anmeldung, nutzt kurzlebige GitHub-OIDC-Anmeldung, überträgt das unveränderte Image und vergleicht den ACR-Digest. AKS wird mit dem unveränderlichen Digest aktualisiert; Rollout und öffentliches HTTPS werden nachgeprüft.

Nur der vertrauenswürdige Repository-/Branch-Kontext erhält die Azure-Föderation und id-token:write. Pull Requests und andere Branches führen keine privilegierte Auslieferung aus. Actions und Scanner sind auf überprüfte Commit- beziehungsweise Image-Digests festgelegt. Der getestete Implementierungsweg verwendet Azure AKS Run Command, ohne die API-Firewall für beliebige GitHub-Runner-IP-Adressen zu öffnen.

Erfolgreiche Läufe: 44534120752 mit Historien-Scan und 44536752654 mit Cloud-KI-Code. Der Lauf 44543103953 bestätigte die Backup-/Wiederaufbauhelfer vor dem Wartungsfenster.

## Sicherheitsgrenzen und Negativnachweise

Der absichtliche Sicherheitsfehler lag in einem isolierten Proof-Branch: Eine Netzwerkregel erlaubte SSH aus 0.0.0.0/0. Terraform wurde daraus nie angewendet. Trivy meldete AZU-0047 und AZU-0050 als CRITICAL und beendete den Prüfschritt mit Exitcode 1. Der Workflow blieb fehlgeschlagen; die Auslieferung wurde übersprungen.

Der Proof-Branch war zusätzlich grundsätzlich von der privilegierten Auslieferung ausgeschlossen. Der Lauf belegt deshalb unmittelbar die Erkennung und den Fehlerstatus des Scanners, nicht allein die needs-Abhängigkeit als isolierte Ursache des übersprungenen Lieferjobs. Die Workflow-Datei verlangt unabhängig davon alle drei erfolgreichen Prüfjobs.

Gitleaks erkannte beim Historien-Scan einen öffentlichen Docker-Tag fälschlich als API-Schlüssel. Zwei historische Dokumentationsfundstellen und eine Wiederholung im Prüftext wurden anhand von Commit, Datei, Regel und Zeile einzeln geprüft. Die Ausnahme enthält nur diese drei exakten Fingerprints. Weder ganze Dateien noch die allgemeine Erkennungsregel wurden deaktiviert.

Ein echter Lieferlauf deckte eine fehlende Kubernetes-Berechtigung auf. Die vorherige Annahme, ARM Run Command würde die Kubernetes-Rechte umgehen, war falsch: In diesem Cluster wurde die Aufruferautorisierung durchgesetzt. Die Korrektur vergibt nur Deployment-Lese-/Schreibaktionen im Namespace learningsteps. Das gestattet Änderungen an Workload-Vorlagen im Namespace und ist keine auf das Imagefeld begrenzte Erlaubnis.

Private Schlüssel, Datenbankkennwörter, Foundry-Schlüssel und Bearer-Tokens werden nicht veröffentlicht. Der vom Nutzer gelieferte Swagger-Screenshot enthielt einen Authorization-Header und wurde nicht in Bericht oder Paket kopiert. Der Nachweis verwendet die separat übermittelten, tokenfreien Antwortdaten.

## Private Datenbank und Zugriffsschutz

PostgreSQL Flexible Server 15 liegt in einem delegierten Subnetz. Öffentlicher Datenzugriff ist deaktiviert. Private DNS-Verknüpfungen und Peering verbinden AKS und Datenbank. Die Netzprüfung bestätigte private Auflösung, erreichbaren TCP-Port 5432 und eine TLS-1.3-Verbindung mit überprüfter Zertifikatskette und Hostnamen.

Die Anwendung arbeitet mit learningsteps_app statt dem Administrator. Diese Rolle erhält CONNECT, Schema-USAGE sowie SELECT, INSERT, UPDATE und DELETE auf entries. Sie darf weder Rollen noch Datenbanken oder Tabellen erzeugen und besitzt keine erhöhten Rollenmitgliedschaften. Der tatsächliche Test bestätigte Tabellenrechte und die Ablehnung von CREATE TABLE.

| Datenebene | Sicherheitsmaßnahme |
| --- | --- |
| Geheimnisse | Getrennte Admin- und App-Kennwörter; API darf nur die Verbindungs-URL lesen. |
| Transport | Private Adressen und verifiziertes TLS; kein sslmode=disable und kein umgangenes Zertifikatsvertrauen. |
| Betrieb | Reguläre Verwaltung nutzt ephemere Werte und Write-only-Felder. Importausnahme und anschließende Rotation sind unten eingeordnet. |
| Nutzertrennung | Geprüfte Tenant-/Objekt-ID begrenzt sämtliche API-Operationen; fremde Eintrags-IDs werden nicht zugänglich. |
| Konfiguration | URL entweder lokal aus Umgebung oder aus der CSI-Datei; doppelte Quellen werden abgelehnt. |

Die CSI-Datei wird nur in den API-Pod gemountet; keine Kubernetes-Secret-Synchronisierung. Das Datenbankkennwort wird nicht dem Browser übergeben. Die API liest ihre Konfiguration beim Prozessstart: Eine Dateirotation erfordert weiterhin einen kontrollierten Pod-Rollout, damit laufende Verbindungen die neue Konfiguration übernehmen.

Automatisierte SQL-Kennwortrotation ist nicht Teil dieses Projekts. Die geplante Ablaufzeit verlangt eine koordinierte Aktualisierung von Key Vault, SQL-Rolle und API-Rollout. Row-Level Security wurde nicht eingerichtet; die mandantenbezogene Autorisierung liegt in der API.

## Die sichere KI-Funktion

POST /me/notes/summary akzeptiert keinen frei wählbaren Nutzer, keine externen Notiztexte und keinen eigenen Prompt. Die Route erhält die geprüfte Identität, lädt deren tatsächliche gespeicherte Notizen über den vorhandenen Service und sendet nur die benötigten Notizfelder serverseitig an Foundry.

Entra-Nutzer â†’ eigene DB-Notizen â†’ Backend-Prompt
Notizen als Daten â†’ Foundry-Modell â†’ Textantwort

Die Anweisung trennt vertrauenswürdige Regeln und nicht vertrauenswürdige Notizinhalte. Eingebettete Aufforderungen, Regeln zu ändern, fremde Daten abzurufen oder URLs aufzurufen, werden als Text behandelt. Der Modellaufruf enthält tools=[], store=false und keinen vorherigen Gesprächszustand. Eine unerwartete Werkzeugantwort wird abgelehnt. Damit existiert kein Werkzeugpfad, über den Notizinhalte zusätzliche Zugriffe auslösen könnten.

Die Eingabe ist begrenzt. Ein zu großer Gesamtbestand wird mit 413 abgelehnt, ohne still einzelne Notizen auszulassen. Timeout, leere oder unvollständige Modellantworten und Providerfehler führen zu kontrollierten Antworten ohne interne Fehlertexte. Der Minutenbegrenzer gilt pro Nutzer und Prozess; er ist kein globaler, über alle Replikate verteilter Kostenbegrenzer.

Die Cloud-API verwendet ausdrücklich WorkloadIdentityCredential. Fehlt die erwartete Cluster-Identität, wird nicht auf die CLI zurückgefallen. Lokal bleibt AzureCliCredential möglich. Das Modell gpt-5-mini, Version 2025-08-07, GlobalStandard mit Kapazität 1 und die Inferenzrechte sind in Terraform beschrieben. enable_ai_summary steuert Modell und API-Inferenzrecht gemeinsam.

## KI-Abnahme mit echten Daten

Zunächst lieferte ein echter SDK-Aufruf aus dem AKS-API-Pod eine Zusammenfassung von drei synthetischen RAM-Notizen zu Terraform-State, Kubernetes-Probes und JWT. Der protokollierte Modus war workload_identity; es gab keine CLI- oder Schlüsselanmeldung. Diese Prüfung isolierte den tatsächlichen Modellzugriff der Dienstidentität.

Anschließend führte der Nutzer den authentifizierten öffentlichen Endpunkt in Swagger aus. Die API verwendete eine gespeicherte eigene Cloud-Notiz. HTTP 200, note_count=1 und ai_generated=true wurden am 19.11.2026 um 13:57:57 UTC bestätigt.

| Gespeicherter Inhalt | Wiedergabe in der Antwort |
| --- | --- |
| Arbeit | LearningSteps läuft auf AKS und ist über HTTPS erreichbar. |
| Schwierigkeit | Zusammenspiel von Kubernetes, LoadBalancer und Zertifikaten verstehen. |
| Intention | Build, Sicherheitsprüfungen und Deployment mit GitHub Actions automatisieren. |

Die drei Abschnitte der Antwort passen zur gespeicherten Notiz. Dass GitHub Actions dort noch als nächster Schritt erscheint, ist kein Nachweis eines Projektfehlers: Die KI fasst den gespeicherten Eintrag zusammen und hat keinen Zugriff auf den aktuellen Projektfortschritt. Der Auslieferungsweg war zum Abnahmezeitpunkt bereits funktionsfähig.

Die drei synthetischen Modellnotizen und die eine gespeicherte Notiz sind unterschiedliche Nachweise. Der zweite Fall belegt den vollständigen Nutzerweg über HTTPS, Entra, API, private Datenbank und Foundry. Die frühere Tagesaufgabe wurde laut Nutzer mit Text und Screenshot eingereicht. Ein zweites echtes Entra-Nutzerkonto stand nicht zur Verfügung; Nutzertrennung wurde mit zwei signierten synthetischen Identitäten und echter Testdatenbank geprüft.

## Kubernetes und betriebliche Abnahme

Die API startet mit zwei Replikaten, CPU-/Speicher-Requests und Limits, Topologieverteilung und RollingUpdate mit maxUnavailable=0. Der interne Service verteilt Anfragen auf bereite Pods. Startup-, Liveness- und Readiness-Probes haben unterschiedliche Aufgaben: Liveness prüft nur den Prozess; Readiness prüft zeitlich begrenzt den tatsächlichen Tabellenlesezugriff.

| Versuch | Beobachtung |
| --- | --- |
| Ein API-Pod entfernt | Neuer Pod mit anderer UID nach 17,9 Sekunden bereit; weiterer ursprünglicher Pod am Abschluss bereit. |
| Begrenzte interne HTTP-Last | Zwei nicht privilegierte Lastgeneratoren rufen ausschließlich GET /health/live auf. |
| Hochskalierung | CPU-Messwert steigt; HPA erhöht von zwei auf vier bereite API-Pods. |
| Lastende | Last-Job entfernt; nach Messwertverzögerung und Stabilisierung Rückkehr zu zwei bereiten Pods. |
| Erfasste Antworten | 83.999 plus 84.489 HTTP-200-Antworten, keine gemeldeten Anfragefehler. |

341 Prozent beziehungsweise zeitweise 500 Prozent sind Anteile am CPU-Request von 100m, nicht Prozent der gesamten Maschine. Der Request ist die Bezugsgröße des HPA. Das Scale-down-Stabilisierungsfenster von 120 Sekunden und verzögerte Messwerte erklären, warum vier Pods nach Lastende vorübergehend erhalten blieben.

Der Lasttest belegt die Autoskalierungsfunktion unter synthetischer HTTP-/CPU-Last. Er prüft weder Datenbank- noch KI-Durchsatz und liefert keine belastbare Kapazitätsplanung. Die Ersatzpod-Prüfung misst Wiederbereitschaft; eine lückenlose Verfügbarkeitsmessung während dieses Versuchs wurde nicht durchgeführt.

## Verschlüsselte Datensicherung

Vor dem vollständigen Abbau wurde der einzige gespeicherte Cloud-Eintrag logisch exportiert. Die Sicherung enthält alle sechs Spalten der Tabelle entries: ID, JSON-Daten, beide Zeitstempel sowie Tenant- und Nutzerkennung. Zusätzliche öffentliche Tabellen würden den Sicherungslauf abbrechen, damit unbekannte Anwendungsdaten nicht unbemerkt fehlen.

Der Export läuft über einen kurzlebigen gehärteten Diagnose-Pod und überprüftes Datenbank-TLS. Zugangsdaten werden nur im Arbeitsspeicher beziehungsweise über Standardinput übergeben. Daten und Zertifikatszustand werden lokal mit AES-256-GCM verschlüsselt. Der Schlüssel bleibt in einem separat geschützten lokalen Ordner und wird weder in Git noch im Abgabepaket gespeichert.

| Sicherungsprüfung | Ergebnis |
| --- | --- |
| Inhalt | Ein vollständiger Datensatz einschließlich Eigentümerkennungen und Zeitstempeln. |
| Isolierter Restore | Neue zufällig benannte Testdatenbank; vollständiger Daten-SHA-256 identisch; Testdatenbank entfernt. |
| Nichtleeres Ziel | Restore in die gefüllte reguläre Tabelle ausdrücklich abgelehnt; kein Überschreiben. |
| Nachprüfung | Live-Inhalt nach dem Negativtest und nochmals im Wartungsfenster identisch zur Sicherung. |
| Release | Getestete API-/Gateway-Images und verschlüsselter ACME-Zustand zusätzlich archiviert. |

Diese Sicherung ist eine vollständige Anwendungsdatensicherung für das bekannte Ein-Tabellen-Schema, kein allgemeines PostgreSQL-Clusterbackup. SQL-Schema und Rollen werden aus dem Repository neu eingerichtet. Der Dienst schützt damit Daten unabhängig vom Azure-Server, dessen integrierte Sicherungen beim kompletten Serverabbau keine alleinige Wiederaufbaubasis darstellen sollen.

## Vollständiger Infrastrukturtest

Der vollständige Wiederaufbau ist nachgewiesen. Dieser Betriebsnachweis stammt vom 19.11.2026. Aktuell ist die Cloud auf Wunsch vollständig abgebaut, einschließlich State-Speicher. Der Abbau wurde am 20.11.2026 gesondert geprüft; die folgende Architektur beschreibt den wiederherstellbaren Betriebsstand.

Vor der Zerstörung wurden Sicherung und Rücksicherung geprüft, laufende API-Schreibzugriffe im Wartungsfenster angehalten und der Dateninhalt nochmals verglichen. Der öffentliche Kubernetes-Service und das gemountete Zertifikatsvolume wurden kontrolliert entfernt, bevor Terraform die dazugehörige Azure-Infrastruktur abbaut.

Der gespeicherte Destroy-Plan wurde auf genau 45 Anwendungsressourcen in den LearningSteps-Gruppen geprüft und anhand seiner SHA-256-Prüfsumme angewendet. Remote State und fremde Gruppen waren ausgeschlossen. Der Abbau von Key Vault und Foundry bleibt softlöschend; die Schutzmechanismen werden nicht durch Purge umgangen.

| Rekonstruktionsschritt | Prüfziel |
| --- | --- |
| Terraform | Leerer Anwendungs-State nach Abbau; vollständiger Apply nach Wiederherstellung geschützter Konten. |
| Registry | Archivierte Images erneut geladen, übertragen und AMD64-Manifeste verglichen. |
| Datenbank | Schema und App-Rolle neu eingerichtet; Daten nur in eine leere Tabelle restauriert. |
| Kubernetes | Neue Cluster-/Namespacekennungen, aktuelle kubeconfig, SA/CSI, API, Service und HPA. |
| HTTPS | Zertifikatszustand sicher restauriert; Router nach stabiler öffentlicher HTTP-Erreichbarkeit aktiviert. |
| Abschluss | Identischer Dateninhalt, API-/KI-Prüfung, kontrollierte CI-Identität und Terraform No changes. |

Der unterbrochene Apply hinterließ zwei bereits erstellte Ressourcen außerhalb des gespeicherten State. Nach Prüfung, dass kein Terraform-Prozess mehr lief, wurde die verwaiste Sperre aufgehoben und der Bestand importiert. Der Geheimnisimport liest vorübergehend einen Wert in den privaten State. Deshalb wurde die App-Kennwortversion vor dem Einrichten der SQL-Rolle erneuert und die Ressource wieder auf Write-only umgestellt. Historische State-Versionen bleiben private sensible Betriebsdaten; der alte importierte Wert wird nicht als SQL-Zugang verwendet.

Aktueller Abschlussstatus des Wiederaufbaus: 45 Ressourcen vollständig abgebaut und wiederhergestellt; eine Notiz mit identischem Datenhash restauriert. HTTPS, zwei API-Replikate, eingeschränkter Datenbankzugriff und echte KI per Workload Identity erneut geprüft. Terraform: keine Änderungen.

## Betrieb Kosten und Grenzen

Die verwendeten zwei Standard_D4s_v6-Knoten wurden mit einem öffentlichen Listenpreis von 0,4344 EUR pro Stunde zusammen ermittelt. Dies ist nur VM-Compute, kein Gesamtpreis. PostgreSQL, Storage, ACR, DNS, IPs, LoadBalancer, Datentransfer und Modellaufrufe kommen hinzu; Verträge und Steuern können die tatsächliche Rechnung verändern.

Für eine normale Pause können AKS und PostgreSQL gestoppt werden. Die Datenbank startet nach sieben Tagen automatisch wieder. Persistent gespeicherte Daten, ACR, DNS, IPs und Disks bleiben gegebenenfalls kostenpflichtig. Ein Modellschalter ersetzt keinen subscriptionweiten Budgetalarm. Kostenkontrolle erfordert das Prüfen der tatsächlichen Azure-Abrechnung.

Die öffentliche Entwickler-IP kann wechseln. Das dafür vorgesehene Werkzeug liest die aktuelle IPv4, ergänzt bei ausdrücklicher Vorbereitung nur diese /32 für die notwendige Terraform-Aktualisierung und erstellt einen Plan. Eine Öffnung für 0.0.0.0/0 ist keine Fehlerbehebung. Die im Projekt beobachtete DNS-/Timeout-Störung der AKS-API wurde auf eine veraltete erlaubte Entwickler-IP zurückgeführt.

| Bewusste Grenze | Folge |
| --- | --- |
| Ein Gateway und kleine DB ohne HA | Geeignet für das Lernprojekt; kein vollständiger Produktions-HA-Nachweis. |
| Prozesslokales KI-Limit | Mehrere Pods besitzen getrennte Limits; kein globaler Ausgabendeckel. |
| Readiness mit DB-Verbindung | Praktischer Funktionsnachweis, aber zusätzliche Verbindungslast. |
| Keine Monitoring-Erweiterung | Prometheus/Grafana ist laut Aufgabenstellung optional und ausdrücklich nicht umgesetzt. |
| Schlüssel lokal für Restore | Verlust des lokalen Entschlüsselungsschlüssels verhindert die Wiederherstellung. |

## Lernerkenntnisse und Entscheidungen

Der wichtigste Fortschritt ist die Trennung von gewünschtem Zustand und einmaliger manueller Einrichtung. Terraform beschreibt Azure-Ressourcen, Kubernetes beschreibt Prozesse und Betriebsregeln, und GitHub Actions liefert nur den geprüften Anwendungsstand aus. Ein erfolgreicher Build allein beweist weder Datenzugriff noch HTTPS oder sichere Nutzertrennung.

Die Fehlersuche wurde durch gezielte Nachweise schneller: Ein privater Netzwerk-Pod prüfte DNS, TCP und TLS ohne SQL-Anmeldung. Danach folgten SQL-Anmeldung, eingeschränkte Rolle und erst anschließend Workload Identity. Beim Gateway wurden Dateirechte und öffentliche Routing-Konvergenz getrennt untersucht. Das verhinderte pauschale Lockerungen von Firewall, TLS oder Dateisystemrechten.

Die Unterschiede zwischen einem Mehrplattform-Index und dem tatsächlichen AMD64-Manifest waren für die Imageintegrität entscheidend. Ein unterschiedlicher Digest bedeutet nicht automatisch geänderten Anwendungscode; die Zuordnung muss jedoch anhand des unveränderlichen Publisher-Indexes geprüft werden. Ein bloßer Tagvergleich genügt nicht.

Die Nutzeranmeldung und die Dienstidentität dürfen nicht vermischt werden. Die Nutzeridentität entscheidet, welche Notizen verarbeitet werden. Die API-Identität erlaubt nur die dafür benötigten Azure-Dienste. Diese Trennung macht auch den KI-Zusatz nachvollziehbar und verhindert, dass Browser oder Notizinhalte Zugriffsschlüssel erhalten.

Beim Neuaufbau war die früher erfolgreiche feste Datenbankzone 3 nicht mehr verfügbar. Nach Entfernen dieser Bindung wählte Azure Zone 2 bei unveränderter B1ms-Größe. Eine SKU-Liste garantiert keine tatsächliche Kapazität. Der vollständige Neuaufbau prüft mehr als Terraform-Syntax: Ein leerer Server braucht Schema und Rollen, eine neue Registry braucht Images, neue Azure-Identitäten brauchen aktuelle Föderation und GitHub-Variablen, und Zertifikate sowie Daten benötigen eine explizite Wiederherstellungsstrategie. Erst die tatsächliche Ausführung schließt diese Lücken.

## Nachweisindex und Übergabe

| Nachweisdatei unter artifacts/ | Belegt |
| --- | --- |
| github/history-scan-and-delivery-44534120752.json | Erfolgreiche Git-Historienprüfung und automatische Lieferung. |
| github/security-gate-negative-log.txt | Absichtlicher Terraform-Sicherheitsfehler mit CRITICAL-Abbruch. |
| azure/workload-access-check.json | CSI-Dateizugriff, eingeschränkte App-Anmeldung und Admin-Geheimnis verweigert. |
| azure/pod-recovery-check.json | Ersatzpod nach 17,9 Sekunden. |
| azure/hpa-scaling-check.json | Hoch- und Rückskalierung mit erfassten HTTP-Antworten. |
| azure/foundry-workload-inference-check.json | Echter AKS-Modellaufruf mit Workload Identity. |
| azure/cloud-stored-note-summary-check.json | Vom Nutzer bestätigte authentifizierte Zusammenfassung einer gespeicherten eigenen Notiz. |
| azure/data-check-check.json | Isolierte Rücksicherung der verschlüsselten Anwendungsdaten. |
| azure/restore-empty-rejection-check.json | Verweigerter Restore in eine nichtleere Tabelle. |
| azure/evolution-recovery-final.json | Zusammengeführter tatsächlicher Infrastruktur-/Daten-Wiederaufbaunachweis. |

Die Abgabe enthält Quellen, diesen Bericht, die zusätzliche Ablauferklärung und ausgewählte tokenfreie Nachweise. Lokale Geheimnisse, State, Image-TAR-Archive, private Zertifikate, verschlüsselte Datenbackups und ihre Schlüssel sind absichtlich nicht enthalten. Der Betreiber muss die lokalen Wiederherstellungsdateien separat aufbewahren.

Repository: https://github.com/CyberAlex91/learningsteps
Projektbrief: LearningSteps Evolution, Weeks 3–6, individuelle Aufgabe. Die tägliche KI-Übung wurde zusätzlich in das bestehende Projekt integriert.

## Quellen und technische Referenzen

Die Aufgabenabdeckung beruht auf dem bereitgestellten Projektbrief und den tatsächlichen Projektartefakten. Technische Referenzen dienen zum Nachvollziehen der verwendeten Funktionen; sie ersetzen keine Ausführungsnachweise.

| Referenz | Verwendeter Zusammenhang |
| --- | --- |
| AzureRM Provider v5.14.0 | Cognitive Account/Deployment, Feature-Schalter und Soft-Delete-Verhalten. |
| Microsoft Azure Identity Python | WorkloadIdentityCredential und die vom AKS-Webhook injizierten Identitätsparameter. |
| Microsoft Azure OpenAI RBAC | Cognitive Services OpenAI User als Inferenzrecht ohne Schlüsselverwaltung. |
| Gitleaks Dokumentation | Git-Historienmodus, vollständige Maskierung und exakte Fingerprints. |
| Kubernetes-Dokumentation | HPA, Ressourcengrößen, Probes und deklarative Deployments. |
| Projekt-Quellcode und Messprotokolle | Konkrete Versionen, Befehle, erwartete Schutzgrenzen und beobachtete Ergebnisse. |

https://github.com/hashicorp/terraform-provider-azurerm/tree/v5.14.0/website/docs
https://learn.microsoft.com/python/api/azure-identity/azure.identity.aio.workloadidentitycredential
https://learn.microsoft.com/azure/foundry-classic/openai/how-to/role-based-access-control
https://github.com/gitleaks/gitleaks
https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

Die ursprünglichen Funktions-, CI- und Wiederaufbauprüfungen stammen vom 19.11.2026. Der vollständige Kostenabbau und die neue Backend-Wiederherstellung sind als Ergänzung vom 20.11.2026 getrennt ausgewiesen. Zukünftige Versionen, Modellverfügbarkeit, Quoten, Kosten und Advisories können sich ändern.
