import requests
from credentials import tokens

class TokenRefresh:
    def __init__(self, user):
        self.user = user
        self.refresh_token = tokens[user]['refresh_token']
        self.client_secret_base64 = tokens[user]['client_secret_base64']

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