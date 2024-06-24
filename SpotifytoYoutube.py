from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow #0.4.1
import google.oauth2.credentials
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import unidecode

# https://developer.spotify.com/
# Replace with placeholders with your credentials
SPOTIPY_CLIENT_ID = 'Your_client_id'
SPOTIPY_CLIENT_SECRET = 'Your_client_secret'
SPOTIPY_REDIRECT_URI = 'http://localhost:2020/callback'

scope = "playlist-read-private"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=scope))

# https://console.cloud.google.com/apis/dashboard
# YouTube Authentication (Replace placeholder with your credential file)
CLIENT_SECRETS_FILE = "Your_client_file.json"  # Download from Google Cloud Console and put it in the same file
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
credentials = flow.run_local_server(port=0)

youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_spotify_playlist_tracks(playlist_id):
    results = sp.playlist_items(playlist_id)
    tracks = [
        {
            "name": item["track"]["name"],
            "artist": item["track"]["artists"][0]["name"]
        }
        for item in results["items"]
    ]
    return tracks


def search_youtube_music(query):
    request = youtube.search().list(
        part="snippet",
        maxResults=1,  # Get the top result
        q=query,
        type="video"
    )
    response = request.execute()

    if response["items"]:
        return response["items"][0]["id"]["videoId"]
    else:
        print("No tracks found")
        return None


def create_youtube_playlist(playlist_name):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": playlist_name
            },
            "status": {
                "privacyStatus": "private"  # or public
            }
        }
    )
    response = request.execute()
    return response["id"]


def add_video_to_youtube_playlist(playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()


def main():
    spotify_playlist_id = input("Enter Spotify playlist ID: ")
    spotify_tracks = get_spotify_playlist_tracks(spotify_playlist_id)

    youtube_playlist_name = input("Enter YouTube playlist name (or leave empty to create a new one): ")

    if youtube_playlist_name:
        youtube_playlist_id = search_youtube_music(youtube_playlist_name)  # Check if playlist exists
    else:
        youtube_playlist_id = create_youtube_playlist(f"Copy of {spotify_playlist_id}")

    for track in spotify_tracks:
        query = f"{track['name']} - {track['artist']}"
        video_id = search_youtube_music(query)
        if video_id:
            add_video_to_youtube_playlist(youtube_playlist_id, video_id)
            print(f"Added {track['name']} - {track['artist']} to YouTube Music playlist")


if __name__ == "__main__":
    main()