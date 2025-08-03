# TI-Monitoring

Dieses Tool dient der Überwachung verschiedener Komponenten der Telematikinfrastruktur (TI).
Es ist modular aufgebaut, sodass sich je nach Bedarf und Systemleistung auch nur einzelne Funktionen nutzen lassen.

Die Funktionen lassen sich wie folgt zusammenfassen:

* __Abruf und Archivierung__<br>
Die Kernfunktionalität besteht in der regelmäßigen Abfrage des Verfügbarkeitsstatus sämtlicher zentraler TI-Komponenten über eine öffentliche Schnittstelle der gematik GmbH. Die Ergebnisse werden strukturiert in einer hdf5-Datei gespeichert und können so auch für umfangreiche statistische Auswertungen verwendet werden.
* __Benachrichtigungen__<br>
Bei Änderungen der Verfügbarkeit können Benachrichtigungen per E-Mail versendet werden. Zur Filterung der Komponenten kann wahlweise eine White- oder Blacklist definiert werden.
* __Web-App__<br>
Der aktuelle Status sämtlicher TI-Komponenten lässt sich nach Produkten gruppiert in einer interaktiven Web-App einsehen. Darüber hinaus lässt sich für die einzelnen Komponenten eine Statistik der letzten Stunden aufrufen.

## Abruf und Archivierung
Abruf und Archivierung erfolgen durch das Skript `cron.py`, das alle fünf Minuten durch einen Cronjob ausgeführt werden sollte. Um möglichst die aktuellsten Daten abzugreifen,  empfiehlt sich ein minimaler Versatz zum Bereitstellungszeitpunkt der Daten:
```
# m h  dom mon dow   command
2-59/5 * * * * /bin/bash -c 'source myenv/bin/activate && python cron.py'
```
Die Daten werden aufbereitet und in der Datei `data.hdf5` gespeichert. Existiert diese noch nicht, wird sie beim ersten Ausführen des Skriptes `cron.py` automatisch erzeugt.

Innerhalb der Datei wird folgende Gruppenstruktur aufgebaut:

```
.
+-- availability
|   +-- CI-0000001
|   +-- CI-0000002
|   +-- ...
+-- configuration_items
    +-- CI-0000001
    +-- CI-0000002
    +-- ...
```

Die Gruppen `availability` und `configuration_items` enthalten jeweils für jedes Konfigurationsobjekt (z.B. `CI-0000001`) eine gleichnamige Untergruppe.

Die Untergruppe des Konfigurationsobjektes in der Gruppe `availability` enthält Datensätze mit der Verfügbarkeit als Integer (0: nicht verfügbar, 1: verfügbar). Der Name des Datensatzes entspricht der Unix-Zeit des Datenpunktes. Bei Aktualisierungen wird ein neuer Datensatz hinzugefügt.

Die Untergruppe des Konfigurationsobjektes in der Gruppe `configuration_items` enthält mehrere Datensätze mit allegemeinen Eigenschaften wie `name`, `product` und `organization`. Außerdem die aktuelle Verfügbarkeit `current_availability` sowie die Veränderung der Verfügbarkeit `availability_difference` in Bezug auf den vorherigen Wert (-1: nicht mehr verfügbar, 0: keine Veränderung, 1: wieder verfügbar). Bei Aktualisierungen werden die vorhandenen Datensätze überschrieben.

Je nach Systemleistung kann es sinnvoll sein, die hdf5-Datei von Zeit zu Zeit archivieren. Hierzu kann die Datei beispielsweise per Cronjob in ein Archiv-Verzeichnis verschoben werden.

## Benachrichtigungen
Auf Wunsch können bei Änderungen der Verfügbarkeit Beanchrichtigungen per E-Mail versendet werden. Dies geschieht ebenfalls über das Skrip `cron.py`, sofern in der Datei `myconfig.py` die Variable `notifications` den Wert `True` besitzt. Die SMTP-Verbindungsdaten werden ebenfalls in der Datei `myconfig.py` hinterlegt.

In der Datei `notifications.json` können mehrere Profile definiert werden. Ein Profil besteht aus folgenden Eigenschaften:

| Name | Beschreibung |
| ----------- | ----------- |
| name | Name des Profils (wird in der Anrede verwendet) |
| mail | E-Mail-Adresse (Empfänger) |
| ci_list | Liste von Konfigurationselementen (z.B. `["CI-000001", "CI-0000002"]`) |
| type | entweder `blacklist` oder `whitelist` (legt fest, wie die Liste der Konfigurationselemente behandelt wird) |

Hier ein fiktives Beispiel für eine E-Mail-Benachrichtigung:
![E-Mail-Benachrichtigung über Störung (fiktives Beispiel)](docs/img/Benachrichtigung%20(Fiktives%20Beispiel).png "E-Mail-Benachrichtigung über Störung (fiktives Beispiel)")

## Web-App
Der aktuelle Status verschiedener Komponenten kann optional auch in Form einer Web-App auf Basis des [Dash-Frameworks](https://dash.plotly.com) bereitgestellt werden. Die App kann z.B. in Kombination mit uWSGi und nginx (ähnlich [wie hier beschrieben](https://carpiero.medium.com/host-a-dashboard-using-python-dash-and-linux-in-your-own-linux-server-85d891e960bc) veröffentlicht werden.

Auf der Startseite der App werden die Komponenten nach Produkt gruppiert dargestellt. Durch Anklicken der Gruppen lassen sich die jeweiligen Komponenten einblenden.
![Screenshot aus der App: Startseite der App](docs/img/App%20Home.png "Startseite der App")
Per Klick auf die ID einer Komponente lässt sich eine Statistik der letzten Stunden aufrufen.
![Screenshot aus der App: Statistik für eine Komponente](docs/img/App%20Statistik.png "Statistik für eine Komponente")
Um eine gute Performance zu gewährlsiten, kann das Zeitfenster der Statistik über die Variable `stats_delta_hours` in der Datei `myconfig.py` reduziert werden. Zudem kann es ratsam sein, die Datei `data.hdf5` regelmäßig zu archivieren bzw. zu leeren.

Soll die Web-App überhaupt nicht genutzt werden, sind folgende Dateien irrelevant und können entfernt werden:

```
.
+-- assets
|   +-- favicon.ico
|   +-- LSR_logo.svg
|   +-- script.js
|   +-- style.css
+-- pages
|   +-- home.py
|   +-- plot.py
+-- app.py

```

---
**DISCLAIMER**

Es handelt sich um ein privates Projekt ohne offiziellen Support. Jegliche Nutzung erfolgt auf eigene Verantwortung. 

Die Daten werden über eine öffentlich erreichbare Schnittstelle der gematik GmbH abgerufen. Eine ausführliche Beschreibung diser Schnittstelle ist öffentlich auf GitHub verfügbar: [https://github.com/gematik/api-tilage](https://github.com/gematik/api-tilage).

---