# Podcast RSS zu Discord Webhook

Ein Python-Script, das RSS-Feeds von Podcasts überwacht und neue Episoden automatisch über Discord Webhooks ankündigt. Optional kann die Spotify API verwendet werden, um direkte Links zu Spotify-Episoden und -Shows bereitzustellen.

## Funktionen

- Überwacht mehrere Podcast RSS-Feeds
- Sendet Benachrichtigungen über Discord Webhooks
- Extrahiert Podcast-Informationen (Titel, Beschreibung, Datum, Dauer, etc.)
- Unterstützt Rollen-Erwähnungen in Discord
- Optionale Spotify API-Integration für direkte Links zu Episoden und Shows
- Anpassbare Bot-Namen und -Avatare für die Discord-Nachrichten
- Speichert bereits gesendete Episoden in einer SQLite-Datenbank

## Voraussetzungen

- Python 3.9 oder höher
- Pip (Python-Paketmanager)
- Zugang zu Discord Webhooks
- Optional: Spotify Developer-Konto für API-Zugriff

## Installation

1. Klone das Repository oder lade die Dateien herunter:
   ```bash
   git clone https://git.fastm.de/Max/Podcast-Discord-Notification.git
   cd podcast-rss-discord
   ```

2. Erstelle eine virtuelle Python-Umgebung und installiere die erforderlichen Pakete:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   pip install feedparser requests python-dotenv zoneinfo
   ```

3. Passe die ```.env```-Datei an deine Bedürfnisse an (siehe Konfiguration unten)

4. Passe das Ausführungsscript ```run_spotify_rss.sh``` an, falls der Pfad abweicht:
   ```bash
   #!/bin/bash
   cd /pfad/zu/deinem/projekt
   source venv/bin/activate
   python spotify_rss.py
   ```

5. Mache das Ausführungsscript ausführbar:
   ```bash
   chmod +x run_spotify_rss.sh
   ```

## Konfiguration

Die ```.env```-Datei enthält alle notwendigen Konfigurationsoptionen. Eine Beispiel-Datei ist bereits im Repository enthalten:

```
# Spotify API Zugangsdaten (optional) Wird Genutzt um die Aktuelle Folge richtig zu verlinken!
# SPOTIFY_CLIENT_ID=dein_spotify_client_id
# SPOTIFY_CLIENT_SECRET=dein_spotify_client_secret

# Feed 1 Konfiguration
FEED_URL_1=https://anchor.fm/s/abc123/podcast/rss # Link zum RSS Feed von Spotify
WEBHOOK_URL_1=https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz # WebHook URL von Discord Kanal
SPOTIFY_SHOW_ID_1=123456789 # Optional Wird Benötigt Wenn die API Genutzt wird um den Podcast zu dinden!
ROLE_ID_1=123456789123456 # Optional Discord Rollen ID die erwähnt werden soll!
#BOT_NAME_1=Podcast Bot # Optional und können weggelassen werden dann werden RSS Feed Infos genommen
#BOT_AVATAR_1=https://example.com/podcast_logo.png # Optional und können weggelassen werden dann werden RSS Feed Infos genommen

# Feed 2 Konfiguration
# FEED_URL_2=https://anchor.fm/s/abc123/podcast/rss # Link zum RSS Feed von Spotify
# WEBHOOK_URL_2=https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz # WebHook URL von Discord Kanal
# SPOTIFY_SHOW_ID_2=123456789 # Optional Wird Benötigt Wenn die API Genutzt wird um den Podcast zu dinden!
# ROLE_ID_2=123456789123456  # Optional Discord Rollen ID die erwähnt werden soll!
# BOT_NAME_2=Podcast Bot # Optional und können weggelassen werden dann werden RSS Feed Infos genommen
# BOT_AVATAR_2=https://example.com/podcast_logo.png # Optional und können weggelassen werden dann werden RSS Feed Infos genommen

# Feed 3 Konfiguration
# .
# .
# .

# Feed 4 Konfiguration
#. 
#. 
#.
```

### Konfigurationsoptionen

1. **Spotify API Zugangsdaten** (optional):
   - ```SPOTIFY_CLIENT_ID```: Deine Spotify Developer Client ID
   - ```SPOTIFY_CLIENT_SECRET```: Dein Spotify Developer Client Secret
   - Diese werden benötigt, um die Spotify API zu nutzen und Episoden korrekt zu verlinken.

2. **Feed-Konfiguration** (für jeden Feed eine Gruppe):
   - ```FEED_URL_X```: Die URL des RSS-Feeds des Podcasts
   - ```WEBHOOK_URL_X```: Die Discord Webhook URL, an die die Benachrichtigungen gesendet werden
   - ```SPOTIFY_SHOW_ID_X```: Die Spotify Show-ID des Podcasts (optional, wird für die API-Nutzung benötigt)
   - ```ROLE_ID_X```: Die Discord Rollen-ID, die in der Benachrichtigung erwähnt werden soll (optional)
   - ```BOT_NAME_X```: Der Name, der für den Webhook-Bot angezeigt werden soll (optional)
   - ```BOT_AVATAR_X```: Die URL des Avatars für den Webhook-Bot (optional)

Du kannst beliebig viele Feeds konfigurieren, indem du die Nummerierung fortsetzt (FEED_URL_3, WEBHOOK_URL_3, usw.).

### Spotify API einrichten (optional)

1. Besuche [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Melde dich an oder erstelle ein Konto
3. Erstelle eine neue App
4. Kopiere die Client ID und das Client Secret in deine ```.env```-Datei

### Discord Webhook einrichten

1. Öffne Discord und gehe zu dem Server und Kanal, in dem du Benachrichtigungen erhalten möchtest
2. Gehe zu den Kanaleinstellungen → Integrationen → Webhooks → Neuer Webhook
3. Gib dem Webhook einen Namen und wähle optional ein Bild aus
4. Kopiere die Webhook-URL und füge sie in deine ```.env```-Datei ein

### Discord Rollen-ID finden

1. Aktiviere den Entwicklermodus in Discord (Einstellungen → Erweitert → Entwicklermodus)
2. Rechtsklick auf die Rolle → Rollen-ID kopieren
3. Füge die ID in deine ```.env```-Datei ein

### Spotify Show-ID finden

1. Öffne den Podcast in Spotify
2. Kopiere die URL (z.B. ```https://open.spotify.com/show/1a2b3c4d5e6f7g8h9i0j```)
3. Die ID ist der Teil nach ```/show/``` (in diesem Beispiel ```1a2b3c4d5e6f7g8h9i0j```)

## Verwendung

### Manuelle Ausführung

Führe das Script manuell aus:

```bash
./run_spotify_rss.sh
```

### Automatisierung mit Cron (Linux/macOS)

Um das Script regelmäßig auszuführen, kannst du einen Cron-Job einrichten:

1. Öffne die Crontab-Datei:
   ```bash
   crontab -e
   ```

2. Füge eine Zeile hinzu, um das Script z.B. alle 15 Minuten auszuführen:
   ```
   */15 * * * * /pfad/zu/deinem/projekt/run_spotify_rss.sh
   ```

### Automatisierung mit Task Scheduler (Windows)

1. Öffne den Task Scheduler
2. Erstelle eine neue Aufgabe
3. Stelle ein, dass die Aufgabe regelmäßig ausgeführt wird (z.B. alle 15 Minuten)
4. Als Aktion wähle "Programm starten" und gib den Pfad zu deinem Batch-Script an (erstelle eine .bat-Datei mit ähnlichem Inhalt wie das .sh-Script)

## Anpassung der Discord-Nachricht

Die Discord-Nachricht enthält:

- Titel der Episode
- Beschreibung (gekürzt auf 1000 Zeichen)
- Episodennummer (falls im Titel vorhanden)
- Dauer der Episode
- Veröffentlichungsdatum
- Links zur Episode und zur Show (wenn Spotify API aktiviert ist)
- Thumbnail-Bild (aus Spotify oder dem RSS-Feed)
- Name der Podcast-Ersteller (aus dem RSS-Feed extrahiert)

## Verzeichnisstruktur

```
/home/scripts/spotify_rss/
├── spotify_rss.py       # Hauptscript
├── .env                 # Konfigurationsdatei
├── run_spotify_rss.sh   # Ausführungsscript
├── venv/                # Virtuelle Python-Umgebung
└── verplant_rss.db      # SQLite-Datenbank für gesendete Episoden
└── verplant_rss.log     # Log-Datei
```

## Fehlerbehebung

Das Script erstellt eine Log-Datei unter ```/home/scripts/spotify_rss/verplant_rss.log```. Überprüfe diese Datei, wenn Probleme auftreten.

Häufige Probleme:

1. **Keine neuen Episoden gefunden**: Überprüfe, ob der RSS-Feed korrekt ist und neue Episoden enthält.
2. **Spotify API-Fehler**: Überprüfe deine Client ID und Client Secret.
3. **Discord Webhook-Fehler**: Stelle sicher, dass die Webhook-URL gültig ist.
4. **Pfad-Probleme**: Überprüfe, ob die Pfade in ```run_spotify_rss.sh``` korrekt sind.
5. **Berechtigungsprobleme**: Stelle sicher, dass das Ausführungsscript ausführbar ist (```chmod +x run_spotify_rss.sh```).

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz - siehe die LICENSE-Datei für Details.

## Beitragen

Beiträge sind willkommen! Erstelle einfach einen Pull Request oder öffne ein Issue, wenn du Verbesserungsvorschläge hast.

## Danksagung

Dieses Projekt verwendet die folgenden Open-Source-Bibliotheken:
- [feedparser](https://pypi.org/project/feedparser/)
- [requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [zoneinfo](https://docs.python.org/3/library/zoneinfo.html)

