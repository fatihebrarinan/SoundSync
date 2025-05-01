import io

import qrcode
import requests
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, redirect, send_file
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os

load_dotenv()

# Spotify API Bilgileri
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

MEKAN_ID = int(os.getenv("MEKAN_ID", 1))

# OAuth Yapılandırması
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read",
)

app = Flask(__name__)

# app route login spotify dan izin alma kısmını yapıyor
@app.route("/login")
def login():
    # Redirect user to Spotify's authorization page
    auth_url = (
        "https://accounts.spotify.com/authorize?"
        f"client_id={SPOTIFY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=user-top-read"  # Required scope for your project
        "&show_dialog=true"
    )
    return redirect(auth_url)

@app.route('/generate_qr')
def generate_qr_route():
    return generate_qr(MEKAN_ID)

# app route callbackte token alıp bu tokenle en çok dinlenilen şarkıları çekiyoruz
@app.route("/callback")
def callback():
    code = request.args.get("code")

    # Request access token
    token_url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code != 200:
        print("Token exchange failed:", response.status_code, response.text)
        return "Authentication error", response.status_code

    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        print("No access token received:", token_data)
        return "Authentication error", 400

    top_tracks_json = get_top_tracks(access_token=access_token)
    print(top_tracks_json)

    for track in top_tracks_json.get('items', []):
        track_name = track['name']
        track_id = track['id']
        save_track_to_db(track_id, track_name)

    return redirect("http://localhost:5000/dj")

def generate_qr(mekan_id):
    url = f"http://localhost/login"

    # QR kod oluştur
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # QR kodunu bellekte sakla
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # QR kodunu kullanıcıya gönder
    return send_file(buf, mimetype="image/png")

# APp route djde en çok dinlenilen şarkıları bir liste halinde kullanıcıya sunuyoruz
@app.route('/dj')
def dj_dashboard():
    top_tracks = get_top_tracks_from_db()
    html = "<h1>DJ Panosu</h1><ul>"
    for track in top_tracks:
        html += f"<li>{track[0]} - {track[1]} oy</li>"
    html += "</ul>"
    return html


def get_top_tracks(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    parameters = {
        "time_range": "short_term",
        "limit": 10,
    }

    response = requests.get(
        "https://api.spotify.com/v1/me/top/tracks",
        params=parameters,
        headers=headers,
        timeout=10
    )

    # Check if the request was successful
    if response.status_code != 200:
        print("Error fetching top tracks:", response.status_code, response.text)
        return {}

    try:
        return response.json()
    except Exception as e:
        print("JSON decode error:", e, response.text)
        raise


# Initialize the database
def initialize_db():
    conn = sqlite3.connect('tracks.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            name TEXT,
            votes INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            vote_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0,
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        )
    ''')
    conn.commit()
    conn.close()

def save_track_to_db(track_id, track_name):
    conn = sqlite3.connect('tracks.db')
    cursor = conn.cursor()

    # Insert track if it does not exist
    cursor.execute('''
        INSERT OR IGNORE INTO tracks (id, name, votes)
        VALUES (?, ?, 0)
    ''', (track_id, track_name))

    # Insert a new vote with current timestamp
    cursor.execute('''
        INSERT INTO votes (track_id, vote_time, processed)
        VALUES (?, ?, 0)
    ''', (track_id, datetime.now()))

    # Increment vote count for the track
    cursor.execute('''
        UPDATE tracks
        SET votes = votes + 1
        WHERE id = ?
    ''', (track_id,))

    conn.commit()
    conn.close()

def decrement_old_votes():
    conn = sqlite3.connect('tracks.db')
    cursor = conn.cursor()

    # Calculate the time threshold (1.5 hours ago)
    time_threshold = datetime.now() - timedelta(minutes= 1)

    # Select votes older than 1.5 hours that haven't been processed
    cursor.execute('''
        SELECT vote_id, track_id FROM votes 
        WHERE vote_time < ? AND processed = 0
    ''', (time_threshold,))
    old_votes = cursor.fetchall()

    for vote_id, track_id in old_votes:
        # Decrement vote count for the track if it's above 0
        cursor.execute('''
            UPDATE tracks
            SET votes = CASE WHEN votes > 0 THEN votes - 1 ELSE 0 END
            WHERE id = ?
        ''', (track_id,))

        # Mark the vote as processed
        cursor.execute('''
            UPDATE votes
            SET processed = 1
            WHERE vote_id = ?
        ''', (vote_id,))

    conn.commit()
    conn.close()

# Initialize the database
initialize_db()

# Start the background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(decrement_old_votes, 'interval', minutes=1)  # Run every minute
scheduler.start()

def get_top_tracks_from_db():
    import sqlite3
    conn = sqlite3.connect('tracks.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, votes FROM tracks ORDER BY votes DESC LIMIT 10')
    top_tracks = cursor.fetchall()
    conn.close()
    return top_tracks


if __name__ == '__main__':
    app.run(debug=True)

