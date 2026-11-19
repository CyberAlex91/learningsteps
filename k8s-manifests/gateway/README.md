<!-- Zweck: Erklärt HTTPS-Gateway, Zertifikatsvolume, Betrieb und verbleibende Neuaufbaugrenzen. -->
# Öffentliches HTTPS-Gateway

`traefik.yaml` ist die einzige aktive Gateway-Konfiguration. Sie definiert
StorageClass, 4-GiB-PVC, öffentliche Konfiguration, einen nicht privilegierten
Traefik-Pod und den LoadBalancer-Service mit Port 80/443.
Die verworfene Caddy-Konfiguration wurde entfernt; ihr Scanbefund bleibt in
[SECURITY-SCANS.md](../../SECURITY-SCANS.md) und den externen Nachweisen erhalten.

`deploy_https_gateway.sh` prüft Cluster/Subscription und den festgelegten
Linux/AMD64-Digest, überträgt das Image unverändert nach ACR, prüft den Registry-Digest
und validiert/appliziert ausschließlich dieses Manifest. Der Multiarch-Index
unterscheidet sich vom AMD64-Manifest; die Zuordnung wird geprüft.
`check_https_access.py` prüft danach Zertifikatsvertrauen, Hostname, HTTP-Weiterleitung,
öffentliche Probes/Docs und die Ablehnung anonymer Notizabrufe.

Hostname: learningsteps-alex-0ad5f630.germanywestcentral.cloudapp.azure.com.
Öffentliche IP zuletzt 131.189.29.152, Terraform-Ressource pip-learningsteps-https.
Öffentliche HTTPS-Abnahme sowie Entra-Browserlogin und eigene Notizanlage/-abfrage
sind erfolgt. Kein API-Schlüssel oder Datenbankgeheimnis im Gateway.

Traefik arbeitet intern auf 8080/8443; Health-Port 8082 ist nicht öffentlich.
Keine Docker-/Kubernetes-Discovery, kein Dashboard, keine Azure-Identität und
keine Datenbankkonfiguration. Zertifikate und ACME-Konto bleiben im PVC unter
/data. Beim Start werden umask077 und Dateirechte0600 für acme.json gesetzt;
Datei oder Volume nicht als Diagnosemaßnahme löschen oder exportieren.

Ein Gateway mit Recreate und RWO-Disk ist eine bewusste Laboreinschränkung:
kein hochverfügbares Gateway, auch wenn mehrere API-Pods bereitstehen.
Gateway-Readiness beweist nicht, dass das öffentliche Zertifikat ausgestellt ist.
Beim ersten Aufbau scheiterte ACME während der öffentlichen Routing-Konvergenz;
ein späteres dynamisches Konfigurations-Reload ohne Neustart löste die Ausstellung
nachweislich aus. Dies muss vor dem vollständigen Neuaufbautest automatisiert werden.

In normalen Pausen PVC behalten. Beim geplanten vollständigen Abbau öffentliche
Services und PVC kontrolliert vor AKS entfernen. Disk, öffentliche IP und
LoadBalancer können auch neben den Rechenknoten Kosten verursachen.
Nicht rekursiv alle Kubernetes-Manifeste einschließlich Diagnose-Pods anwenden.
