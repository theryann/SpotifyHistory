import requests
import time
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
        """ [REQUEST] make GET request to API and save JSON into self.response_json variable and optional as recent.json file"""

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
        return
        with open('recent.json', 'w') as fd:
            json.dump(self.response_json, fd)

    def save_songs_to_list(self):
        """ [OFFLINE] parse data from JSON and write to CSV """
       
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
                artist      = song['track']['artists'][0]['id']


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


    def update_song_database_with_history_data(self):
        """ [OFFLINE] goes through the csv file and wirtes all songs that appear for the first time in the database.json """
        
        with open('song_database.json', 'r') as fd:
            database = json.load(fd)
        
        with open('history.csv', 'r') as fd:
            reader = csv.reader(fd)
            for line in reader:
                if line[1] not in database:
                    song_attributes = {
                        "titel"       : line[2],
                        "album"       : line[4],
                        "duration"    : line[3],
                        "popularity"  : line[5],
                        "is_explicit" : line[6],
                        "artist"      : [],
                        "genre"       : []
                    }                    
                    
                    for artist in line[7].split(','):
                        song_attributes["artist"].append(artist.strip())                    
                        
                    database[line[1]] = song_attributes
                    
        with open('song_database.json', 'w') as fd:
            json.dump(database, fd)
         
    def update_song_database_with_audio_features(self):
        with open('song_database.json', 'r') as fd:
            database = json.load(fd)
            
        track_ids = []
        
        number_of_requests = 0
        
        for i, song_id in enumerate(database):
            
            # filling 10 new track id list
            if len(track_ids) < 10:
                if "audio-features" not in database[song_id]:
                    track_ids.append(song_id)
                    print('appended', song_id)
                    
            # making bulk request for all IDs
            else: 
                ids_string = ','.join(track_ids)
                        
                result = self.get_multiple_audio_features(ids_string)
                number_of_requests += 1                
                
                # bad response handeling:
                if not "audio_features" in result:
                    print('ERROR:', result)
                    break
                
                # append succesful response to database
                for track in result["audio_features"]:
                    id = track["id"]
                    database[id]["audio-features"] = track
                    
                track_ids = []
                
                if number_of_requests == 5:
                    break

        
        # write updated database to JSON            
        with open('song_database.json', 'w') as fd:
            json.dump(database, fd)
            
    def update_song_database_with_artists(self):
        with open('song_database.json', 'r') as fd:
            song_database = json.load(fd)
        
        number_of_requests = 0
        
        track_ids = []
        
        for song_id in song_database:
            if len(track_ids) < 10:
                if type(song_database[song_id]["artist"][0]) is not dict:
                    track_ids.append(song_id)
                    
            else:
                songs = self.get_multiple_tracks(','.join(track_ids))
                number_of_requests += 1
                
                if not "tracks" in songs:
                    print('[ ERROR ]', songs)
                    break
                
                for track in songs["tracks"]:
                    artist_ids_string = ','.join(artist["id"] for artist in track["artists"]) 
                    
                    artists = self.get_multiple_artists(artist_ids_string)
                    number_of_requests += 1
                    
                    if not "artists" in artists:
                        print('[ ERROR ]', songs)
                        break
                    
                    song_database[track["id"]]["artist"] = artists["artists"]
                    print("Added for", song_database[track["id"]]['titel'])
                    
                    track_ids = []
                    break
                
        
        # write updated database to JSON            
        with open('song_database.json', 'w') as fd:
            json.dump(song_database, fd)
            

    def get_audio_features(self, id):
        """ [REQUEST] param: id,
            makes GET request and returns audio features of ONE Track
        """        
        
        query = f'https://api.spotify.com/v1/audio-features/{id}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        return response.json()
        
    def get_multiple_audio_features(self, ids):
        """ [REQUEST] param: ids, comma seperated,
            makes GET request and returns audio features of MULTIPLE Tracks
        """ 
        
        query = f'https://api.spotify.com/v1/audio-features?ids={ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        print('[ REQUEST ] multiple audio features')

        return response.json()
        
    def get_multiple_tracks(self, ids):
        """ [REQUEST] param: ids, comma seperated,
            makes GET request and returns MULTIPLE Tracks
        """ 
        
        query = f'https://api.spotify.com/v1/tracks?ids={ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        print('[ REQUEST ] multiple artists features')

        return response.json()
    
    def get_multiple_artists(self, ids):
        """ [REQUEST] param: ids, comma seperated,
            makes GET request and returns artists of MULTIPLE Tracks
        """ 
        
        query = f'https://api.spotify.com/v1/artists?ids={ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        print('[ REQUEST ] multiple artists features')

        return response.json()
    
    def get_artists(self, id):
        """ [REQUEST] param: ids, comma seperated,
            makes GET request and returns artists of MULTIPLE Tracks
        """ 
        
        query = f'https://api.spotify.com/v1/artists/id={id}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        print('[ REQUEST ] multiple artists features')

        return response.json()
        



if __name__ == "__main__":

    songs = RecentSongs()
    songs.find_songs()
    songs.save_songs_to_list()
    songs.update_song_database_with_history_data()
    songs.update_song_database_with_audio_features()
    songs.update_song_database_with_artists()
    

