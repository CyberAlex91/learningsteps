<!-- Zweck: Ablauf zum Verstehen und Nachmachen des LearningSteps-Evolution-Projekts mit tatsächlichen Nachweisen. -->
# LearningSteps Evolution

Alexander Plank | 19.11.2026 | Finale Projektfassung

## Was LearningSteps macht

LearningSteps ist dein persönliches Lerntagebuch. Ein Eintrag beantwortet drei Fragen: Was habe ich bearbeitet? Wo hatte ich Schwierigkeiten? Was möchte ich als Nächstes tun? Die Felder heißen work, struggle und intention. PostgreSQL bewahrt die Einträge dauerhaft auf; FastAPI bietet die Funktionen zum Anlegen, Lesen, Ändern und Löschen.

Die Seite /docs ist Swagger: eine technische Oberfläche zum Ausprobieren der API. Dass sie wie eine Liste von GET-, POST- und PATCH-Aufrufen aussieht, passt zur Backend-Aufgabe. Ein gestaltetes Endnutzer-Frontend wurde nicht verlangt und ist hier nicht zusätzlich gebaut worden. Die Bedienung kann deshalb technisch wirken, obwohl die Funktion dahinter ein einfaches Journal ist.

| Begriff | Bedeutung für dich |
| --- | --- |
| GET | Vorhandene eigene Einträge lesen; keine neuen Daten erzeugen. |
| POST | Einen neuen Eintrag anlegen oder eine Zusammenfassung anfordern. |
| PATCH | Nur bestimmte Felder eines eigenen Eintrags ändern. |
| DELETE mit entry_id | Genau einen eigenen Eintrag löschen. |
| DELETE ohne entry_id | Alle eigenen Einträge löschen. Nicht zum gewöhnlichen Ausprobieren verwenden. |

Jeder Eintrag bekommt eine eindeutige ID. Sie ist die Adresse dieses Datensatzes, kein Passwort. Für gezielte Änderungen kopierst du die ID aus der erfolgreichen POST-Antwort. Zwei POST-Ausführungen können zwei verschiedene Einträge erzeugen; zwei GET-Ausführungen lesen denselben aktuellen Datenbestand.

Die KI-Funktion erzeugt keine neue Notiz. Sie liest deine gespeicherten eigenen Notizen und formuliert daraus Gelerntes, Schwierigkeiten und nächste Schritte. Alte Absichten bleiben alte Absichten: Die KI weiß nicht automatisch, welche Schritte du inzwischen tatsächlich erledigt hast.

## Wie eine Anfrage durch das System geht

Du im Browser â†’ HTTPS-Gateway â†’ API mit Identität â†’ private Datenbank

Du meldest dich in Swagger über Authorize bei Microsoft Entra an. Der Browser erhält ein zeitlich begrenztes Zugriffstoken und sendet es bei geschützten API-Anfragen mit. Die API prüft Unterschrift, Aussteller, Ziel und benötigte Berechtigung. Erst danach steht fest, welcher Nutzer die Anfrage stellt.

Das öffentliche Gateway stellt die verschlüsselte Verbindung zu deinem Browser bereit. Dahinter erreicht es einen internen Kubernetes-Service. Dieser führt zur laufenden API. Die API verbindet sich über das private Azure-Netz und zusätzlich verifiziertes TLS mit PostgreSQL. Du musst die Datenbank weder öffentlich öffnen noch ein Datenbankkennwort im Browser eingeben.

Warum es zwei verschiedene Identitäten gibt

Deine Nutzeridentität entscheidet, welche Notizen dir gehören. Die Identität der Anwendung entscheidet, ob die Anwendung ihr Verbindungsgeheimnis aus Key Vault lesen und Foundry aufrufen darf. Beide Aufgaben brauchen unterschiedliche Rechte. Die Anwendung darf ihren eigenen Azure-Zugang nicht aus einer beliebigen Nutzerangabe im Request ableiten.

Bei der KI-Zusammenfassung lädt die API zuerst deine eigenen Notizen. Erst diese Daten gehen serverseitig zum Modell. Im Browser gibt es keinen Foundry-Schlüssel. Notizinhalte sind für das Modell Daten; sie können keine zusätzlichen Werkzeuge, URL-Aufrufe oder Datenbankabfragen veranlassen, weil der Modellaufruf keine Werkzeuge besitzt.

## Welche Programme du wofür öffnest

| Ort | Dort machen wir diese Arbeit |
| --- | --- |
| VS Code mit WSL | Projekt öffnen, Dateien bearbeiten, Git-/Azure-/Terraform-/Kubernetes-Befehle ausführen. |
| Docker Desktop unter Windows | Lokale Projektcontainer und lokale Image-Builds bereitstellen. |
| Browser | Swagger bedienen, Entra-Anmeldung abschließen, eigene Notizen und Zusammenfassungen ansehen. |
| PowerShell | Die vorhandenen Start-Lokal.ps1 und Stop-Lokal.ps1 für den lokalen Test bedienen. |
| Azure Portal | Bei Bedarf Ergebnisse und Kosten ansehen; der reguläre Infrastrukturaufbau erfolgt über CLI/Terraform. |

Von geschlossenen Programmen zum Projekt

Öffne Docker Desktop, wenn du lokal entwickeln oder Images bearbeiten möchtest. Öffne anschließend VS Code mit WSL-Verbindung. Im integrierten WSL-Terminal wechselst du in den Projektordner und setzt die beiden lokalen Werkzeugvariablen:

```bash
cd "/mnt/c/Users/Administrator/Documents/Codex/Cyber Learning/LearningSteps"
export PATH="$HOME/.local/share/learningsteps-tools/bin:$PATH"
export KUBECONFIG="$HOME/.kube/learningsteps-evolution.yaml"
git -C app status --short --branch
```

KUBECONFIG wählt ausdrücklich unseren Clusterzugang. Ohne diese Einstellung könnte kubectl eine andere Konfiguration verwenden. Die PATH-Ergänzung verwendet die eigens installierten passenden Werkzeuge. Sie verändert nur dieses Terminal, keine dauerhafte Windows-Einstellung.

In WSL kann zusätzlich eine native Docker-Engine vorhanden sein. Diese ist nicht automatisch Docker Desktop. Deshalb verwenden die bisherigen Projekt-Buildskripte ausdrücklich die Windows-Docker-Datei. Ein leerer docker-ps-Aufruf gegen die andere Engine bedeutet nicht, dass unsere Container gelöscht wurden.

## Die Cloud nach einer Pause benutzen

Beginne mit lesenden Prüfungen. Eine erfolgreiche Azure-Anmeldung in PowerShell ist nicht automatisch dieselbe Anmeldung wie in WSL oder im Entwicklungscontainer. Für unsere Cloud-Befehle zählt die WSL-Azure-CLI.

```bash
az account show --query "{Subscription:name,Status:state}" -o json
python3 app/scripts/refresh_developer_access.py
```

Erwartet wird Alexander Plank - Sub. Das IP-Werkzeug prüft zunächst nur. Hat sich deine öffentliche IPv4 geändert, darf die AKS-API weiterhin nur die neue gezielte /32 erhalten. Mit --prepare wird der notwendige eng begrenzte Zugang vorbereitet und ein Terraform-Plan erstellt. Diesen Plan anschließend lesen und erst dann anwenden.

```bash
python3 app/scripts/refresh_developer_access.py --prepare
terraform -chdir=app/infra-terraform apply developer-ip.tfplan
```

Prüfe anschließend den Betriebszustand von AKS und PostgreSQL. Nur falls sie gestoppt sind, starte sie wieder. Die Startvorgänge können mehrere Minuten dauern. Ein Azure-Status Running allein beweist noch nicht, dass die API-Pods und der öffentliche Weg bereits bereit sind.

```bash
az aks start -g rg-learningsteps-evolution -n aks-learningsteps-evolution
az postgres flexible-server start -g rg-learningsteps-data \
  -n psql-learningsteps-alex-0ad5f630
kubectl get nodes
python3 app/scripts/check_https_access.py --timeout 180
```

Für die öffentliche Anwendung brauchst du nicht gleichzeitig die lokale PostgreSQL-Entwicklungsumgebung. Sie ist eine getrennte Umgebung. Für lokale Tests verwendest du in PowerShell Start-Lokal.ps1; ein lokal erstellter Eintrag erscheint nicht automatisch in der Cloud-Datenbank.

## Eine Notiz bewusst ausprobieren

Öffne die öffentliche /docs-Seite und melde dich über Authorize an. Führe zunächst GET /me aus. Code 200 bestätigt eine akzeptierte Anmeldung. GET /entries zeigt anschließend deine eigenen vorhandenen Notizen. Behalte den bereits für den Projektbeleg gespeicherten Eintrag unverändert.

Einen eigenen Demo-Eintrag anlegen

Öffne POST /entries, wähle Try it out und ersetze die Platzhalter durch einen erkennbaren Demo-Inhalt. Einmal Execute genügt. Kopiere danach die zurückgegebene ID für spätere gezielte Änderungen.

```bash
{
  "work": "Ich teste LearningSteps nach dem Wiederaufbau.",
  "struggle": "Die Aufgaben von API und Datenbank unterscheiden.",
  "intention": "Meinen Demo-Eintrag gezielt ändern und wieder löschen."
}
```

Rufe GET /entries erneut auf. Öffne zum Ändern PATCH /entries/{entry_id}, trage die gerade erzeugte Demo-ID ein und sende nur das Feld, das du ändern möchtest. Prüfe anschließend per GET, ob genau dieser Datensatz aktualisiert wurde.

```bash
{"intention": "Als Nächstes die Zusammenfassung der eigenen Notizen testen."}
```

Wenn du die Demo aufräumen willst, verwende ausschließlich DELETE /entries/{entry_id} mit deiner Demo-ID. Der Sammellösch-Endpunkt DELETE /entries ist dafür unnötig. Die übrigen Notizen und der Projektbeleg sollen bestehen bleiben.

## Die KI-Antwort verstehen

Öffne POST /me/notes/summary. Als Body reicht {}. Die API akzeptiert hier keine fremde Nutzerkennung und keine frei erfundenen Notiztexte, sondern verwendet die gespeicherten eigenen Einträge. Drücke einmal Execute und warte auf die Antwort.

| Antwortfeld | So liest du es |
| --- | --- |
| summary | Die vom Modell formulierten drei Themenbereiche. Prüfe sie gegen deine Notizen. |
| note_count | Anzahl der tatsächlich geladenen eigenen Einträge. |
| ai_generated | true bei echter Modellantwort; bei leerem Journal gibt es eine normale erklärende Antwort ohne Modellaufruf. |
| generated_at | Zeitpunkt der Antwort in UTC, nicht Erstellungszeitpunkt der Notiz. |

Bei unserer Cloud-Abnahme erschien Code 200 mit note_count=1 und ai_generated=true. Die Antwort nannte AKS/HTTPS, Schwierigkeiten mit LoadBalancer und Zertifikaten sowie die gespeicherte GitHub-Actions-Absicht. Sie hat also die vorhandene Notiz sinnvoll zusammengefasst.

Lies eine KI-Antwort fachlich nach. Ein plausibler Text kann Formulierungen ergänzen oder missverständlich verdichten. Der Sicherheitsteil begrenzt Zugriffswege und behandelt Notizen als Daten; er ist kein Beweis, dass jeder Satz einer Modellantwort zwangsläufig wahr ist. Eine Notiz mit eingebetteten Anweisungen darf keine Werkzeuge oder zusätzlichen Datenzugriffe auslösen.

Bei 429 einen Moment warten und nicht fortlaufend Execute drücken. Bei 503 ist die Dienstanmeldung oder Erreichbarkeit zu prüfen; niemals einen Foundry-Schlüssel in Swagger einsetzen. Für Screenshots nur den Response body aufnehmen. Der darüber angezeigte Curl-Befehl enthält bei Anmeldung das Bearer-Token und gehört nicht in die Abgabe.

## Was bei einem Git-Push passiert

Du änderst Quellen in VS Code und kontrollierst Git-Diff und Tests. Ein Commit beschreibt einen nachvollziehbaren Stand. Der Push lädt diesen Stand hoch und startet GitHub Actions. Das bedeutet noch nicht automatisch, dass ungeprüfter Code bereits in Azure läuft.

Änderung und Commit â†’ Push und Prüfungen â†’ geprüftes Image â†’ berechtigter Rollout

Fehlgeschlagene Tests oder HIGH-/CRITICAL-Befunde stoppen den Ablauf. Der erfolgreiche Testzweig demonstrierte genau das: Eine absichtlich offene SSH-Regel wurde erkannt. Wir haben sie nie in Azure angewendet. Allein die Prüfdatei im isolierten Proof-Branch reichte für den roten Workflow.

Bei erfolgreicher Prüfung wird dasselbe geprüfte Image ausgeliefert. Der Lieferjob erhält eine kurzlebige Azure-Anmeldung über die festgelegte GitHub-Föderation. Ein Pull Request von fremdem oder nicht vertrauenswürdigem Code erhält diese Auslieferungsrechte nicht. Das Image wird per Digest statt allein per veränderlichem Tag in AKS eingetragen.

```bash
git -C app status --short --branch
git -C app diff --check
git -C app diff
# Danach nur bewusst ausgewählte Dateien hinzufügen und committen.
git -C app push
gh run list --repo CyberAlex91/learningsteps --limit 3
```

Der freigegebene Lieferbranch ist main. Workflow, zusätzliche Kontextprüfung und Entra-Föderation verwenden gemeinsam genau diesen Branch. Der frühere Feature-Branch bleibt Entwicklungshistorie. Neue Änderungen werden geprüft und nach main übernommen; erst ein erfolgreicher main-Push darf ausliefern. Einzelne Branchnamen nicht unabhängig voneinander ändern.

## Warum Kubernetes sich selbst repariert

Ein Deployment beschreibt die gewünschte Zahl gleicher API-Pods. Wird einer entfernt, vergleicht Kubernetes Wunsch und Wirklichkeit und startet Ersatz. In unserem kontrollierten Versuch war ein neuer Pod nach 17,9 Sekunden bereit. Die Daten gingen dadurch nicht verloren: Sie liegen in PostgreSQL und nicht im beschreibbaren Dateisystem des API-Containers.

Readiness bestimmt, ob ein Pod Anfragen erhalten soll. Liveness prüft, ob der Prozess grundsätzlich lebt. Ein kurzzeitig nicht erreichbarer Datenbankserver soll den Pod nicht in eine sinnlose Neustartschleife treiben; deshalb führt nur Readiness die begrenzte DB-Prüfung aus. Startup gibt dem Prozess zusätzlich Zeit zum Anlaufen.

Der HPA beobachtet CPU-Verbrauch relativ zum CPU-Request. Der Request ist die angeforderte Planungsgröße und nicht das CPU-Limit. Ein Wert von 341 Prozent kann deshalb sinnvoll sein, wenn ein Pod deutlich mehr als seinen Request verbraucht, aber noch innerhalb seines Limits arbeitet.

```bash
python3 app/scripts/check_pod_recovery.py
python3 app/scripts/check_hpa_scaling.py
```

Diese Befehle sind gezielte Abnahmen und nicht bei jedem Start nötig. Der erste entfernt einen API-Pod. Der zweite erzeugt zeitlich begrenzte interne HTTP-Last und räumt seine Lastgeneratoren wieder auf. Er benötigt mehrere Minuten, weil Messwerte und Rückskalierung verzögert reagieren. Parallel dazu keine CI-Auslieferung oder zweiten Lasttest starten.

Die bestandene Skalierung 2 → 4 → 2 beweist die Funktion, nicht unbegrenzte Leistung. Das einzelne Gateway und die kleine Datenbank bleiben mögliche Engpässe. Ein richtiger Kapazitätstest müsste repräsentative Anfragen, Datenbankzugriffe, KI-Latenz und längere Messzeiträume getrennt untersuchen.

## Sichern bevor etwas zerstört wird

Terraform sichert keine Inhalte deiner Notizen. Es beschreibt Ressourcen wie Server, Netze und Identitäten. Ein neu angelegter PostgreSQL-Server ist zunächst leer. Deshalb brauchen wir neben Quellcode und State eine unabhängige Datensicherung.

```bash
python3 app/scripts/cloud_data_backup.py backup
python3 app/scripts/cloud_data_backup.py check \
  --manifest PFAD_ZUM_AUSGEGEBENEN_MANIFEST
python3 app/scripts/recovery.py prepare \
  --backup PFAD_ZUM_AUSGEGEBENEN_MANIFEST
```

backup verschlüsselt alle bekannten Anwendungsdaten. check restauriert sie in einer neuen Testdatenbank und vergleicht den vollständigen Inhalt. Erst dieser zweite Schritt zeigt, dass eine vorhandene Datei auch praktisch nutzbar ist. Der Test entfernte anschließend ausschließlich seine eigene Testdatenbank.

prepare bewahrt die tatsächlich getesteten API-/Gateway-Images und den verschlüsselten Zertifikatszustand. Wird auch die Registry gelöscht, reicht ein alter Image-Digest allein nicht: Der Inhalt muss noch an einer unabhängigen Stelle vorhanden sein. Gleiches gilt für die privaten Zertifikatsschlüssel.

Der Entschlüsselungsschlüssel bleibt lokal unter .secrets/backups. Er gehört nicht in den Bericht, nicht in Git und nicht in das Abgabepaket. Die Windows-Ordnerrechte begrenzen den Zugriff. Bewahre Schlüssel und verschlüsselte Sicherung getrennt auf; ohne passenden Schlüssel ist eine korrekte AES-GCM-Datei nicht restaurierbar.

Das Werkzeug restore-empty verweigert das Schreiben in eine bereits gefüllte Zieltabelle. Wir haben diese Sperre tatsächlich ausgelöst und danach die unveränderten Live-Daten erneut geprüft. Damit ist die Sicherung nicht bloß ein Skriptversprechen.

## Den vollständigen Neuaufbau nachvollziehen

Der vollständige Test ist ein Wartungsfenster. Zuerst wird die API angehalten, damit nach dem letzten Datenvergleich keine neuen Notizen hinzukommen. Der öffentliche Kubernetes-Service und das Zertifikatsvolume werden geordnet entfernt. Erst dann darf der geprüfte Terraform-Destroy-Plan die Azure-Anwendungsressourcen abbauen.

Unsere separate Remote-State-Gruppe bleibt bestehen. Key Vault und Foundry verwenden Soft-Delete; der geschützte Tresor wird nicht zwangsweise gepurgt. Die Wiederherstellung behandelt diese Dienstzustände ausdrücklich. Ein kompletter Neuaufbau bedeutet hier keine Umgehung von Azure-Löschschutz.

```bash
python3 app/scripts/recovery.py plan-destroy
# Vollständigen Plan prüfen, dann den gespeicherten Plan anwenden.
terraform -chdir=app/infra-terraform apply evolution-destroy.tfplan
terraform -chdir=app/infra-terraform state list
python3 app/scripts/recovery.py infrastructure
python3 app/scripts/recovery.py bootstrap
python3 app/scripts/recovery.py restore-guards
```

infrastructure legt die Azure-Ressourcen wieder an. bootstrap stellt Images, Datenbankschema, SQL-Rechte und gesicherte Notizen wieder her. Es aktualisiert die Clusterkonfiguration und die neu entstandene GitHub-Identität. Der Zertifikatszustand wird vor dem Gateway-Start restauriert; die öffentliche Konfiguration wird erst nach stabiler Erreichbarkeit aktiviert.

Zum Schluss müssen Dateninhalt, neue Clusterkennungen, zwei bereite API-Pods, gültiges öffentliches HTTPS, echter Modellzugriff und Terraform No changes überprüft sein. Der konkrete Abschlussstatus dieses Laufs lautet: 45 Ressourcen vollständig abgebaut und wiederhergestellt; eine Notiz mit identischem Datenhash restauriert. HTTPS, zwei API-Replikate, eingeschränkter Datenbankzugriff und echte KI per Workload Identity erneut geprüft. Terraform: keine Änderungen.

Die detaillierten Voraussetzungen, Wiederholungsgrenzen und Dateipfade stehen in RECOVERY.md. Diesen Ablauf nicht als gewöhnlichen täglichen Start verwenden.

## Pause Fehlerbilder und nächste Pflege

Eine normale Pause ist kleiner als ein vollständiger Abbau. Prüfe zuerst, dass keine Auslieferung und keine Sicherung mehr läuft. Danach kannst du AKS und PostgreSQL gezielt stoppen. Bereits angefallene Kosten verschwinden dadurch nicht, und gespeicherte Ressourcen können weiter Kosten verursachen.

```bash
az aks stop -g rg-learningsteps-evolution -n aks-learningsteps-evolution
az postgres flexible-server stop -g rg-learningsteps-data \
  -n psql-learningsteps-alex-0ad5f630
```

PostgreSQL startet nach sieben Tagen automatisch wieder. Zum Fortsetzen zunächst Azure-Anmeldung und öffentliche Entwickler-IP prüfen, dann die Dienste bei Bedarf starten und die echte HTTPS-Abnahme wiederholen. Modellaufrufe verursachen auch bei kleinen Tests Verbrauchskosten; häufiges erneutes Execute ist kein Fehlerdiagnoseverfahren.

| Beobachtung | Gezielter nächster Schritt |
| --- | --- |
| kubectl-Timeout nach IP-Wechsel | Aktuelle /32 und erlaubte API-Adressen mit refresh_developer_access.py vergleichen. |
| 401 bei eigenen Notizen | Entra-Anmeldung und den passenden API-Scope prüfen; keine DB-Rechte erweitern. |
| Readiness 503 | Private DNS-/TLS-/Datenbankverbindung prüfen; Liveness nicht mit DB-Abhängigkeit überladen. |
| Ungültiges HTTPS-Zertifikat | Gateway-/ACME-Zustand und öffentliche Konvergenz prüfen; niemals TLS-Verifikation abschalten. |
| KI 503 oder 502 | Identitätsmodus, Modellverfügbarkeit und Inferenzrecht prüfen; keine Schlüssel in Swagger eintragen. |
| Restore bricht ab | Manifest, Schlüssel, Hash und leeres Ziel kontrollieren; vorhandene Notizen nicht pauschal löschen. |

Für produktive Nutzung wären insbesondere Gateway-/Datenbank-HA, globales Rate-/Kostenlimit, automatisierte Kennwortrotation und Monitoring auszubauen. Prometheus/Grafana blieb im Rahmen dieser ausdrücklich optionalen Teilaufgabe offen. Die Kernnachweise für Container, IaC, Sicherheits-Pipeline, Auslieferung, Skalierung und Wiederherstellung sind getrennt dokumentiert.
