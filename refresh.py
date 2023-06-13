import requests
from credentials import refresh_token, client_secret_base64

class TokenRefresh:
    def __init__(self):
        self.refresh_token = refresh_token
        self.client_secret_base64 = client_secret_base64

    def refresh_spotify_token(self):
        query = 'https://accounts.spotify.com/api/token'

        response = requests.post(
            query,
            data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            headers = {"Authorization": f"Basic {self.client_secret_base64}"}
        )

        if response.status_code != 200:
            print('[ RESPONSE ERROR ] ... terminated Program')
            print(response.text)
            quit()

        new_token = response.json()['access_token']
        print("new Token:", new_token)

        return new_token