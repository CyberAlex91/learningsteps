<!-- Zweck: Erklärt den aktuellen sicheren GitHub-Auslieferungsweg und seine tatsächlichen Nachweise. -->
# CI/CD – vom Commit zur laufenden API

## Ablauf und Grenzen

Pushes und Pull Requests starten drei unabhängige Prüfungen:

1. Python-Prüfung, Unit-Tests und echte PostgreSQL-Tests mit zwei synthetischen Nutzeridentitäten.
2. Vollständiger Git-Historien- und Arbeitsverzeichnis-Geheimnisscan sowie Terraform-Sicherheitsanalyse.
3. Produktionsimage bauen, gehärtet starten und auf HIGH/CRITICAL-Schwachstellen prüfen.

Ein Scannerfehler bricht ab. Es gibt kein ignore-unfixed und keine pauschale
Regelausnahme. Drei genau geprüfte historische Docker-Tag-Fehlalarme sind nur
über ihre exakten Fingerprints ausgenommen; siehe SECURITY-SCANS.md.

Nur ein Push auf `main` in `CyberAlex91/learningsteps` darf nach ALLEN drei
bestandenen Prüfungen ausliefern. Pull Requests, Forks und Feature-Branches
bekommen keine passende Azure-Föderation. Nur der Lieferjob erhält
`id-token: write`; `pull_request_target` wird nicht verwendet.

Der Lieferjob lädt das im selben Lauf geprüfte Imagearchiv, prüft SHA256 und
Image-ID, meldet sich schlüssellos über GitHub OIDC an und lädt genau dieses
Image nach ACR. Auslieferung erfolgt mit unveränderlichem Digest. Es wird
zwischen Scan und Deployment kein neues Image gebaut. `scripts/ci_deploy.py`
prüft zusätzlich Repository, Ereignis, Branch und Imageformat.

AKS Run Command benötigt sowohl begrenzte ARM-Rechte am Cluster als auch
Kubernetes-Deployment-Lese-/Schreibrechte ausschließlich im Namespace
`learningsteps`. Die Identität hat keine direkten Secret-Lese-, Pod-Exec- oder
RBAC-Verwaltungsrechte. Deployment-Schreibrecht kann jedoch Podvorlagen ändern;
es ist keine Beschränkung auf ein einzelnes Imagefeld. Daher bleibt der
vertrauenswürdige Repository-/Branchkontext eine wichtige Sicherheitsgrenze.

Die Pipeline ändert das API-Image, wartet auf Rollout, bestätigt den Digest und
prüft öffentliches HTTPS. Sie baut Terraform nicht bei jedem Code-Push neu auf,
ändert keine Notizen und setzt keine HPA-Replikazahl zurück. Infrastrukturänderungen
werden separat geplant und kontrolliert angewandt.

## Konfiguration

Die Repository-Variablen `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` und
`AZURE_SUBSCRIPTION_ID` enthalten öffentliche Identifikatoren, keine Schlüssel.
Nach einem vollständigen Neuaufbau aktualisiert `recovery.py bootstrap` die
geänderte Client-ID. Die Föderation in `infra-terraform/github-actions.tf`
verwendet den bestätigten unveränderlichen GitHub-Repository-Präfix und den
exakten Branch `refs/heads/main`. Ihr alter Ressourcenname enthält aus
Bestandsgründen noch feature-branch; maßgeblich ist der tatsächliche Subject-Wert.

## Bereits nachgewiesene Läufe

| Lauf | Nachweis |
| --- | --- |
| 44523116149 | Vollständige Prüfung und OIDC-Auslieferung nach Namespace-Rechtekorrektur. |
| 44534120752 | Erfolgreiche vollständige Historienprüfung und automatische Auslieferung. |
| 44536752654 | Erfolgreiche Auslieferung des expliziten AKS-Workload-Identity-Modus. |
| 44543103953 | Erfolgreiche Prüfungen und Auslieferung vor dem vollständigen Wiederaufbau. |
| 44525079246 | Absichtlich unsichere Terraform-Regel: zwei CRITICAL-Funde, Exit 1. |

Die früheren erfolgreichen Lieferläufe liefen auf dem damaligen Feature-Branch.
Der abschließende main-Lauf wird separat als Nachweis abgelegt.

Der isolierte Negativtest öffnete SSH nur in einem ungemergten Proof-Commit.
Kein Terraform-Apply wurde ausgeführt. Delivery wurde übersprungen; zusätzlich
war der Proof-Branch unabhängig von der fehlgeschlagenen Prüfung ausgeschlossen.
Der Lauf beweist die Scannerwirkung, isoliert aber nicht die needs-Abhängigkeit
als einzige Ursache des übersprungenen Deployments. Niemals diesen Proof-Branch
mergen. `scripts/prove_security_gate.py` bewahrt Arbeitsverzeichnis und normalen
Git-Index unverändert und verweigert unkontrollierte Wiederholungen.

## Fehler, die wir behoben haben

Der erste Lieferlauf konnte trotz erfolgreicher ARM-Anmeldung im Cluster keine
Deployments lesen. AKS Run Command umgeht in diesem Entra-/Azure-RBAC-Cluster die
Kubernetes-Autorisierung nicht. Die begrenzte Namespace-Rolle behob das Problem.
Ein weiterer Lauf brach auf einem öffentlichen Docker-Tag-Fehlalarm im
Dokumentationstext ab. Die exakte historische Fundstelle wurde geprüft; die
allgemeine Secret-Regel bleibt aktiv. Beide Fehler wurden durch reale neue
Läufe überprüft, nicht nur durch Änderungen am YAML.

## Nachweise ansehen – Ort: WSL-Terminal in VS Code

```bash
gh run list --repo CyberAlex91/learningsteps --branch main --limit 5
gh run view RUN_ID --repo CyberAlex91/learningsteps
gh run watch RUN_ID --repo CyberAlex91/learningsteps --exit-status
```

Ein grüner Quellcode-Push allein beweist kein fertiges Deployment. Entscheidend
sind erfolgreicher Lieferjob, bestätigter Digest und öffentliche HTTPS-Prüfung.
Ausgewählte tokenfreie Protokolle liegen außerhalb des Repositorys unter
`../artifacts/github/`. Private Zugangsdaten gehören weder in diese Dateien noch
in Screenshots. Actions und Scanner sind auf geprüfte unveränderliche Digests
beziehungsweise Commit-IDs festgelegt.
