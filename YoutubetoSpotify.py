import spotipy
from spotipy.oauth2 import SpotifyOAuth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import re
import unidecode

# https://developer.spotify.com/
# Replace with placeholders with your credentials
SPOTIPY_CLIENT_ID = 'Your_client_id'
SPOTIPY_CLIENT_SECRET = 'Your_client_secret'
SPOTIPY_REDIRECT_URI = 'http://localhost:2020/callback'

scope = "playlist-read-private playlist-modify-private playlist-modify-public"
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


def get_youtube_playlist_tracks(youtube, playlist_id):
    tracks = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response["items"]:
            video_id = item["snippet"]["resourceId"]["videoId"]  # Get video ID
            video_request = youtube.videos().list(  # Fetch video details
                part="snippet",
                id=video_id
            )
            video_response = video_request.execute()
            channel_title = video_response["items"][0]["snippet"]["channelTitle"]
            video_title = item["snippet"]["title"]
            track, artist = extract_track_and_artist(video_title)

            #Gets "Topic" mostly i should add if else statement for this
            """# Use channel title as artist if artist is not found
            if not artist:
                artist = channel_title"""

            if track:
                tracks.append({"name": track, "artist": artist})

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return tracks


def extract_track_and_artist(video_title):
    # Remove irrelevant parts
    video_title = re.sub(r"\s*(?:\(.*?\)|\[.*?\]|\||♬)\s*$", "",
                         video_title)  # Remove parentheses, brackets, pipes at end
    video_title = re.sub(r"\s*(?:\(Official Music Video\)|\[Official HD Music Video\]|♬)", "", video_title)
    video_title = unidecode.unidecode(video_title)  # Normalize

    # Split by common separators or if there's only one word
    parts = re.split(r"\s*-\s*", video_title)  # Split by hyphen with optional spaces
    if len(parts) < 2:
        parts = re.split(r"\s*:\s*", video_title)  # Split by colon with optional spaces
    if len(parts) < 2:
        parts = [video_title]  # If it's just one part, assume it's the song title
    if len(parts) >= 2:
        return parts[-1].strip(), " ".join(parts[:-1]).strip()  # Last part as title, rest as artist
    else:
        return parts[0].strip(), ""  # Single part is the title, artist is empty


def search_spotify(spotify, track, artist):
    # First, try to find an exact match by track name and artist
    query = f"track:{track} artist:{artist}"
    results = spotify.search(q=query, type="track")
    if results["tracks"]["items"]:
        return results["tracks"]["items"][0]["uri"]

    # If no exact match, try fuzzy matching
    from fuzzywuzzy import fuzz
    for item in results["tracks"]["items"]:
        spotify_track = item["name"]
        spotify_artist = item["artists"][0]["name"]

        # Use fuzzywuzzy's token_set_ratio for more flexibility
        track_score = fuzz.token_set_ratio(track.lower(), spotify_track.lower())
        artist_score = fuzz.token_set_ratio(artist.lower(), spotify_artist.lower())

        # Adjust the threshold
        if track_score >= 65 and artist_score >= 65:
            return item["uri"]

    # If no good match found, return None
    return None


def create_spotify_playlist(spotify, playlist_name, public=True):
    user_id = sp.me()["id"]
    return spotify.user_playlist_create(user_id, playlist_name, public=public)["id"]


def add_track_to_spotify_playlist(spotify, playlist_id, track, artist):

    if artist:  # if there is an artist then search with title and artist
        track_uri = search_spotify(sp, track, artist)
    else:  # if no artist present then just search for the song
        query = f"track:{track}"
        results = spotify.search(q=query, type="track")
        if results["tracks"]["items"]:
            track_uri = results["tracks"]["items"][0]["uri"]
        else:
            track_uri = None

    if track_uri:
        spotify.playlist_add_items(playlist_id, [track_uri])
        print(f"Added track: {track} by {artist or '<Unknown>'} to playlist: {playlist_id}")
    else:
        print(f"Could not find on Spotify: {track} by {artist or '<Unknown>'}")


def main():
    artist = ""
    # Get YouTube playlist ID
    youtube_playlist_id = input("Enter YouTube Music playlist ID: ")

    # Get YouTube playlist tracks
    youtube_tracks = get_youtube_playlist_tracks(youtube, youtube_playlist_id)

    # Get or create Spotify playlist
    spotify_playlist_name = input("Enter Spotify playlist name (or leave empty to create a new one): ")

    if spotify_playlist_name:
        playlists = sp.current_user_playlists()
        for playlist in playlists['items']:
            if playlist['name'] == spotify_playlist_name:
                spotify_playlist_id = playlist['id']
                break
        else:
            spotify_playlist_id = create_spotify_playlist(sp, spotify_playlist_name)
    else:
        spotify_playlist_id = create_spotify_playlist(sp, f"Copy of {youtube_playlist_id}")

    # Add tracks to Spotify playlist
    added_tracks = set()
    for track in youtube_tracks:
        track_uri = search_spotify(sp, track['name'], track['artist'])
        if track_uri:
            add_track_to_spotify_playlist(sp, spotify_playlist_id, track['name'], track['artist'])
        else:
            print(f"Could not find on Spotify: {track['name']} by {track['artist']}")


if __name__ == "__main__":
    main()
