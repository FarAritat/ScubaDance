import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

class SpotifyHandler:
    def __init__(self):
        self.client_id = os.getenv("SPOTIPY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing Spotify Credentials in Secrets")

        self.auth_manager = SpotifyClientCredentials(
            client_id=self.client_id, 
            client_secret=self.client_secret
        )
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

    def search_scuba_music(self, query="Scuba Dance", limit=1):
        try:
            results = self.sp.search(q=query, limit=limit, type='track')
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                return track['id']
            return "1REeLUZFTRdtqFLnGNZQF2" # คืนค่า ID สำรองถ้าหาไม่เจอ
        except:
            return "1REeLUZFTRdtqFLnGNZQF2"