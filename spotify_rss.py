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

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/scripts/spotify_rss/verplant_rss.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env
load_dotenv("/home/scripts/spotify_rss/.env")

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect('/home/scripts/spotify_rss/verplant_rss.db')
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

        if not feed_url or not webhook_url:
            break

        feeds.append({
            'id': i,
            'feed_url': feed_url,
            'webhook_url': webhook_url,
            'role_id': role_id
        })

        i += 1

    return feeds

# HTML-Tags entfernen
def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

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

            # Debug-Ausgabe des Datums
            logger.info(f"Datum im Feed: {published_date}")

            # Prüfe, ob diese Episode bereits gesendet wurde
            cursor.execute("SELECT episode_id FROM last_episodes WHERE feed_id = ?", (str(feed_id),))
            result = cursor.fetchone()

            if not result or result[0] != episode_id:
                # Neue Episode gefunden
                logger.info(f"Neue Episode für Feed {feed_id} gefunden: {latest_entry.title}")

                # Discord-Nachricht senden
                send_discord_notification(feed_config, latest_entry, feed.feed.title)

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
def send_discord_notification(feed_config, episode, podcast_title):
    webhook_url = feed_config['webhook_url']
    role_id = feed_config['role_id']

    # Erstelle die Erwähnung, falls eine Rolle angegeben ist
    mention = f"<@&{role_id}> " if role_id else ""

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

    # Erstelle die Discord-Embed-Nachricht
    embed = {
        "title": title,
        "description": description,
        "url": episode.link,
        "color": 3447003,  # Blau
        "footer": {
            "text": f"Jamy und Max • {formatted_date}"
        },
        "author": {
            "name": podcast_title
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

    # Füge ein Bild hinzu, falls vorhanden
    if hasattr(episode, 'image') and episode.image.get('href'):
        embed["thumbnail"] = {"url": episode.image.get('href')}
    elif hasattr(feed, 'feed') and hasattr(feed.feed, 'image'):
        embed["thumbnail"] = {"url": feed.feed.image.href}

    # Füge das große Bild hinzu, falls vorhanden
    if hasattr(episode, 'image') and episode.image.get('href'):
        embed["image"] = {"url": episode.image.get('href')}

    # Erstelle die Discord-Webhook-Payload
    payload = {
        "content": f"{mention}{podcast_title} - {title}",
        "embeds": [embed],
        "username": "Verplant",
        "avatar_url": "https://e.fastm.de/verplant/verplant_logo.jpg"  # Optional: URL zum Avatar
    }

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
    logger.info("Verplant Podcast RSS zu Discord Webhook Script gestartet")

    # Datenbank initialisieren
    conn = init_db()

    # Konfiguration laden
    feeds = load_config()

    if not feeds:
        logger.error("Keine Feeds konfiguriert. Bitte .env-Datei überprüfen.")
        return

    logger.info(f"{len(feeds)} Feeds geladen")

    try:
        check_for_new_episodes(conn, feeds)
        logger.info("Überprüfung abgeschlossen")
    except Exception as e:
        logger.error(f"Fehler bei der Ausführung: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
