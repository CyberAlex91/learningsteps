# Zweck: Erzeugt den technischen Evolution-Bericht und die verständliche Anleitung im geprüften Red-Blue-Layout aus nachgewiesenen Ergebnissen.
"""Use the bundled document Python. --draft writes only private QA previews."""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
BLUE = colors.HexColor("#183B61")
RED = colors.HexColor("#B33D49")
PALE = colors.HexColor("#F0F4F8")
GRAY = colors.HexColor("#53677C")
W, H = A4
M = 46
FONTDIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONTDIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("BodyBold", str(FONTDIR / "arialbd.ttf")))
STYLES = {
    "body": ParagraphStyle("Body", fontName="Body", fontSize=10.1, leading=14.6, spaceAfter=10, textColor=colors.HexColor("#26384A")),
    "h1": ParagraphStyle("Chapter", fontName="BodyBold", fontSize=19, leading=23, textColor=BLUE, spaceAfter=17),
    "h2": ParagraphStyle("Subheading", fontName="BodyBold", fontSize=12, leading=16, textColor=BLUE, spaceBefore=10, spaceAfter=7),
    "cell": ParagraphStyle("Cell", fontName="Body", fontSize=9, leading=12, textColor=colors.HexColor("#26384A")),
    "thead": ParagraphStyle("TableHeader", fontName="BodyBold", fontSize=9, leading=12, textColor=colors.white),
    "code": ParagraphStyle("Code", fontName="Courier", fontSize=8.2, leading=11.5, spaceAfter=12, textColor=BLUE),
    "small": ParagraphStyle("Small", fontName="Body", fontSize=8.4, leading=11, textColor=GRAY, spaceAfter=9),
}


def p(text, style="body"):
    return Paragraph(escape(text).replace("\n", "<br/>"), STYLES[style])


class Diagram(Flowable):
    def __init__(self, labels):
        super().__init__(); self.labels = labels; self.width = W - 2*M; self.height = 100

    def draw(self):
        c = self.canv; n = len(self.labels); gap = 14; width = (self.width-gap*(n-1))/n
        for i, label in enumerate(self.labels):
            x = i*(width+gap)
            c.setFillColor(PALE); c.setStrokeColor(BLUE); c.roundRect(x, 24, width, 62, 3, fill=1)
            q = p(label, "cell"); _, height = q.wrap(width-14, 58); q.drawOn(c, x+7, 55-height/2)
            if i<n-1:
                c.setStrokeColor(RED); c.line(x+width+2, 55, x+width+gap-2, 55)
                c.line(x+width+gap-5, 58, x+width+gap-2, 55)
                c.line(x+width+gap-5, 52, x+width+gap-2, 55)


def table(headers, rows):
    weights = [1]*len(headers)
    if len(headers)==2: weights=[0.36,0.64]
    data = [[p(v,"thead") for v in headers]] + [[p(str(v),"cell") for v in row] for row in rows]
    obj = Table(data, colWidths=[(W-2*M)*w/sum(weights) for w in weights], repeatRows=1, hAlign="LEFT")
    obj.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),BLUE), ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8), ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8), ("LINEBELOW",(0,0),(-1,0),0.6,BLUE),
        ("LINEBELOW",(0,1),(-1,-1),0.35,colors.HexColor("#C9D6E3")),
    ])); return obj


class Report(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "Chapter":
            title = flowable.getPlainText(); key="chapter-"+str(self.page)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,0,False)
            self.notify("TOCEntry",(0,title,self.page,key))


def page(canvas, doc):
    if doc.page == 1:
        canvas.saveState()
        canvas.linearGradient(0,H,W,0,[colors.HexColor("#A3333D"),colors.HexColor("#B33D49"),colors.HexColor("#1B5B8F"),colors.HexColor("#163C66")],[0,.35,.65,1])
        canvas.setFillColor(colors.white); canvas.setFont("BodyBold",9)
        canvas.drawString(62,H-182,doc.kind.upper())
        canvas.setFont("BodyBold",38); canvas.drawString(62,H-260,"LearningSteps")
        canvas.drawString(62,H-307,"Evolution")
        canvas.setFont("Body",17); canvas.drawString(62,H-363,doc.subtitle)
        canvas.setFont("Body",12)
        canvas.drawString(62,H-405,"Terraform · AKS · CI/CD · sichere KI")
        canvas.setFillColor(colors.white);canvas.rect(62,H-438,164,7,fill=1,stroke=0)
        canvas.setStrokeColor(colors.white);canvas.setLineWidth(.5);canvas.line(62,224,W-62,224)
        for x,y,label,value in [(62,196,"VERFASSER","Alexander Plank"),(W/2+28,196,"STAND","19.11.2026"),
                                (62,137,"PROJEKT","CyberSteps Weeks 3–6"),(W/2+28,137,"FASSUNG",doc.version_label)]:
            canvas.setFont("Body",7);canvas.drawString(x,y,label)
            canvas.setFont("BodyBold",10);canvas.drawString(x,y-20,value)
        canvas.setFont("Body",8);canvas.drawString(62,58,"ARCHITEKTUR / FUNKTION / SICHERHEIT / WIEDERHERSTELLUNG")
        canvas.restoreState();return
    canvas.saveState(); canvas.setFillColor(BLUE);canvas.rect(M,H-34,(W-2*M)*.7,3,fill=1,stroke=0)
    canvas.setFillColor(RED);canvas.rect(M+(W-2*M)*.7,H-34,(W-2*M)*.3,3,fill=1,stroke=0)
    canvas.setFillColor(GRAY);canvas.setFont("Body",7)
    canvas.drawString(M,H-48,"LEARNINGSTEPS EVOLUTION | "+doc.kind.upper())
    canvas.setStrokeColor(colors.HexColor("#CCD7E2"));canvas.setLineWidth(.4);canvas.line(M,39,W-M,39)
    canvas.drawString(M,27,"Alexander Plank | 19.11.2026 | "+doc.version_label)
    canvas.drawRightString(W-M,27,"Seite "+str(doc.page));canvas.restoreState()


def write_document(filename, kind, subtitle, sections, draft):
    output = ROOT / (".state/report-qa" if draft else "output/pdf")
    output.mkdir(parents=True,exist_ok=True)
    doc = Report(str(output/(filename+".pdf")),pagesize=A4,leftMargin=M,rightMargin=M,topMargin=65,bottomMargin=53,
                 title="LearningSteps Evolution "+kind,author="Alexander Plank")
    doc.kind=kind;doc.subtitle=subtitle;doc.version_label="Entwurf – Wiederaufbauprüfung offen" if draft else "Finale Projektfassung"
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle("TOC",fontName="Body",fontSize=10,leading=16,spaceBefore=5,textColor=BLUE,leftIndent=0,firstLineIndent=0)]
    story=[Spacer(1,1),PageBreak(),p("Inhalt","h2"),toc,PageBreak()]
    md=["<!-- Zweck: "+kind+" des LearningSteps-Evolution-Projekts mit tatsächlichen Nachweisen. -->", "# LearningSteps Evolution", "", "Alexander Plank | 19.11.2026 | "+doc.version_label, ""]
    for index,(title,blocks) in enumerate(sections):
        if index:story.append(PageBreak())
        story.append(p(title,"h1"));md += ["## "+title,""]
        for block in blocks:
            if block[0] in ("p","small","h2"):
                style="body" if block[0]=="p" else block[0]
                story.append(p(block[1],style));md.extend([block[1],""])
            elif block[0]=="code":
                story.append(p(block[1],"code"));md.extend(["```bash",block[1],"```",""])
            elif block[0]=="table":
                story.extend([table(block[1],block[2]),Spacer(1,12)])
                md += ["| "+" | ".join(block[1])+" |","| "+" | ".join(["---"]*len(block[1]))+" |"]
                md += ["| "+" | ".join(str(v).replace('\n',' ') for v in row)+" |" for row in block[2]];md.append("")
            elif block[0]=="diagram":
                story.append(Diagram(block[1]));md.extend([" â†’ ".join(block[1]),""])
    doc.multiBuild(story,onFirstPage=page,onLaterPages=page)
    if not draft:
        sources=APP/"docs";sources.mkdir(exist_ok=True)
        (sources/(filename+".md")).write_text("\n".join(md),encoding="utf-8")
    return str(output/(filename+".pdf"))


def contents(final):
    status = "Der vollständige Wiederaufbau ist nachgewiesen." if final.get("passed") else "Der vollständige Wiederaufbau wird aktuell geprüft; noch kein Erfolgsnachweis."
    report = [
        ("Ergebnis und Geltungsbereich",[
            ("p","LearningSteps wurde von einer manuell betriebenen Anwendung zu einem durch Terraform verwalteten Cloud-System mit automatischer Auslieferung weiterentwickelt. FastAPI läuft in gehärteten Containern auf AKS. PostgreSQL ist privat erreichbar; Nutzer melden sich über Entra an. Eine serverseitige KI fasst ausschließlich die gespeicherten eigenen Notizen zusammen."),
            ("p",status),
            ("table",["Abnahme","Tatsächlicher Nachweis"],[("Öffentliche Anwendung","Vertrauenswürdiges HTTPS, Entra-Anmeldung sowie Anlage und Abruf einer eigenen Cloud-Notiz."),("Continuous Delivery","Codeänderung über GitHub-Prüfungen, OIDC, ACR und AKS bis zur öffentlichen API ausgeliefert."),("Sicherheitsabbruch","Absichtlich offene SSH-Regel: zwei CRITICAL-Befunde, Scanner-Exitcode 1."),("Selbstheilung und Skalierung","API-Ersatzpod nach 17,9 Sekunden; Lasttest mit 2 → 4 → 2 bereiten Pods."),("Cloud-KI","Drei synthetische RAM-Notizen per Workload Identity; anschließend gespeicherte eigene Notiz mit HTTP 200 zusammengefasst.")]),
            ("p","Die optionale Prometheus-/Grafana-Erweiterung wurde nicht implementiert. Die Datenbankrechte sind auf die Anwendung begrenzt; die Trennung einzelner Nutzer erfolgt in der API und wurde mit synthetischen Identitäten getestet. Dieser Bericht beschreibt einen kontrollierten Lernprojektstand, keine uneingeschränkte Produktionsfreigabe."),
        ]),
        ("Architektur und Kommunikationswege",[
            ("diagram",["Browser\nEntra-Anmeldung","Traefik\nöffentliches HTTPS","FastAPI auf AKS\ninterner Service","PostgreSQL\nprivates Netz"]),
            ("p","Der Browser erreicht nur das HTTPS-Gateway. Traefik entschlüsselt HTTPS und leitet an den internen ClusterIP-Service der API weiter. Die API prüft das Entra-Zugriffstoken und führt Datenbankoperationen mit einer eingeschränkten SQL-Rolle aus. PostgreSQL besitzt keinen öffentlichen Datenzugang."),
            ("p","Der AKS-Cluster und sein VNet liegen in Germany West Central. Für PostgreSQL war die Bereitstellung in dieser Subscription dort eingeschränkt; deshalb liegt die private Datenumgebung in West Europe. Die beiden VNets sind durch Peering verbunden. Die dokumentierte Einschränkung betrifft die geprüfte Subscription und ist keine allgemeine Aussage über die Region."),
            ("table",["Netzbereich","Aufgabe"],[("10.60.0.0/16","Evolution-VNet; AKS-Subnetz 10.60.0.0/22."),("10.62.0.0/16","Daten-VNet in West Europe; delegiertes DB-Subnetz 10.62.1.0/24."),("10.61.0.0/16","Interne Kubernetes-Serviceadressen; keine direkt aus dem Internet erreichbaren API-Pods."),("Port 80 und 443","ACME/HTTPS-Weiterleitung und öffentlicher HTTPS-Zugriff am Gateway."),("Port 5432","PostgreSQL über das private Netz und verifiziertes TLS.")]),
            ("p","Das einzelne Gateway mit Recreate-Strategie und RWO-Zertifikatsdisk ist bewusst keine hochverfügbare Eingangsschicht. Mehrere API-Pods schützen den Anwendungsbetrieb vor dem Ausfall eines einzelnen API-Pods; sie beseitigen nicht diese Gateway-Einschränkung."),
        ]),
        ("Werkzeuge und reproduzierbare Quellen",[
            ("p","Azure CLI, Terraform, Git und Kubernetes-Befehle werden im WSL-Terminal von VS Code ausgeführt. Docker Desktop ist die verwendete lokale Container-Engine. Die native WSL-Docker-Engine war eine getrennte Umgebung und zeigte deshalb anfangs die bestehenden Projektcontainer nicht an."),
            ("table",["Quellbereich","Verantwortung"],[("api/","FastAPI, Datenmodelle, Nutzerprüfung, Datenbankzugriff und Zusammenfassungslogik."),("infra-terraform/","Netze, AKS, ACR, PostgreSQL, Key Vault, Identitäten, Rollen und Modell."),("k8s-manifests/","API, Probes, Ressourcenlimits, Services, HPA, CSI und HTTPS-Gateway."),("scripts/ und tests/","Auslieferung, betriebliche Abnahmen, Sicherung und Wiederherstellung."),(".github/workflows/ci.yml","Automatische Prüfungen und vertrauenswürdige Auslieferung."),("docs/ und RECOVERY.md","Bericht, Ablauferklärung und ausführbare Betriebsanleitung.")]),
            ("p","Nach der Bereinigung tragen eigene kommentierbare Quelldateien kurze Zweckhinweise. JSON-Dateien, erzeugte Sperrdateien und unveränderte Messprotokolle werden nicht durch ungültige Kommentare verändert; ihre Aufgaben sind in DATEIUEBERSICHT.md beschrieben."),
            ("p","Git enthält Quellcode und öffentliche Konfiguration. Private .env-Dateien, Terraform-Pläne und State, lokale Schlüssel, Backups, Zertifikatsmaterial und Python-Umgebungen bleiben außerhalb der veröffentlichten Quellen. Der historische Origins-Abschluss ist als finales Paket und PDF erhalten; überholte lose VM-Skripte wurden entfernt."),
        ]),
        ("Terraform und Infrastrukturzustand",[
            ("p","Terraform beschreibt die gewünschte Infrastruktur und vergleicht sie mit Azure. Der Remote State liegt in einem getrennten Azure-Storagekonto mit Entra-Anmeldung, deaktivierten Shared Keys, HTTPS, Versionierung sowie sieben Tagen Blob-/Container-Löschaufbewahrung. Das Backend bleibt beim Anwendungs-Neuaufbautest bewusst erhalten. Auch die bestehenden Entra-Registrierungen für API und Swagger bleiben als dokumentierte Anmeldevoraussetzungen bestehen; der Test rekonstruiert die 45 verwalteten Anwendungsressourcen, keinen leeren Entra-Tenant."),
            ("p","Vor jeder Änderung werden Formatierung, Validierung und der tatsächliche Plan geprüft. Der Foundry-Lauf ergänzte beispielsweise genau Modell und API-Recht: zwei neue Ressourcen, keine Änderung und keine Löschung. Der nachfolgende Plan meldete No changes. Bestehende Ressourcen und das manuelle Entwickler-Modellrecht wurden kontrolliert importiert."),
            ("code","terraform -chdir=app/infra-terraform fmt\nterraform -chdir=app/infra-terraform validate\nterraform -chdir=app/infra-terraform plan -out=reviewed.tfplan\nterraform -chdir=app/infra-terraform apply reviewed.tfplan"),
            ("p","Eine Azure-Richtlinie ergänzte das Tag created-on während der Bereitstellung. Die Übernahme von veränderlichen Ressourcengruppen-Tags in abhängige Ressourcen verursachte einen inkonsistenten Provider-Plan. Statische Projekt-Tags und das gezielte Ignorieren allein dieses extern gepflegten Metadatenfelds behoben den Fehler, ohne andere Infrastrukturänderungen zu verdecken."),
            ("p","Temporäre prevent_destroy-Sperren schützen Datenbank und Foundry während der Einrichtung. Für den vollständigen Abnahmetest werden nur diese drei bekannten Sperren nach geprüften Sicherungen kontrolliert geöffnet und anschließend wiederhergestellt. Soft-Delete und Purge Protection bleiben aktiv; der Wiederaufbau berücksichtigt sie ausdrücklich."),
        ]),
        ("Container und Schwachstellenprüfung",[
            ("p","Das API-Image verwendet Python 3.12 auf einem festgelegten Alpine-Basisdigest. Direkte und transitive Python-Versionen sind in requirements.lock fixiert. Das Image aktualisiert Alpine-Pakete beim Build, installiert binäre Python-Pakete und läuft als Benutzer 10001. Kubernetes erzwingt ein schreibgeschütztes Rootdateisystem, entfernte Linux-Capabilities, keine Privilegienerhöhung und RuntimeDefault-Seccomp."),
            ("p","Dockerfile und .dockerignore begrenzen den Buildkontext auf die erforderlichen API-Dateien. Lokale Geheimnisse, private Schlüssel, Caches und Entwicklungsumgebungen gelangen nicht in das Produktionsimage. Die Azure CLI ist dort nicht installiert; die Cloud-KI verwendet Workload Identity."),
            ("table",["Prüfbereich","Entscheidung und Beleg"],[("Debian-Kandidaten","Bookworm und Trixie wurden wegen HIGH-Befunden verworfen; keine pauschale Ausnahme."),("Alpine-Anwendung","Paketkorrekturen, Dependency-Check, gehärteter Start und selektierter HIGH/CRITICAL-Scan bestanden."),("Caddy-Kandidat","Zwei HIGH-Befunde im Go-Binary; nicht bereitgestellt, Konfiguration entfernt."),("Traefik","Geprüftes v2.11.61-Image; null HIGH/CRITICAL zum Scanzeitpunkt. AMD64-Manifest und ACR-Digest verifiziert.")]),
            ("p","Trivy prüft das tatsächlich gebaute und exportierte Image. Zwischen Scan und Auslieferung findet kein zweiter Build statt. Ein erfolgreicher Scan ist eine Aussage zum verwendeten Prüfzeitpunkt und Schweregrad, keine Garantie für die Abwesenheit aller heutigen oder zukünftigen Schwachstellen."),
        ]),
        ("Identitäten und minimale Rechte",[
            ("diagram",["Nutzer\nEntra-Token","API\nprüft Identität","API-ServiceAccount\nWorkload Identity","Key Vault / Foundry\ngezielte Rechte"]),
            ("p","Nutzeranmeldung und Dienstanmeldung sind zwei getrennte Grenzen. Das signaturgeprüfte Nutzer-Token bestimmt Tenant und Nutzer der angeforderten Notizen. Der Kubernetes-ServiceAccount authentifiziert dagegen die API gegenüber Azure. Eine Nutzerkennung aus einem frei wählbaren Request-Body darf diese Auswahl nicht ersetzen."),
            ("table",["Identität","Begrenzte Aufgabe"],[("Entwickler","Terraform-Verwaltung und kontrollierte lokale Werkzeuge; Entra statt veröffentlichter Schlüssel."),("AKS-Kubelet","Images mit AcrPull aus der Projektregistry laden."),("API-Workload","Nur das DB-URL-Geheimnis lesen und am Foundry-Konto Modellinferenz ausführen."),("GitHub-Auslieferung","AcrPush plus AKS Run Command; Deployment-Datenaktionen nur im Namespace learningsteps."),("Gateway","Keine Azure-Identität, keine DB-Konfiguration, keine Token- oder Notiz-Accesslogs.")]),
            ("p","Die API liest den Admin-Datenbankschlüssel nicht. Ein echter Workload-Test bestätigte sowohl App-Anmeldung über TLS als auch ForbiddenByRbac beim Versuch, das Admin-Geheimnis zu lesen. Das schließt eine bloße Übernahme von Entwicklerrechten als Testersatz aus."),
        ]),
    ]
    report.extend([
        ("Automatische Auslieferung mit GitHub",[
            ("diagram",["Git-Push","Tests und Scans","geprüftes Image","OIDC und ACR","AKS-Rollout"]),
            ("p","Jeder Push startet drei voneinander unabhängige Prüfbereiche. Der Qualitätsjob installiert gesperrte Abhängigkeiten, prüft Python-Konstrukte und führt Unit- sowie echte PostgreSQL-Nutzertrennungstests aus. Die Testdatenbank ist kurzlebig und enthält ausschließlich synthetische Daten. Zielprüfung und separate Datenbanknamen verhindern eine Verwechslung mit dem Journal."),
            ("p","Der Quellenjob prüft aktuelle Dateien und die vollständig gefetchte Git-Historie auf Geheimnisse sowie Terraform auf HIGH-/CRITICAL-Fehlkonfigurationen. Der Imagejob baut das Produktionsimage, prüft nicht privilegierten Start und anonyme Zugriffsablehnung und scannt das identische Imagearchiv. Erst alle drei erfolgreichen Jobs erlauben die gesonderte Auslieferung."),
            ("p","Das Imagearchiv, seine SHA-256-Prüfsumme und die Imagekennung wechseln als Artefakt desselben Workflow-Laufs in den Lieferjob. Dieser prüft Archiv und Inhalt vor der Azure-Anmeldung, nutzt kurzlebige GitHub-OIDC-Anmeldung, überträgt das unveränderte Image und vergleicht den ACR-Digest. AKS wird mit dem unveränderlichen Digest aktualisiert; Rollout und öffentliches HTTPS werden nachgeprüft."),
            ("p","Nur der vertrauenswürdige Repository-/Branch-Kontext erhält die Azure-Föderation und id-token:write. Pull Requests und andere Branches führen keine privilegierte Auslieferung aus. Actions und Scanner sind auf überprüfte Commit- beziehungsweise Image-Digests festgelegt. Der getestete Implementierungsweg verwendet Azure AKS Run Command, ohne die API-Firewall für beliebige GitHub-Runner-IP-Adressen zu öffnen."),
            ("small","Erfolgreiche Läufe: 44534120752 mit Historien-Scan und 44536752654 mit Cloud-KI-Code. Der Lauf 44543103953 bestätigte die Backup-/Wiederaufbauhelfer vor dem Wartungsfenster."),
        ]),
        ("Sicherheitsgrenzen und Negativnachweise",[
            ("p","Der absichtliche Sicherheitsfehler lag in einem isolierten Proof-Branch: Eine Netzwerkregel erlaubte SSH aus 0.0.0.0/0. Terraform wurde daraus nie angewendet. Trivy meldete AZU-0047 und AZU-0050 als CRITICAL und beendete den Prüfschritt mit Exitcode 1. Der Workflow blieb fehlgeschlagen; die Auslieferung wurde übersprungen."),
            ("p","Der Proof-Branch war zusätzlich grundsätzlich von der privilegierten Auslieferung ausgeschlossen. Der Lauf belegt deshalb unmittelbar die Erkennung und den Fehlerstatus des Scanners, nicht allein die needs-Abhängigkeit als isolierte Ursache des übersprungenen Lieferjobs. Die Workflow-Datei verlangt unabhängig davon alle drei erfolgreichen Prüfjobs."),
            ("p","Gitleaks erkannte beim Historien-Scan einen öffentlichen Docker-Tag fälschlich als API-Schlüssel. Zwei historische Dokumentationsfundstellen und eine Wiederholung im Prüftext wurden anhand von Commit, Datei, Regel und Zeile einzeln geprüft. Die Ausnahme enthält nur diese drei exakten Fingerprints. Weder ganze Dateien noch die allgemeine Erkennungsregel wurden deaktiviert."),
            ("p","Ein echter Lieferlauf deckte eine fehlende Kubernetes-Berechtigung auf. Die vorherige Annahme, ARM Run Command würde die Kubernetes-Rechte umgehen, war falsch: In diesem Cluster wurde die Aufruferautorisierung durchgesetzt. Die Korrektur vergibt nur Deployment-Lese-/Schreibaktionen im Namespace learningsteps. Das gestattet Änderungen an Workload-Vorlagen im Namespace und ist keine auf das Imagefeld begrenzte Erlaubnis."),
            ("p","Private Schlüssel, Datenbankkennwörter, Foundry-Schlüssel und Bearer-Tokens werden nicht veröffentlicht. Der vom Nutzer gelieferte Swagger-Screenshot enthielt einen Authorization-Header und wurde nicht in Bericht oder Paket kopiert. Der Nachweis verwendet die separat übermittelten, tokenfreien Antwortdaten."),
        ]),
        ("Private Datenbank und Zugriffsschutz",[
            ("p","PostgreSQL Flexible Server 15 liegt in einem delegierten Subnetz. Öffentlicher Datenzugriff ist deaktiviert. Private DNS-Verknüpfungen und Peering verbinden AKS und Datenbank. Die Netzprüfung bestätigte private Auflösung, erreichbaren TCP-Port 5432 und eine TLS-1.3-Verbindung mit überprüfter Zertifikatskette und Hostnamen."),
            ("p","Die Anwendung arbeitet mit learningsteps_app statt dem Administrator. Diese Rolle erhält CONNECT, Schema-USAGE sowie SELECT, INSERT, UPDATE und DELETE auf entries. Sie darf weder Rollen noch Datenbanken oder Tabellen erzeugen und besitzt keine erhöhten Rollenmitgliedschaften. Der tatsächliche Test bestätigte Tabellenrechte und die Ablehnung von CREATE TABLE."),
            ("table",["Datenebene","Sicherheitsmaßnahme"],[("Geheimnisse","Getrennte Admin- und App-Kennwörter; API darf nur die Verbindungs-URL lesen."),("Transport","Private Adressen und verifiziertes TLS; kein sslmode=disable und kein umgangenes Zertifikatsvertrauen."),("Betrieb","Reguläre Verwaltung nutzt ephemere Werte und Write-only-Felder. Importausnahme und anschließende Rotation sind unten eingeordnet."),("Nutzertrennung","Geprüfte Tenant-/Objekt-ID begrenzt sämtliche API-Operationen; fremde Eintrags-IDs werden nicht zugänglich."),("Konfiguration","URL entweder lokal aus Umgebung oder aus der CSI-Datei; doppelte Quellen werden abgelehnt.")]),
            ("p","Die CSI-Datei wird nur in den API-Pod gemountet; keine Kubernetes-Secret-Synchronisierung. Das Datenbankkennwort wird nicht dem Browser übergeben. Die API liest ihre Konfiguration beim Prozessstart: Eine Dateirotation erfordert weiterhin einen kontrollierten Pod-Rollout, damit laufende Verbindungen die neue Konfiguration übernehmen."),
            ("small","Automatisierte SQL-Kennwortrotation ist nicht Teil dieses Projekts. Die geplante Ablaufzeit verlangt eine koordinierte Aktualisierung von Key Vault, SQL-Rolle und API-Rollout. Row-Level Security wurde nicht eingerichtet; die mandantenbezogene Autorisierung liegt in der API."),
        ]),
        ("Die sichere KI-Funktion",[
            ("p","POST /me/notes/summary akzeptiert keinen frei wählbaren Nutzer, keine externen Notiztexte und keinen eigenen Prompt. Die Route erhält die geprüfte Identität, lädt deren tatsächliche gespeicherte Notizen über den vorhandenen Service und sendet nur die benötigten Notizfelder serverseitig an Foundry."),
            ("diagram",["Entra-Nutzer","eigene DB-Notizen","Backend-Prompt\nNotizen als Daten","Foundry-Modell","Textantwort"]),
            ("p","Die Anweisung trennt vertrauenswürdige Regeln und nicht vertrauenswürdige Notizinhalte. Eingebettete Aufforderungen, Regeln zu ändern, fremde Daten abzurufen oder URLs aufzurufen, werden als Text behandelt. Der Modellaufruf enthält tools=[], store=false und keinen vorherigen Gesprächszustand. Eine unerwartete Werkzeugantwort wird abgelehnt. Damit existiert kein Werkzeugpfad, über den Notizinhalte zusätzliche Zugriffe auslösen könnten."),
            ("p","Die Eingabe ist begrenzt. Ein zu großer Gesamtbestand wird mit 413 abgelehnt, ohne still einzelne Notizen auszulassen. Timeout, leere oder unvollständige Modellantworten und Providerfehler führen zu kontrollierten Antworten ohne interne Fehlertexte. Der Minutenbegrenzer gilt pro Nutzer und Prozess; er ist kein globaler, über alle Replikate verteilter Kostenbegrenzer."),
            ("p","Die Cloud-API verwendet ausdrücklich WorkloadIdentityCredential. Fehlt die erwartete Cluster-Identität, wird nicht auf die CLI zurückgefallen. Lokal bleibt AzureCliCredential möglich. Das Modell gpt-5-mini, Version 2025-08-07, GlobalStandard mit Kapazität 1 und die Inferenzrechte sind in Terraform beschrieben. enable_ai_summary steuert Modell und API-Inferenzrecht gemeinsam."),
        ]),
        ("KI-Abnahme mit echten Daten",[
            ("p","Zunächst lieferte ein echter SDK-Aufruf aus dem AKS-API-Pod eine Zusammenfassung von drei synthetischen RAM-Notizen zu Terraform-State, Kubernetes-Probes und JWT. Der protokollierte Modus war workload_identity; es gab keine CLI- oder Schlüsselanmeldung. Diese Prüfung isolierte den tatsächlichen Modellzugriff der Dienstidentität."),
            ("p","Anschließend führte der Nutzer den authentifizierten öffentlichen Endpunkt in Swagger aus. Die API verwendete eine gespeicherte eigene Cloud-Notiz. HTTP 200, note_count=1 und ai_generated=true wurden am 19.11.2026 um 13:57:57 UTC bestätigt."),
            ("table",["Gespeicherter Inhalt","Wiedergabe in der Antwort"],[("Arbeit","LearningSteps läuft auf AKS und ist über HTTPS erreichbar."),("Schwierigkeit","Zusammenspiel von Kubernetes, LoadBalancer und Zertifikaten verstehen."),("Intention","Build, Sicherheitsprüfungen und Deployment mit GitHub Actions automatisieren.")]),
            ("p","Die drei Abschnitte der Antwort passen zur gespeicherten Notiz. Dass GitHub Actions dort noch als nächster Schritt erscheint, ist kein Nachweis eines Projektfehlers: Die KI fasst den gespeicherten Eintrag zusammen und hat keinen Zugriff auf den aktuellen Projektfortschritt. Der Auslieferungsweg war zum Abnahmezeitpunkt bereits funktionsfähig."),
            ("p","Die drei synthetischen Modellnotizen und die eine gespeicherte Notiz sind unterschiedliche Nachweise. Der zweite Fall belegt den vollständigen Nutzerweg über HTTPS, Entra, API, private Datenbank und Foundry. Die frühere Tagesaufgabe wurde laut Nutzer mit Text und Screenshot eingereicht. Ein zweites echtes Entra-Nutzerkonto stand nicht zur Verfügung; Nutzertrennung wurde mit zwei signierten synthetischen Identitäten und echter Testdatenbank geprüft."),
        ]),
        ("Kubernetes und betriebliche Abnahme",[
            ("p","Die API startet mit zwei Replikaten, CPU-/Speicher-Requests und Limits, Topologieverteilung und RollingUpdate mit maxUnavailable=0. Der interne Service verteilt Anfragen auf bereite Pods. Startup-, Liveness- und Readiness-Probes haben unterschiedliche Aufgaben: Liveness prüft nur den Prozess; Readiness prüft zeitlich begrenzt den tatsächlichen Tabellenlesezugriff."),
            ("table",["Versuch","Beobachtung"],[("Ein API-Pod entfernt","Neuer Pod mit anderer UID nach 17,9 Sekunden bereit; weiterer ursprünglicher Pod am Abschluss bereit."),("Begrenzte interne HTTP-Last","Zwei nicht privilegierte Lastgeneratoren rufen ausschließlich GET /health/live auf."),("Hochskalierung","CPU-Messwert steigt; HPA erhöht von zwei auf vier bereite API-Pods."),("Lastende","Last-Job entfernt; nach Messwertverzögerung und Stabilisierung Rückkehr zu zwei bereiten Pods."),("Erfasste Antworten","83.999 plus 84.489 HTTP-200-Antworten, keine gemeldeten Anfragefehler.")]),
            ("p","341 Prozent beziehungsweise zeitweise 500 Prozent sind Anteile am CPU-Request von 100m, nicht Prozent der gesamten Maschine. Der Request ist die Bezugsgröße des HPA. Das Scale-down-Stabilisierungsfenster von 120 Sekunden und verzögerte Messwerte erklären, warum vier Pods nach Lastende vorübergehend erhalten blieben."),
            ("p","Der Lasttest belegt die Autoskalierungsfunktion unter synthetischer HTTP-/CPU-Last. Er prüft weder Datenbank- noch KI-Durchsatz und liefert keine belastbare Kapazitätsplanung. Die Ersatzpod-Prüfung misst Wiederbereitschaft; eine lückenlose Verfügbarkeitsmessung während dieses Versuchs wurde nicht durchgeführt."),
        ]),
        ("Verschlüsselte Datensicherung",[
            ("p","Vor dem vollständigen Abbau wurde der einzige gespeicherte Cloud-Eintrag logisch exportiert. Die Sicherung enthält alle sechs Spalten der Tabelle entries: ID, JSON-Daten, beide Zeitstempel sowie Tenant- und Nutzerkennung. Zusätzliche öffentliche Tabellen würden den Sicherungslauf abbrechen, damit unbekannte Anwendungsdaten nicht unbemerkt fehlen."),
            ("p","Der Export läuft über einen kurzlebigen gehärteten Diagnose-Pod und überprüftes Datenbank-TLS. Zugangsdaten werden nur im Arbeitsspeicher beziehungsweise über Standardinput übergeben. Daten und Zertifikatszustand werden lokal mit AES-256-GCM verschlüsselt. Der Schlüssel bleibt in einem separat geschützten lokalen Ordner und wird weder in Git noch im Abgabepaket gespeichert."),
            ("table",["Sicherungsprüfung","Ergebnis"],[("Inhalt","Ein vollständiger Datensatz einschließlich Eigentümerkennungen und Zeitstempeln."),("Isolierter Restore","Neue zufällig benannte Testdatenbank; vollständiger Daten-SHA-256 identisch; Testdatenbank entfernt."),("Nichtleeres Ziel","Restore in die gefüllte reguläre Tabelle ausdrücklich abgelehnt; kein Überschreiben."),("Nachprüfung","Live-Inhalt nach dem Negativtest und nochmals im Wartungsfenster identisch zur Sicherung."),("Release","Getestete API-/Gateway-Images und verschlüsselter ACME-Zustand zusätzlich archiviert.")]),
            ("p","Diese Sicherung ist eine vollständige Anwendungsdatensicherung für das bekannte Ein-Tabellen-Schema, kein allgemeines PostgreSQL-Clusterbackup. SQL-Schema und Rollen werden aus dem Repository neu eingerichtet. Der Dienst schützt damit Daten unabhängig vom Azure-Server, dessen integrierte Sicherungen beim kompletten Serverabbau keine alleinige Wiederaufbaubasis darstellen sollen."),
        ]),
        ("Vollständiger Infrastrukturtest",[
            ("p",status),
            ("p","Vor der Zerstörung wurden Sicherung und Rücksicherung geprüft, laufende API-Schreibzugriffe im Wartungsfenster angehalten und der Dateninhalt nochmals verglichen. Der öffentliche Kubernetes-Service und das gemountete Zertifikatsvolume wurden kontrolliert entfernt, bevor Terraform die dazugehörige Azure-Infrastruktur abbaut."),
            ("p","Der gespeicherte Destroy-Plan wurde auf genau 45 Anwendungsressourcen in den LearningSteps-Gruppen geprüft und anhand seiner SHA-256-Prüfsumme angewendet. Remote State und fremde Gruppen waren ausgeschlossen. Der Abbau von Key Vault und Foundry bleibt softlöschend; die Schutzmechanismen werden nicht durch Purge umgangen."),
            ("table",["Rekonstruktionsschritt","Prüfziel"],[("Terraform","Leerer Anwendungs-State nach Abbau; vollständiger Apply nach Wiederherstellung geschützter Konten."),("Registry","Archivierte Images erneut geladen, übertragen und AMD64-Manifeste verglichen."),("Datenbank","Schema und App-Rolle neu eingerichtet; Daten nur in eine leere Tabelle restauriert."),("Kubernetes","Neue Cluster-/Namespacekennungen, aktuelle kubeconfig, SA/CSI, API, Service und HPA."),("HTTPS","Zertifikatszustand sicher restauriert; Router nach stabiler öffentlicher HTTP-Erreichbarkeit aktiviert."),("Abschluss","Identischer Dateninhalt, API-/KI-Prüfung, kontrollierte CI-Identität und Terraform No changes.")]),
            ("p","Der unterbrochene Apply hinterließ zwei bereits erstellte Ressourcen außerhalb des gespeicherten State. Nach Prüfung, dass kein Terraform-Prozess mehr lief, wurde die verwaiste Sperre aufgehoben und der Bestand importiert. Der Geheimnisimport liest vorübergehend einen Wert in den privaten State. Deshalb wurde die App-Kennwortversion vor dem Einrichten der SQL-Rolle erneuert und die Ressource wieder auf Write-only umgestellt. Historische State-Versionen bleiben private sensible Betriebsdaten; der alte importierte Wert wird nicht als SQL-Zugang verwendet."),
            ("p","Aktueller Abschlussstatus des Wiederaufbaus: "+str(final.get("summary","Prüfung läuft. Die endgültigen Messwerte werden erst nach dem realen Restore eingetragen."))),
        ]),
        ("Betrieb Kosten und Grenzen",[
            ("p","Die verwendeten zwei Standard_D4s_v6-Knoten wurden mit einem öffentlichen Listenpreis von 0,4344 EUR pro Stunde zusammen ermittelt. Dies ist nur VM-Compute, kein Gesamtpreis. PostgreSQL, Storage, ACR, DNS, IPs, LoadBalancer, Datentransfer und Modellaufrufe kommen hinzu; Verträge und Steuern können die tatsächliche Rechnung verändern."),
            ("p","Für eine normale Pause können AKS und PostgreSQL gestoppt werden. Die Datenbank startet nach sieben Tagen automatisch wieder. Persistent gespeicherte Daten, ACR, DNS, IPs und Disks bleiben gegebenenfalls kostenpflichtig. Ein Modellschalter ersetzt keinen subscriptionweiten Budgetalarm. Kostenkontrolle erfordert das Prüfen der tatsächlichen Azure-Abrechnung."),
            ("p","Die öffentliche Entwickler-IP kann wechseln. Das dafür vorgesehene Werkzeug liest die aktuelle IPv4, ergänzt bei ausdrücklicher Vorbereitung nur diese /32 für die notwendige Terraform-Aktualisierung und erstellt einen Plan. Eine Öffnung für 0.0.0.0/0 ist keine Fehlerbehebung. Die im Projekt beobachtete DNS-/Timeout-Störung der AKS-API wurde auf eine veraltete erlaubte Entwickler-IP zurückgeführt."),
            ("table",["Bewusste Grenze","Folge"],[("Ein Gateway und kleine DB ohne HA","Geeignet für das Lernprojekt; kein vollständiger Produktions-HA-Nachweis."),("Prozesslokales KI-Limit","Mehrere Pods besitzen getrennte Limits; kein globaler Ausgabendeckel."),("Readiness mit DB-Verbindung","Praktischer Funktionsnachweis, aber zusätzliche Verbindungslast."),("Keine Monitoring-Erweiterung","Prometheus/Grafana ist laut Aufgabenstellung optional und ausdrücklich nicht umgesetzt."),("Schlüssel lokal für Restore","Verlust des lokalen Entschlüsselungsschlüssels verhindert die Wiederherstellung.")]),
        ]),
        ("Lernerkenntnisse und Entscheidungen",[
            ("p","Der wichtigste Fortschritt ist die Trennung von gewünschtem Zustand und einmaliger manueller Einrichtung. Terraform beschreibt Azure-Ressourcen, Kubernetes beschreibt Prozesse und Betriebsregeln, und GitHub Actions liefert nur den geprüften Anwendungsstand aus. Ein erfolgreicher Build allein beweist weder Datenzugriff noch HTTPS oder sichere Nutzertrennung."),
            ("p","Die Fehlersuche wurde durch gezielte Nachweise schneller: Ein privater Netzwerk-Pod prüfte DNS, TCP und TLS ohne SQL-Anmeldung. Danach folgten SQL-Anmeldung, eingeschränkte Rolle und erst anschließend Workload Identity. Beim Gateway wurden Dateirechte und öffentliche Routing-Konvergenz getrennt untersucht. Das verhinderte pauschale Lockerungen von Firewall, TLS oder Dateisystemrechten."),
            ("p","Die Unterschiede zwischen einem Mehrplattform-Index und dem tatsächlichen AMD64-Manifest waren für die Imageintegrität entscheidend. Ein unterschiedlicher Digest bedeutet nicht automatisch geänderten Anwendungscode; die Zuordnung muss jedoch anhand des unveränderlichen Publisher-Indexes geprüft werden. Ein bloßer Tagvergleich genügt nicht."),
            ("p","Die Nutzeranmeldung und die Dienstidentität dürfen nicht vermischt werden. Die Nutzeridentität entscheidet, welche Notizen verarbeitet werden. Die API-Identität erlaubt nur die dafür benötigten Azure-Dienste. Diese Trennung macht auch den KI-Zusatz nachvollziehbar und verhindert, dass Browser oder Notizinhalte Zugriffsschlüssel erhalten."),
            ("p","Beim Neuaufbau war die früher erfolgreiche feste Datenbankzone 3 nicht mehr verfügbar. Nach Entfernen dieser Bindung wählte Azure Zone 2 bei unveränderter B1ms-Größe. Eine SKU-Liste garantiert keine tatsächliche Kapazität. Der vollständige Neuaufbau prüft mehr als Terraform-Syntax: Ein leerer Server braucht Schema und Rollen, eine neue Registry braucht Images, neue Azure-Identitäten brauchen aktuelle Föderation und GitHub-Variablen, und Zertifikate sowie Daten benötigen eine explizite Wiederherstellungsstrategie. Erst die tatsächliche Ausführung schließt diese Lücken."),
        ]),
        ("Nachweisindex und Übergabe",[
            ("table",["Nachweisdatei unter artifacts/","Belegt"],[("github/history-scan-and-delivery-44534120752.json","Erfolgreiche Git-Historienprüfung und automatische Lieferung."),("github/security-gate-negative-log.txt","Absichtlicher Terraform-Sicherheitsfehler mit CRITICAL-Abbruch."),("azure/workload-access-check.json","CSI-Dateizugriff, eingeschränkte App-Anmeldung und Admin-Geheimnis verweigert."),("azure/pod-recovery-check.json","Ersatzpod nach 17,9 Sekunden."),("azure/hpa-scaling-check.json","Hoch- und Rückskalierung mit erfassten HTTP-Antworten."),("azure/foundry-workload-inference-check.json","Echter AKS-Modellaufruf mit Workload Identity."),("azure/cloud-stored-note-summary-check.json","Vom Nutzer bestätigte authentifizierte Zusammenfassung einer gespeicherten eigenen Notiz."),("azure/data-check-check.json","Isolierte Rücksicherung der verschlüsselten Anwendungsdaten."),("azure/restore-empty-rejection-check.json","Verweigerter Restore in eine nichtleere Tabelle."),("azure/evolution-recovery-final.json","Zusammengeführter tatsächlicher Infrastruktur-/Daten-Wiederaufbaunachweis.")]),
            ("p","Die Abgabe enthält Quellen, diesen Bericht, die zusätzliche Ablauferklärung und ausgewählte tokenfreie Nachweise. Lokale Geheimnisse, State, Image-TAR-Archive, private Zertifikate, verschlüsselte Datenbackups und ihre Schlüssel sind absichtlich nicht enthalten. Der Betreiber muss die lokalen Wiederherstellungsdateien separat aufbewahren."),
            ("small","Repository: https://github.com/CyberAlex91/learningsteps\nProjektbrief: LearningSteps Evolution, Weeks 3–6, individuelle Aufgabe. Die tägliche KI-Übung wurde zusätzlich in das bestehende Projekt integriert."),
        ]),
        ("Quellen und technische Referenzen",[
            ("p","Die Aufgabenabdeckung beruht auf dem bereitgestellten Projektbrief und den tatsächlichen Projektartefakten. Technische Referenzen dienen zum Nachvollziehen der verwendeten Funktionen; sie ersetzen keine Ausführungsnachweise."),
            ("table",["Referenz","Verwendeter Zusammenhang"],[("AzureRM Provider v5.14.0","Cognitive Account/Deployment, Feature-Schalter und Soft-Delete-Verhalten."),("Microsoft Azure Identity Python","WorkloadIdentityCredential und die vom AKS-Webhook injizierten Identitätsparameter."),("Microsoft Azure OpenAI RBAC","Cognitive Services OpenAI User als Inferenzrecht ohne Schlüsselverwaltung."),("Gitleaks Dokumentation","Git-Historienmodus, vollständige Maskierung und exakte Fingerprints."),("Kubernetes-Dokumentation","HPA, Ressourcengrößen, Probes und deklarative Deployments."),("Projekt-Quellcode und Messprotokolle","Konkrete Versionen, Befehle, erwartete Schutzgrenzen und beobachtete Ergebnisse.")]),
            ("small","https://github.com/hashicorp/terraform-provider-azurerm/tree/v5.14.0/website/docs\nhttps://learn.microsoft.com/python/api/azure-identity/azure.identity.aio.workloadidentitycredential\nhttps://learn.microsoft.com/azure/foundry-classic/openai/how-to/role-based-access-control\nhttps://github.com/gitleaks/gitleaks\nhttps://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/"),
            ("p","Alle angegebenen Prüfergebnisse beziehen sich auf den dokumentierten Projektstand vom 19.11.2026. Zukünftige Versionen, Modellverfügbarkeit, Quoten, Kosten und Advisories können sich ändern. Die festgelegten Versionen und Images werden vor einem späteren produktiven Einsatz erneut geprüft."),
        ]),
    ])
    return report


def guide(final):
    return [
        ("Was LearningSteps macht",[
            ("p","LearningSteps ist dein persönliches Lerntagebuch. Ein Eintrag beantwortet drei Fragen: Was habe ich bearbeitet? Wo hatte ich Schwierigkeiten? Was möchte ich als Nächstes tun? Die Felder heißen work, struggle und intention. PostgreSQL bewahrt die Einträge dauerhaft auf; FastAPI bietet die Funktionen zum Anlegen, Lesen, Ändern und Löschen."),
            ("p","Die Seite /docs ist Swagger: eine technische Oberfläche zum Ausprobieren der API. Dass sie wie eine Liste von GET-, POST- und PATCH-Aufrufen aussieht, passt zur Backend-Aufgabe. Ein gestaltetes Endnutzer-Frontend wurde nicht verlangt und ist hier nicht zusätzlich gebaut worden. Die Bedienung kann deshalb technisch wirken, obwohl die Funktion dahinter ein einfaches Journal ist."),
            ("table",["Begriff","Bedeutung für dich"],[("GET","Vorhandene eigene Einträge lesen; keine neuen Daten erzeugen."),("POST","Einen neuen Eintrag anlegen oder eine Zusammenfassung anfordern."),("PATCH","Nur bestimmte Felder eines eigenen Eintrags ändern."),("DELETE mit entry_id","Genau einen eigenen Eintrag löschen."),("DELETE ohne entry_id","Alle eigenen Einträge löschen. Nicht zum gewöhnlichen Ausprobieren verwenden.")]),
            ("p","Jeder Eintrag bekommt eine eindeutige ID. Sie ist die Adresse dieses Datensatzes, kein Passwort. Für gezielte Änderungen kopierst du die ID aus der erfolgreichen POST-Antwort. Zwei POST-Ausführungen können zwei verschiedene Einträge erzeugen; zwei GET-Ausführungen lesen denselben aktuellen Datenbestand."),
            ("p","Die KI-Funktion erzeugt keine neue Notiz. Sie liest deine gespeicherten eigenen Notizen und formuliert daraus Gelerntes, Schwierigkeiten und nächste Schritte. Alte Absichten bleiben alte Absichten: Die KI weiß nicht automatisch, welche Schritte du inzwischen tatsächlich erledigt hast."),
        ]),
        ("Wie eine Anfrage durch das System geht",[
            ("diagram",["Du im Browser","HTTPS-Gateway","API mit Identität","private Datenbank"]),
            ("p","Du meldest dich in Swagger über Authorize bei Microsoft Entra an. Der Browser erhält ein zeitlich begrenztes Zugriffstoken und sendet es bei geschützten API-Anfragen mit. Die API prüft Unterschrift, Aussteller, Ziel und benötigte Berechtigung. Erst danach steht fest, welcher Nutzer die Anfrage stellt."),
            ("p","Das öffentliche Gateway stellt die verschlüsselte Verbindung zu deinem Browser bereit. Dahinter erreicht es einen internen Kubernetes-Service. Dieser führt zur laufenden API. Die API verbindet sich über das private Azure-Netz und zusätzlich verifiziertes TLS mit PostgreSQL. Du musst die Datenbank weder öffentlich öffnen noch ein Datenbankkennwort im Browser eingeben."),
            ("h2","Warum es zwei verschiedene Identitäten gibt"),
            ("p","Deine Nutzeridentität entscheidet, welche Notizen dir gehören. Die Identität der Anwendung entscheidet, ob die Anwendung ihr Verbindungsgeheimnis aus Key Vault lesen und Foundry aufrufen darf. Beide Aufgaben brauchen unterschiedliche Rechte. Die Anwendung darf ihren eigenen Azure-Zugang nicht aus einer beliebigen Nutzerangabe im Request ableiten."),
            ("p","Bei der KI-Zusammenfassung lädt die API zuerst deine eigenen Notizen. Erst diese Daten gehen serverseitig zum Modell. Im Browser gibt es keinen Foundry-Schlüssel. Notizinhalte sind für das Modell Daten; sie können keine zusätzlichen Werkzeuge, URL-Aufrufe oder Datenbankabfragen veranlassen, weil der Modellaufruf keine Werkzeuge besitzt."),
        ]),
        ("Welche Programme du wofür öffnest",[
            ("table",["Ort","Dort machen wir diese Arbeit"],[("VS Code mit WSL","Projekt öffnen, Dateien bearbeiten, Git-/Azure-/Terraform-/Kubernetes-Befehle ausführen."),("Docker Desktop unter Windows","Lokale Projektcontainer und lokale Image-Builds bereitstellen."),("Browser","Swagger bedienen, Entra-Anmeldung abschließen, eigene Notizen und Zusammenfassungen ansehen."),("PowerShell","Die vorhandenen Start-Lokal.ps1 und Stop-Lokal.ps1 für den lokalen Test bedienen."),("Azure Portal","Bei Bedarf Ergebnisse und Kosten ansehen; der reguläre Infrastrukturaufbau erfolgt über CLI/Terraform.")]),
            ("h2","Von geschlossenen Programmen zum Projekt"),
            ("p","Öffne Docker Desktop, wenn du lokal entwickeln oder Images bearbeiten möchtest. Öffne anschließend VS Code mit WSL-Verbindung. Im integrierten WSL-Terminal wechselst du in den Projektordner und setzt die beiden lokalen Werkzeugvariablen:"),
            ("code",'cd "/mnt/c/Users/Administrator/Documents/Codex/Cyber Learning/LearningSteps"\nexport PATH="$HOME/.local/share/learningsteps-tools/bin:$PATH"\nexport KUBECONFIG="$HOME/.kube/learningsteps-evolution.yaml"\ngit -C app status --short --branch'),
            ("p","KUBECONFIG wählt ausdrücklich unseren Clusterzugang. Ohne diese Einstellung könnte kubectl eine andere Konfiguration verwenden. Die PATH-Ergänzung verwendet die eigens installierten passenden Werkzeuge. Sie verändert nur dieses Terminal, keine dauerhafte Windows-Einstellung."),
            ("p","In WSL kann zusätzlich eine native Docker-Engine vorhanden sein. Diese ist nicht automatisch Docker Desktop. Deshalb verwenden die bisherigen Projekt-Buildskripte ausdrücklich die Windows-Docker-Datei. Ein leerer docker-ps-Aufruf gegen die andere Engine bedeutet nicht, dass unsere Container gelöscht wurden."),
        ]),
        ("Die Cloud nach einer Pause benutzen",[
            ("p","Beginne mit lesenden Prüfungen. Eine erfolgreiche Azure-Anmeldung in PowerShell ist nicht automatisch dieselbe Anmeldung wie in WSL oder im Entwicklungscontainer. Für unsere Cloud-Befehle zählt die WSL-Azure-CLI."),
            ("code",'az account show --query "{Subscription:name,Status:state}" -o json\npython3 app/scripts/refresh_developer_access.py'),
            ("p","Erwartet wird Alexander Plank - Sub. Das IP-Werkzeug prüft zunächst nur. Hat sich deine öffentliche IPv4 geändert, darf die AKS-API weiterhin nur die neue gezielte /32 erhalten. Mit --prepare wird der notwendige eng begrenzte Zugang vorbereitet und ein Terraform-Plan erstellt. Diesen Plan anschließend lesen und erst dann anwenden."),
            ("code",'python3 app/scripts/refresh_developer_access.py --prepare\nterraform -chdir=app/infra-terraform apply developer-ip.tfplan'),
            ("p","Prüfe anschließend den Betriebszustand von AKS und PostgreSQL. Nur falls sie gestoppt sind, starte sie wieder. Die Startvorgänge können mehrere Minuten dauern. Ein Azure-Status Running allein beweist noch nicht, dass die API-Pods und der öffentliche Weg bereits bereit sind."),
            ("code",'az aks start -g rg-learningsteps-evolution -n aks-learningsteps-evolution\naz postgres flexible-server start -g rg-learningsteps-data \\\n  -n psql-learningsteps-alex-0ad5f630\nkubectl get nodes\npython3 app/scripts/check_https_access.py --timeout 180'),
            ("p","Für die öffentliche Anwendung brauchst du nicht gleichzeitig die lokale PostgreSQL-Entwicklungsumgebung. Sie ist eine getrennte Umgebung. Für lokale Tests verwendest du in PowerShell Start-Lokal.ps1; ein lokal erstellter Eintrag erscheint nicht automatisch in der Cloud-Datenbank."),
        ]),
        ("Eine Notiz bewusst ausprobieren",[
            ("p","Öffne die öffentliche /docs-Seite und melde dich über Authorize an. Führe zunächst GET /me aus. Code 200 bestätigt eine akzeptierte Anmeldung. GET /entries zeigt anschließend deine eigenen vorhandenen Notizen. Behalte den bereits für den Projektbeleg gespeicherten Eintrag unverändert."),
            ("h2","Einen eigenen Demo-Eintrag anlegen"),
            ("p","Öffne POST /entries, wähle Try it out und ersetze die Platzhalter durch einen erkennbaren Demo-Inhalt. Einmal Execute genügt. Kopiere danach die zurückgegebene ID für spätere gezielte Änderungen."),
            ("code",'{\n  "work": "Ich teste LearningSteps nach dem Wiederaufbau.",\n  "struggle": "Die Aufgaben von API und Datenbank unterscheiden.",\n  "intention": "Meinen Demo-Eintrag gezielt ändern und wieder löschen."\n}'),
            ("p","Rufe GET /entries erneut auf. Öffne zum Ändern PATCH /entries/{entry_id}, trage die gerade erzeugte Demo-ID ein und sende nur das Feld, das du ändern möchtest. Prüfe anschließend per GET, ob genau dieser Datensatz aktualisiert wurde."),
            ("code",'{"intention": "Als Nächstes die Zusammenfassung der eigenen Notizen testen."}'),
            ("p","Wenn du die Demo aufräumen willst, verwende ausschließlich DELETE /entries/{entry_id} mit deiner Demo-ID. Der Sammellösch-Endpunkt DELETE /entries ist dafür unnötig. Die übrigen Notizen und der Projektbeleg sollen bestehen bleiben."),
        ]),
        ("Die KI-Antwort verstehen",[
            ("p","Öffne POST /me/notes/summary. Als Body reicht {}. Die API akzeptiert hier keine fremde Nutzerkennung und keine frei erfundenen Notiztexte, sondern verwendet die gespeicherten eigenen Einträge. Drücke einmal Execute und warte auf die Antwort."),
            ("table",["Antwortfeld","So liest du es"],[("summary","Die vom Modell formulierten drei Themenbereiche. Prüfe sie gegen deine Notizen."),("note_count","Anzahl der tatsächlich geladenen eigenen Einträge."),("ai_generated","true bei echter Modellantwort; bei leerem Journal gibt es eine normale erklärende Antwort ohne Modellaufruf."),("generated_at","Zeitpunkt der Antwort in UTC, nicht Erstellungszeitpunkt der Notiz.")]),
            ("p","Bei unserer Cloud-Abnahme erschien Code 200 mit note_count=1 und ai_generated=true. Die Antwort nannte AKS/HTTPS, Schwierigkeiten mit LoadBalancer und Zertifikaten sowie die gespeicherte GitHub-Actions-Absicht. Sie hat also die vorhandene Notiz sinnvoll zusammengefasst."),
            ("p","Lies eine KI-Antwort fachlich nach. Ein plausibler Text kann Formulierungen ergänzen oder missverständlich verdichten. Der Sicherheitsteil begrenzt Zugriffswege und behandelt Notizen als Daten; er ist kein Beweis, dass jeder Satz einer Modellantwort zwangsläufig wahr ist. Eine Notiz mit eingebetteten Anweisungen darf keine Werkzeuge oder zusätzlichen Datenzugriffe auslösen."),
            ("p","Bei 429 einen Moment warten und nicht fortlaufend Execute drücken. Bei 503 ist die Dienstanmeldung oder Erreichbarkeit zu prüfen; niemals einen Foundry-Schlüssel in Swagger einsetzen. Für Screenshots nur den Response body aufnehmen. Der darüber angezeigte Curl-Befehl enthält bei Anmeldung das Bearer-Token und gehört nicht in die Abgabe."),
        ]),
        ("Was bei einem Git-Push passiert",[
            ("p","Du änderst Quellen in VS Code und kontrollierst Git-Diff und Tests. Ein Commit beschreibt einen nachvollziehbaren Stand. Der Push lädt diesen Stand hoch und startet GitHub Actions. Das bedeutet noch nicht automatisch, dass ungeprüfter Code bereits in Azure läuft."),
            ("diagram",["Änderung und Commit","Push und Prüfungen","geprüftes Image","berechtigter Rollout"]),
            ("p","Fehlgeschlagene Tests oder HIGH-/CRITICAL-Befunde stoppen den Ablauf. Der erfolgreiche Testzweig demonstrierte genau das: Eine absichtlich offene SSH-Regel wurde erkannt. Wir haben sie nie in Azure angewendet. Allein die Prüfdatei im isolierten Proof-Branch reichte für den roten Workflow."),
            ("p","Bei erfolgreicher Prüfung wird dasselbe geprüfte Image ausgeliefert. Der Lieferjob erhält eine kurzlebige Azure-Anmeldung über die festgelegte GitHub-Föderation. Ein Pull Request von fremdem oder nicht vertrauenswürdigem Code erhält diese Auslieferungsrechte nicht. Das Image wird per Digest statt allein per veränderlichem Tag in AKS eingetragen."),
            ("code",'git -C app status --short --branch\ngit -C app diff --check\ngit -C app diff\n# Danach nur bewusst ausgewählte Dateien hinzufügen und committen.\ngit -C app push\ngh run list --repo CyberAlex91/learningsteps --limit 3'),
            ("p","Der freigegebene Lieferbranch ist main. Workflow, zusätzliche Kontextprüfung und Entra-Föderation verwenden gemeinsam genau diesen Branch. Der frühere Feature-Branch bleibt Entwicklungshistorie. Neue Änderungen werden geprüft und nach main übernommen; erst ein erfolgreicher main-Push darf ausliefern. Einzelne Branchnamen nicht unabhängig voneinander ändern."),
        ]),
        ("Warum Kubernetes sich selbst repariert",[
            ("p","Ein Deployment beschreibt die gewünschte Zahl gleicher API-Pods. Wird einer entfernt, vergleicht Kubernetes Wunsch und Wirklichkeit und startet Ersatz. In unserem kontrollierten Versuch war ein neuer Pod nach 17,9 Sekunden bereit. Die Daten gingen dadurch nicht verloren: Sie liegen in PostgreSQL und nicht im beschreibbaren Dateisystem des API-Containers."),
            ("p","Readiness bestimmt, ob ein Pod Anfragen erhalten soll. Liveness prüft, ob der Prozess grundsätzlich lebt. Ein kurzzeitig nicht erreichbarer Datenbankserver soll den Pod nicht in eine sinnlose Neustartschleife treiben; deshalb führt nur Readiness die begrenzte DB-Prüfung aus. Startup gibt dem Prozess zusätzlich Zeit zum Anlaufen."),
            ("p","Der HPA beobachtet CPU-Verbrauch relativ zum CPU-Request. Der Request ist die angeforderte Planungsgröße und nicht das CPU-Limit. Ein Wert von 341 Prozent kann deshalb sinnvoll sein, wenn ein Pod deutlich mehr als seinen Request verbraucht, aber noch innerhalb seines Limits arbeitet."),
            ("code",'python3 app/scripts/check_pod_recovery.py\npython3 app/scripts/check_hpa_scaling.py'),
            ("p","Diese Befehle sind gezielte Abnahmen und nicht bei jedem Start nötig. Der erste entfernt einen API-Pod. Der zweite erzeugt zeitlich begrenzte interne HTTP-Last und räumt seine Lastgeneratoren wieder auf. Er benötigt mehrere Minuten, weil Messwerte und Rückskalierung verzögert reagieren. Parallel dazu keine CI-Auslieferung oder zweiten Lasttest starten."),
            ("p","Die bestandene Skalierung 2 → 4 → 2 beweist die Funktion, nicht unbegrenzte Leistung. Das einzelne Gateway und die kleine Datenbank bleiben mögliche Engpässe. Ein richtiger Kapazitätstest müsste repräsentative Anfragen, Datenbankzugriffe, KI-Latenz und längere Messzeiträume getrennt untersuchen."),
        ]),
        ("Sichern bevor etwas zerstört wird",[
            ("p","Terraform sichert keine Inhalte deiner Notizen. Es beschreibt Ressourcen wie Server, Netze und Identitäten. Ein neu angelegter PostgreSQL-Server ist zunächst leer. Deshalb brauchen wir neben Quellcode und State eine unabhängige Datensicherung."),
            ("code",'python3 app/scripts/cloud_data_backup.py backup\npython3 app/scripts/cloud_data_backup.py check \\\n  --manifest PFAD_ZUM_AUSGEGEBENEN_MANIFEST\npython3 app/scripts/recovery.py prepare \\\n  --backup PFAD_ZUM_AUSGEGEBENEN_MANIFEST'),
            ("p","backup verschlüsselt alle bekannten Anwendungsdaten. check restauriert sie in einer neuen Testdatenbank und vergleicht den vollständigen Inhalt. Erst dieser zweite Schritt zeigt, dass eine vorhandene Datei auch praktisch nutzbar ist. Der Test entfernte anschließend ausschließlich seine eigene Testdatenbank."),
            ("p","prepare bewahrt die tatsächlich getesteten API-/Gateway-Images und den verschlüsselten Zertifikatszustand. Wird auch die Registry gelöscht, reicht ein alter Image-Digest allein nicht: Der Inhalt muss noch an einer unabhängigen Stelle vorhanden sein. Gleiches gilt für die privaten Zertifikatsschlüssel."),
            ("p","Der Entschlüsselungsschlüssel bleibt lokal unter .secrets/backups. Er gehört nicht in den Bericht, nicht in Git und nicht in das Abgabepaket. Die Windows-Ordnerrechte begrenzen den Zugriff. Bewahre Schlüssel und verschlüsselte Sicherung getrennt auf; ohne passenden Schlüssel ist eine korrekte AES-GCM-Datei nicht restaurierbar."),
            ("p","Das Werkzeug restore-empty verweigert das Schreiben in eine bereits gefüllte Zieltabelle. Wir haben diese Sperre tatsächlich ausgelöst und danach die unveränderten Live-Daten erneut geprüft. Damit ist die Sicherung nicht bloß ein Skriptversprechen."),
        ]),
        ("Den vollständigen Neuaufbau nachvollziehen",[
            ("p","Der vollständige Test ist ein Wartungsfenster. Zuerst wird die API angehalten, damit nach dem letzten Datenvergleich keine neuen Notizen hinzukommen. Der öffentliche Kubernetes-Service und das Zertifikatsvolume werden geordnet entfernt. Erst dann darf der geprüfte Terraform-Destroy-Plan die Azure-Anwendungsressourcen abbauen."),
            ("p","Unsere separate Remote-State-Gruppe bleibt bestehen. Key Vault und Foundry verwenden Soft-Delete; der geschützte Tresor wird nicht zwangsweise gepurgt. Die Wiederherstellung behandelt diese Dienstzustände ausdrücklich. Ein kompletter Neuaufbau bedeutet hier keine Umgehung von Azure-Löschschutz."),
            ("code",'python3 app/scripts/recovery.py plan-destroy\n# Vollständigen Plan prüfen, dann den gespeicherten Plan anwenden.\nterraform -chdir=app/infra-terraform apply evolution-destroy.tfplan\nterraform -chdir=app/infra-terraform state list\npython3 app/scripts/recovery.py infrastructure\npython3 app/scripts/recovery.py bootstrap\npython3 app/scripts/recovery.py restore-guards'),
            ("p","infrastructure legt die Azure-Ressourcen wieder an. bootstrap stellt Images, Datenbankschema, SQL-Rechte und gesicherte Notizen wieder her. Es aktualisiert die Clusterkonfiguration und die neu entstandene GitHub-Identität. Der Zertifikatszustand wird vor dem Gateway-Start restauriert; die öffentliche Konfiguration wird erst nach stabiler Erreichbarkeit aktiviert."),
            ("p","Zum Schluss müssen Dateninhalt, neue Clusterkennungen, zwei bereite API-Pods, gültiges öffentliches HTTPS, echter Modellzugriff und Terraform No changes überprüft sein. Der konkrete Abschlussstatus dieses Laufs lautet: "+str(final.get("summary","Noch in Prüfung. Dies ist die Ablaufbeschreibung, kein vorweggenommener Erfolgsnachweis."))),
            ("small","Die detaillierten Voraussetzungen, Wiederholungsgrenzen und Dateipfade stehen in RECOVERY.md. Diesen Ablauf nicht als gewöhnlichen täglichen Start verwenden."),
        ]),
        ("Pause Fehlerbilder und nächste Pflege",[
            ("p","Eine normale Pause ist kleiner als ein vollständiger Abbau. Prüfe zuerst, dass keine Auslieferung und keine Sicherung mehr läuft. Danach kannst du AKS und PostgreSQL gezielt stoppen. Bereits angefallene Kosten verschwinden dadurch nicht, und gespeicherte Ressourcen können weiter Kosten verursachen."),
            ("code",'az aks stop -g rg-learningsteps-evolution -n aks-learningsteps-evolution\naz postgres flexible-server stop -g rg-learningsteps-data \\\n  -n psql-learningsteps-alex-0ad5f630'),
            ("p","PostgreSQL startet nach sieben Tagen automatisch wieder. Zum Fortsetzen zunächst Azure-Anmeldung und öffentliche Entwickler-IP prüfen, dann die Dienste bei Bedarf starten und die echte HTTPS-Abnahme wiederholen. Modellaufrufe verursachen auch bei kleinen Tests Verbrauchskosten; häufiges erneutes Execute ist kein Fehlerdiagnoseverfahren."),
            ("table",["Beobachtung","Gezielter nächster Schritt"],[("kubectl-Timeout nach IP-Wechsel","Aktuelle /32 und erlaubte API-Adressen mit refresh_developer_access.py vergleichen."),("401 bei eigenen Notizen","Entra-Anmeldung und den passenden API-Scope prüfen; keine DB-Rechte erweitern."),("Readiness 503","Private DNS-/TLS-/Datenbankverbindung prüfen; Liveness nicht mit DB-Abhängigkeit überladen."),("Ungültiges HTTPS-Zertifikat","Gateway-/ACME-Zustand und öffentliche Konvergenz prüfen; niemals TLS-Verifikation abschalten."),("KI 503 oder 502","Identitätsmodus, Modellverfügbarkeit und Inferenzrecht prüfen; keine Schlüssel in Swagger eintragen."),("Restore bricht ab","Manifest, Schlüssel, Hash und leeres Ziel kontrollieren; vorhandene Notizen nicht pauschal löschen.")]),
            ("p","Für produktive Nutzung wären insbesondere Gateway-/Datenbank-HA, globales Rate-/Kostenlimit, automatisierte Kennwortrotation und Monitoring auszubauen. Prometheus/Grafana blieb im Rahmen dieser ausdrücklich optionalen Teilaufgabe offen. Die Kernnachweise für Container, IaC, Sicherheits-Pipeline, Auslieferung, Skalierung und Wiederherstellung sind getrennt dokumentiert."),
        ]),
    ]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--draft",action="store_true");args=parser.parse_args()
    file=ROOT/"artifacts/azure/evolution-recovery-final.json"
    final=json.loads(file.read_text()) if file.exists() else {}
    if not args.draft and not final.get("passed"):
        raise SystemExit("Final reports require actual successful recovery evidence; use --draft for QA")
    report=contents(final)
    print(write_document("LearningSteps-Evolution-Projektbericht","Technischer Projektbericht","Automatisierte Azure-Architektur",report,args.draft))
    print(write_document("LearningSteps-Evolution-Ablauf","Ablauf zum Verstehen und Nachmachen","Vom Nutzerklick zum sicheren Neuaufbau",guide(final),args.draft))


if __name__ == "__main__":
    main()
