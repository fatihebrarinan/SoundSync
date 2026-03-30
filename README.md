# SoundSync 🎧

A dynamic, Flask-based collaborative music voting platform that integrates with the Spotify Web API. SoundSync allows users to connect their Spotify accounts, fetch their top tracks, and influence a live DJ dashboard through a real-time voting system.

## 🚀 Engineering Highlights

- **Authentication**: Secure user login and token management flow utilizing the Spotify Web API.
- **Vote Decay**: A time based mathematical decay system for votes, ensuring the live music queue remains fresh and prevents older tracks from dominating the board.
- **Background Scheduling**: Engineered an autonomous background scheduler to routinely clean up the SQLite database.
- **Frictionless Onboarding**: Integrated a dynamic QR code login system.

## Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **External APIs**: Spotify Web API (Spotipy)
- **Frontend**: HTML5, CSS3, JavaScript (Jinja2 Templating)

## Installation & Setup

1. Clone the repository:
   ```bash
   git clone [https://github.com/fatihebrarinan/SoundSync.git](https://github.com/fatihebrarinan/SoundSync.git)
   cd SoundSync

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt

3. Set up your Spotify Developer Application:

- Go to the Spotify Developer Dashboard.
- Create an app and get your Client ID and Client Secret.
- Set your Redirect URI to http://localhost:5000/callback.

4. Configure your environment variables
   ```bash
    SPOTIPY_CLIENT_ID=your_client_id_here
    SPOTIPY_CLIENT_SECRET=your_client_secret_here
    SPOTIPY_REDIRECT_URI=http://localhost:5000/callback
    SECRET_KEY=your_flask_secret_key

5. Run the application:
   ```bash
   python spotify.py
