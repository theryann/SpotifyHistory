import requests
import json
import csv
from secrets import spotify_user_id
from refresh import TokenRefresh


class RecentSongs():

    def __init__(self):
        self.user_id = spotify_user_id
        self.response_json = None

        Refresh = TokenRefresh()    
        self.spotify_token = Refresh.refresh_spotify_token()  # update the API access token for the Spotify API (is only valid for an hour each time)

    def find_songs(self):
        """ make GET request to API and save JSON into self.response_json variable and optional as recent.json file"""

        query = 'https://api.spotify.com/v1/me/player/recently-played?limit=50'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        self.response_json = response.json()

        # writing data to file (while debugging to avoid endless requests)
        # with open('recent.json', 'w') as fd:
        #     json.dump(self.response_json, fd)

    def save_songs_to_list(self):
        """" parse data from JSON and write to CSV """

        # reading data from file (while debugging to avoid endless requests)
        # with open('recent.json') as fd:
        #     self.response_json = json.load(fd)
        
        # create list with songs that are already contained to avoid dublicates
        contained_songs = []
        with open('history.csv', 'r') as history_csv:
            reader = csv.reader(history_csv)
            for line in reader:
                contained_songs.append(line[0])

        # open file to append songs
        with open('history.csv', 'a') as history_csv:
            writer = csv.writer(history_csv, lineterminator='\n')

            # parse Data from JSON
            for song in self.response_json['items']:
                song_id     = song['track']['id']
                song_name   = song['track']['name']
                album       = song['track']['album']['name']
                played_at   = song['played_at']
                duration_ms = song['track']['duration_ms']
                popularity  = song['track']['popularity']
                is_explicit = song['track']['explicit']
                artist      = song['track']['artists'][0]['name']


                # add artists if more than one credited 
                if len(song['track']['artists']) > 1:
                    for art in song['track']['artists']:
                        if song['track']['artists'][0] == art:
                            continue
                        artist += ', ' + art['name']

                # write Data to CSV (history.csv)
                row = [played_at, song_id, song_name, duration_ms, album, popularity, is_explicit, artist]
                
                if played_at in contained_songs:
                    continue
                writer.writerow(row)


    def update_song_database(self):
        pass
        
         
        








if __name__ == "__main__":

    songs = RecentSongs()
    songs.find_songs()
    songs.save_songs_to_list()
    songs.update_song_database()

