#!/usr/bin/env python3

import os
import json
import feedparser
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Verfügbar in Python 3.9+
from dotenv import load_dotenv
import sqlite3
import logging
import re
from html import unescape
import base64
import time

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/scripts/spotify_rss/discord_rss.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env
load_dotenv("/home/scripts/spotify_rss/.env")

# Spotify API Zugangsdaten
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_TOKEN = None
SPOTIFY_TOKEN_EXPIRY = 0

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect('/home/scripts/spotify_rss/discord_rss.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS last_episodes (
        feed_id TEXT PRIMARY KEY,
        episode_id TEXT,
        published_date TEXT
    )
    ''')
    conn.commit()
    return conn

# Konfiguration aus .env laden
def load_config():
    feeds = []
    i = 1

    while True:
        feed_url = os.getenv(f'FEED_URL_{i}')
        webhook_url = os.getenv(f'WEBHOOK_URL_{i}')
        role_id = os.getenv(f'ROLE_ID_{i}', '')
        bot_name = os.getenv(f'BOT_NAME_{i}', '')  # Optional
        bot_avatar = os.getenv(f'BOT_AVATAR_{i}', '')  # Optional
        spotify_show_id = os.getenv(f'SPOTIFY_SHOW_ID_{i}', '')  # Optional

        if not feed_url or not webhook_url:
            break

        feeds.append({
            'id': i,
            'feed_url': feed_url,
            'webhook_url': webhook_url,
            'role_id': role_id,
            'bot_name': bot_name,
            'bot_avatar': bot_avatar,
            'spotify_show_id': spotify_show_id
        })

        i += 1

    return feeds

# HTML-Tags entfernen
def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# Spotify API Token abrufen
def get_spotify_token():
    global SPOTIFY_TOKEN, SPOTIFY_TOKEN_EXPIRY

    # Prüfe, ob die API-Zugangsdaten vorhanden sind
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        logger.warning("Spotify API Zugangsdaten fehlen. Spotify-Funktionen deaktiviert.")
        return None

    # Prüfe, ob der Token noch gültig ist
    if SPOTIFY_TOKEN and time.time() < SPOTIFY_TOKEN_EXPIRY:
        return SPOTIFY_TOKEN

    # Token ist abgelaufen oder nicht vorhanden, neuen Token anfordern
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        json_result = response.json()

        # Token speichern und Ablaufzeit berechnen (mit 5 Minuten Puffer)
        SPOTIFY_TOKEN = json_result["access_token"]
        SPOTIFY_TOKEN_EXPIRY = time.time() + json_result["expires_in"] - 300

        logger.info("Neuer Spotify API Token abgerufen")
        return SPOTIFY_TOKEN
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Spotify API Tokens: {str(e)}")
        return None

# Suche nach der neuesten Episode in Spotify
def find_latest_spotify_episode(show_id):
    token = get_spotify_token()
    if not token:
        logger.warning("Kein Spotify API Token verfügbar")
        return None

    # Rufe die neuesten Episoden des Podcasts ab
    url = f"https://api.spotify.com/v1/shows/{show_id}/episodes?limit=1"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_result = response.json()

        # Extrahiere die neueste Episode
        episodes = json_result.get("items", [])
        if episodes:
            latest_episode = episodes[0]
            logger.info(f"Neueste Episode auf Spotify gefunden: {latest_episode.get('name')}")
            return latest_episode

        logger.warning(f"Keine Episoden für Show {show_id} gefunden")
        return None
    except Exception as e:
        logger.error(f"Fehler bei der Spotify API Anfrage: {str(e)}")
        return None

# Suche nach einer bestimmten Episode in Spotify anhand des Titels
def search_spotify_episode(title, show_id):
    token = get_spotify_token()
    if not token:
        logger.warning("Kein Spotify API Token verfügbar")
        return None

    # Bereinige den Titel für die Suche
    search_title = title.replace(":", "").replace("&", "").replace("-", "")

    # Begrenze die Suche auf die ersten 60 Zeichen, um bessere Ergebnisse zu erzielen
    if len(search_title) > 60:
        search_title = search_title[:60]

    # Rufe die letzten 10 Episoden des Podcasts ab
    url = f"https://api.spotify.com/v1/shows/{show_id}/episodes?limit=10"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_result = response.json()

        # Extrahiere die Episoden
        episodes = json_result.get("items", [])

        # Suche nach der passenden Episode
        for episode in episodes:
            episode_title = episode.get("name", "")
            # Prüfe, ob der Titel ähnlich ist
            if title.lower() in episode_title.lower() or episode_title.lower() in title.lower():
                logger.info(f"Passende Episode gefunden: {episode_title}")
                return episode

        # Wenn keine passende Episode gefunden wurde, versuche es mit einer allgemeineren Suche
        logger.warning(f"Keine passende Episode für '{title}' in den letzten 10 Episoden gefunden")

        # Verwende die Spotify-Suche API
        search_url = f"https://api.spotify.com/v1/search?q={search_title}&type=episode&limit=10"
        search_response = requests.get(search_url, headers=headers)
        search_response.raise_for_status()
        search_result = search_response.json()

        # Extrahiere die Episoden aus dem Suchergebnis
        search_episodes = search_result.get("episodes", {}).get("items", [])

        # Filtere nach der Show-ID
        for episode in search_episodes:
            if episode.get("show", {}).get("id") == show_id:
                episode_title = episode.get("name", "")
                # Prüfe, ob der Titel ähnlich ist
                if title.lower() in episode_title.lower() or episode_title.lower() in title.lower():
                    logger.info(f"Passende Episode durch Suche gefunden: {episode_title}")
                    return episode

        logger.warning(f"Keine passende Episode für '{title}' gefunden")
        return None
    except Exception as e:
        logger.error(f"Fehler bei der Spotify API Anfrage: {str(e)}")
        return None

# Prüfe auf neue Episoden
def check_for_new_episodes(conn, feeds):
    cursor = conn.cursor()

    for feed_config in feeds:
        feed_id = feed_config['id']
        feed_url = feed_config['feed_url']

        try:
            feed = feedparser.parse(feed_url)

            if not feed.entries:
                logger.warning(f"Keine Einträge im Feed {feed_id} gefunden")
                continue

            latest_entry = feed.entries[0]
            episode_id = latest_entry.id
            published_date = latest_entry.published

            # Debug-Ausgabe des Feeds
            logger.info(f"Feed-Einträge: {len(feed.entries)}")
            logger.info(f"Neuester Eintrag: {latest_entry.title}")
            logger.info(f"Link im Feed: {latest_entry.link}")

            # Prüfe, ob diese Episode bereits gesendet wurde
            cursor.execute("SELECT episode_id FROM last_episodes WHERE feed_id = ?", (str(feed_id),))
            result = cursor.fetchone()

            if not result or result[0] != episode_id:
                # Neue Episode gefunden
                logger.info(f"Neue Episode für Feed {feed_id} gefunden: {latest_entry.title}")

                # Discord-Nachricht senden
                send_discord_notification(feed_config, latest_entry, feed)

                # Datenbank aktualisieren
                cursor.execute(
                    "INSERT OR REPLACE INTO last_episodes VALUES (?, ?, ?)",
                    (str(feed_id), episode_id, published_date)
                )
                conn.commit()
            else:
                logger.info(f"Keine neue Episode für Feed {feed_id} gefunden")

        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Feed {feed_id}: {str(e)}")

# Extrahiere die Episodennummer aus dem Titel
def extract_episode_number(title):
    match = re.search(r'Folge (\d+)', title)
    if match:
        return match.group(1)
    return None

# Extrahiere die Dauer aus dem Feed
def format_duration(duration_str):
    if not duration_str:
        return "Unbekannt"

    # Versuche, die Dauer im Format HH:MM:SS zu parsen
    parts = duration_str.split(':')
    if len(parts) == 3:
        return f"{parts[0]}:{parts[1]}:{parts[2]}"
    return duration_str

# Discord-Benachrichtigung senden
def send_discord_notification(feed_config, episode, feed):
    webhook_url = feed_config['webhook_url']
    role_id = feed_config['role_id']
    bot_name = feed_config['bot_name']
    bot_avatar = feed_config['bot_avatar']
    spotify_show_id = feed_config['spotify_show_id']

    # Podcast-Titel aus dem Feed extrahieren
    podcast_title = feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else ""

    # Erstelle die Erwähnung, falls eine Rolle angegeben ist
    mention = f" <@&{role_id}>" if role_id else ""

    # Titel formatieren
    title = episode.title

    # Beschreibung formatieren
    description = ""
    if hasattr(episode, 'summary'):
        description = unescape(strip_html_tags(episode.summary))
        if len(description) > 1000:
            description = description[:997] + "..."

    # Episodennummer extrahieren
    episode_number = extract_episode_number(title)

    # Dauer formatieren
    duration = "Unbekannt"
    if hasattr(episode, 'itunes_duration'):
        duration = format_duration(episode.itunes_duration)

    # Datum formatieren
    try:
        # Versuche verschiedene Datumsformate
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # Standard mit Zeitzone
            '%a, %d %b %Y %H:%M:%S GMT',  # Mit GMT statt numerischer Zeitzone
            '%a, %d %b %Y %H:%M:%S +0000'  # Mit expliziter UTC-Zeitzone
        ]

        formatted_date = None
        for date_format in date_formats:
            try:
                # Parse das Datum
                parsed_date = datetime.strptime(episode.published, date_format)

                # Wenn keine Zeitzone angegeben ist, nehmen wir UTC an
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)

                # Konvertiere zu deutscher Zeit (Europe/Berlin)
                german_date = parsed_date.astimezone(ZoneInfo("Europe/Berlin"))

                # Formatiere das Datum
                formatted_date = german_date.strftime('%d.%m.%Y um %H:%M Uhr')
                break
            except ValueError:
                continue

        if not formatted_date:
            # Fallback, wenn kein Format passt
            formatted_date = episode.published
    except Exception as e:
        logger.warning(f"Fehler beim Formatieren des Datums: {str(e)}")
        formatted_date = episode.published

    # Standardmäßig den Link aus dem RSS-Feed verwenden
    episode_link = episode.link
    spotify_episode = None
    spotify_show_link = None

    # Versuche, die Episode in Spotify zu finden, wenn API-Zugangsdaten vorhanden sind
    if spotify_show_id and get_spotify_token():
        # Erstelle den Link zur Show
        spotify_show_link = f"https://open.spotify.com/show/{spotify_show_id}"

        # Versuche zuerst, die Episode anhand des Titels zu finden
        spotify_episode = search_spotify_episode(title, spotify_show_id)

        if spotify_episode:
            # Wenn eine passende Episode gefunden wurde, verwende deren Link
            episode_link = f"https://open.spotify.com/episode/{spotify_episode.get('id')}"
        else:
            # Wenn keine passende Episode gefunden wurde, verwende die neueste Episode
            latest_episode = find_latest_spotify_episode(spotify_show_id)
            if latest_episode:
                spotify_episode = latest_episode
                episode_link = f"https://open.spotify.com/episode/{latest_episode.get('id')}"

    # Extrahiere den Namen der Ersteller aus dem RSS-Feed
    creator_name = ""
    if hasattr(episode, 'author'):
        creator_name = episode.author
    elif hasattr(episode, 'creator'):
        creator_name = episode.creator
    elif hasattr(episode, 'authors') and episode.authors:
        creator_name = episode.authors[0].name

    # Versuche, das dc:creator-Element zu finden
    if hasattr(episode, 'dc_creator'):
        creator_name = episode.dc_creator

    # Debug-Ausgabe der verfügbaren Felder im Episode-Objekt
    logger.debug(f"Verfügbare Felder in der Episode: {dir(episode)}")

    # Erstelle die Discord-Embed-Nachricht
    embed = {
        "title": title,
        "description": description,
        "url": episode_link,
        "color": 3447003,  # Blau
        "footer": {
            "text": f"{creator_name} • {formatted_date}" if creator_name else formatted_date
        },
        "author": {
            "name": podcast_title,
            "url": spotify_show_link if spotify_show_link else episode_link
        },
        "fields": [
            {
                "name": "Episode",
                "value": episode_number if episode_number else "Unbekannt",
                "inline": True
            },
            {
                "name": "Dauer",
                "value": duration,
                "inline": True
            }
        ]
    }

    # Füge das Anhören-Feld hinzu
    listen_field_value = f"[Zur Episode]({episode_link})"

    # Füge den Link zur Show hinzu, wenn Spotify-Show-Link verfügbar ist
    if spotify_show_link:
        listen_field_value += f" | [Zur Show]({spotify_show_link})"

    listen_field = {
        "name": "Anhören",
        "value": listen_field_value,
        "inline": False
    }

    embed["fields"].append(listen_field)

    # Füge ein Bild hinzu, falls vorhanden
    if spotify_episode and spotify_episode.get("images"):
        # Verwende das Bild aus Spotify
        embed["thumbnail"] = {"url": spotify_episode.get("images")[0].get("url")}
    elif hasattr(episode, 'image') and episode.image.get('href'):
        # Verwende das Bild aus dem RSS-Feed
        embed["thumbnail"] = {"url": episode.image.get('href')}
    elif hasattr(feed, 'feed') and hasattr(feed.feed, 'image'):
        # Verwende das Podcast-Bild aus dem RSS-Feed
        embed["thumbnail"] = {"url": feed.feed.image.href}

    # Erstelle die Discord-Webhook-Payload
    payload = {
        "content": f"{podcast_title} - {title}{mention}",  # Rollenerwähnung am Ende der Nachricht
        "embeds": [embed]
    }

    # Verwende den Podcast-Namen als Bot-Namen, wenn keiner angegeben ist
    if bot_name:
        payload["username"] = bot_name
    else:
        payload["username"] = podcast_title

    # Verwende das Podcast-Bild als Bot-Avatar, wenn keines angegeben ist
    if bot_avatar:
        payload["avatar_url"] = bot_avatar
    elif hasattr(feed, 'feed') and hasattr(feed.feed, 'image'):
        payload["avatar_url"] = feed.feed.image.href

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        logger.info(f"Discord-Benachrichtigung für Feed {feed_config['id']} erfolgreich gesendet")
    except Exception as e:
        logger.error(f"Fehler beim Senden der Discord-Benachrichtigung: {str(e)}")

def main():
    logger.info("Podcast RSS zu Discord Webhook Script gestartet")

    # Datenbank initialisieren
    conn = init_db()

    # Konfiguration laden
    feeds = load_config()

    if not feeds:
        logger.error("Keine Feeds konfiguriert. Bitte .env-Datei überprüfen.")
        return

    logger.info(f"{len(feeds)} Feeds geladen")

    # Prüfe, ob die Spotify API Zugangsdaten vorhanden sind
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        logger.warning("Spotify API Zugangsdaten fehlen. Spotify-Funktionen deaktiviert.")
    else:
        # Teste die Spotify API-Verbindung
        token = get_spotify_token()
        if token:
            logger.info("Spotify API-Verbindung erfolgreich hergestellt")
        else:
            logger.warning("Spotify API-Verbindung konnte nicht hergestellt werden")

    try:
        check_for_new_episodes(conn, feeds)
        logger.info("Überprüfung abgeschlossen")
    except Exception as e:
        logger.error(f"Fehler bei der Ausführung: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
