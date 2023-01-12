import requests
import json
import csv
import re

from scrape_lyrics import retrieve_lyrics

from secrets import spotify_user_id
from refresh import TokenRefresh
from database import Database


class RecentSongs:
    """
    legacy class for CSV and JSON Database support. Someday a parentclass for both should be useful
    """

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
        with open('history.csv', 'r', encoding='utf-8') as history_csv:
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
                        artist += ',' + art['id']

                # write Data to CSV (history.csv)
                row = [played_at, song_id, song_name, duration_ms, album, popularity, is_explicit, artist]
                
                if played_at in contained_songs:
                    continue
                writer.writerow(row)


    def update_song_database_with_history_data(self):
        """ [OFFLINE] goes through the csv file and wirtes all songs that appear for the first time in the database.json """
        
        with open('song_database.json', 'r') as fd:
            database = json.load(fd)
        
        with open('history.csv', 'r', encoding='utf-8') as fd:
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
                    
            # making bulk request for all IDs
            else: 
                ids_string = ','.join(track_ids)
                        
                result = self.get_multiple_audio_features(ids_string)
                number_of_requests += 1                
                
                # bad response handeling:
                if not "audio_features" in result:
                    print('ERROR:', result)
                    #continue
                    break
                
                # append succesful response to database
                for track in result["audio_features"]:
                    if track != None:
                        id = track["id"]
                        database[id]["audio-features"] = track
                    
                track_ids = []
                
                if number_of_requests == 5:
                    break

        
        # write updated database to JSON            
        with open('song_database.json', 'w') as fd:
            json.dump(database, fd)
            
    def update_song_database_with_artists(self):
        with open('song_database.json', 'r', encoding='utf-8') as fd:
            song_database = json.load(fd)
        
        number_of_requests = 0
        
        track_ids = []
        
        for song_id in song_database:
            
            if number_of_requests > 50:
                print('\n50 Requests done')
                break
            
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
                    
                
        
        # write updated database to JSON            
        with open('song_database.json', 'w') as fd:
            json.dump(song_database, fd)
    
    def update_history_with_similar_artist_name(self):
        with open('song_database.json', 'r') as fd:
            database = json.load(fd)
            
        history = []
        with open('history.csv', 'r') as fd:
            reader = csv.reader(fd)
            for line in reader:
                history.append(line)
        
        # replacing literal names with artist ID
        for line in history:
            found_artist = False
            if not re.match("[0-9a-zA-Z]{22}", line[7]):
                for song in database:
                    if found_artist:
                        line[7] = ','.join(artist_list)
                        break
                    artist_list = line[7].split(',')
                    for i in range(len(artist_list)):
                        for artist in database[song]["artist"]:
                            try:
                                if artist["name"] == artist_list[i].strip():
                                    artist_list[i] = artist["id"]
                                    if i == len(artist_list) - 1:
                                        found_artist = True
                            except:
                                print('failed for: ', artist)
                                pass

        # writing changes to file              
        with open('history.csv', 'w') as fd:
            writer = csv.writer(fd, lineterminator="\n")
            for line in history:
                writer.writerow(line)
            
    
    def update_artists_with_similar_known_names(self):
        with open('song_database.json', 'r') as fd:
            database = json.load(fd) 
        
        for song_id in database:
            artist = database[song_id]["artist"]
            if type(artist[0]) == str:

                for search_id in database:
                    search_artist = database[search_id]["artist"]
                    if len(search_artist) == 1 and type(search_artist[0]) == dict:
                        # name wurde gefunden
                        if artist[0] == search_artist[0]["name"]:
                            print(artist[0], search_artist[0]["name"], song_id, search_id)
                            database[song_id]["artist"] = search_artist
                            break
                        # artist id wurde gefunden
                        elif artist[0] == search_artist[0]["id"]:
                            print(artist[0], search_artist[0]["name"], song_id, search_id)
                            database[song_id]["artist"] = search_artist
                            break

        with open('song_database.json', 'w') as fd:
            json.dump(database, fd) 
                        
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
        print('[ REQUEST ] multiple artists features', ids)

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
        
class FetchSongs:
    """ class SQLite Database support. Someday a parentclass for both should be useful """

    def __init__(self):
        self.user_id = spotify_user_id
        self.response_json = None

        Refresh = TokenRefresh()    
        self.spotify_token = Refresh.refresh_spotify_token()  # update the API access token for the Spotify API (is only valid for an hour each time)
        
        self.db = Database("develop.db")


    def recent_songs_to_database(self, song_number=50):
        print("add recently played songs to database...")
        query = f'https://api.spotify.com/v1/me/player/recently-played?limit={song_number}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        ).json()

        for song in response['items']:
            ### parse Data from JSON ###
            # stream info
            played_at = song['played_at']
            
            # song info
            song_id      = song['track']['id']
            song_name    = song['track']['name']
            duration_ms  = song['track']['duration_ms']
            popularity   = song['track']['popularity']
            track_number = song['track']['track_number']
            is_explicit  = int(song['track']['explicit']) # bool as int because sqlite doesnt support bools
            
            # album info
            album_name   = song['track']['album']['name']
            album_id     = song['track']['album']['id']
            album_img    = song['track']['album']['images'][0]["url"]
            album_type   = song['track']['album']['album_type']
            total_tracks = song['track']['album']['total_tracks']
            album_release_date = song['track']['album']['release_date']
           
           # artist info
            song_artists    = song['track']['artists']  # LIST of all artists that made this song
            album_artist_id = song['track']['album']['artists'][0]['id']  # PRIMARY artist who made this album
            
            ### insert data in databse ###
            # enter stream infos
            self.db.insert_row(
                table = "Stream",
                row = {
                    "timeStamp" : played_at,
                    "songID" : song_id
                }
            )
            
            # enter song infos
            self.db.insert_row(
                table = "Song",
                row = {
                    "ID" : song_id,
                    "title" : song_name,
                    "duration" : duration_ms,
                    "popularity" : popularity,
                    "explicit" : is_explicit,
                    "trackNumber" : track_number
                }
            )
            
            # enter album infos
            self.db.insert_row(
                table = "Album",
                row = {
                    "ID" : album_id,
                    "artistID" : album_artist_id,
                    "name" : album_name,
                    "releaseDate" : album_release_date,
                    "totalTracks" : total_tracks,
                    "type" : album_type,
                    "img" : album_img
                }
            )
            
            # enter artist infos
            for artist in song_artists:
                # artist info
                self.db.insert_row(
                    table = "Artist",
                    row = {
                        "ID" : artist["id"],
                        "name" : artist["name"]
                    }
                )
                # song written by assotiation
                self.db.insert_row(
                    table = "writtenBy",
                    row = {
                        "songID" : song_id,
                        "artistID" : artist["id"]
                    }
                )

    def add_album_info(self, song_number=50):
        print("add album info...")
        
        # get songs with trackNumber is NULL. These songs dont have an album associated with them
        rows = self.db.get_all(
            f"""select * from Song where trackNumber IS NULL or albumID IS NULL limit {song_number}"""
        )
        
        if rows == []:
            return
            
        # spotify API request for multiple tracks
        song_ids = ','.join([song["ID"] for song in rows]) # string of song IDS
        
        query = f'https://api.spotify.com/v1/tracks?ids={song_ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        ).json()
        
        # enter album data
        for song in response["tracks"]: 
            track_number = song['track_number']
            song_id      = song['id']
            
            # parse album info
            album_name   = song['album']['name']
            album_id     = song['album']['id']
            album_img    = song['album']['images'][0]["url"]
            album_type   = song['album']['album_type']
            total_tracks = song['album']['total_tracks']
            album_artist_id = song['album']['artists'][0]['id']  # PRIMARY artist who made this album
            album_release_date = song['album']['release_date']
            
            # enter album infos in database
            self.db.insert_row(
                table = "Album",
                row = {
                    "ID" : album_id,
                    "artistID" : album_artist_id,
                    "name" : album_name,
                    "releaseDate" : album_release_date,
                    "totalTracks" : total_tracks,
                    "type" : album_type,
                    "img" : album_img
                }
            )
            
            # enter track number and album of song to database
            self.db.update_cell(
                table = "Song",
                column = "trackNumber",
                primary_keys = { "ID" : song_id },
                new_value = track_number
            )
            self.db.update_cell(
                table = "Song",
                column = "albumID",
                primary_keys = { "ID" : song_id },
                new_value = album_id
            )

    def add_artist_info(self, artist_number=50):
        print('add artist info...')
        # get ids
        rows = self.db.get_all(
            f"""select * from Artist where popularity is null limit {artist_number}"""
        )
        
        if rows == []:
            return
        
        # Spotify API call
        artist_ids = ','.join([artist["ID"] for artist in rows]) # string of artist IDS
        query = f'https://api.spotify.com/v1/artists?ids={artist_ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        ).json()
        
        
        for artist in response["artists"]:
            # parse artist info
            artist_id: str  = artist["id"]
            genres: list    = artist["genres"]
            images: list    = artist["images"]
            popularity: int = artist["popularity"]
            
            # enter data in database
            self.db.update_cell(
                table = "Artist",
                column = "popularity",
                primary_keys = { "ID": artist_id },
                new_value = popularity
            )                
            self.db.update_cell(
                table = "Artist",
                column = "imgBig",
                primary_keys = { "ID": artist_id },
                new_value = images[0]["url"]
            )
            self.db.update_cell(
                table = "Artist",
                column = "imgSmall",
                primary_keys = { "ID": artist_id },
                new_value = images[-1]["url"]
            )
            
            for genre in genres:
                self.db.insert_row(
                    table = "Genre",
                    row = {
                        "artistID" : artist_id,
                        "genre": genre
                    }
                )
            
    def add_audio_features(self, song_number=50):
        print("add audio features...")
        # get songs with key is NULL. These songs propably don't have the other audio features as well
        rows = self.db.get_all(
            f"""select * from Song where key IS NULL limit {song_number}"""
        )
        
        if rows == []:
            return
        
        # Spotify API Call
        song_ids = ','.join([song["ID"] for song in rows]) # string of song IDS
        query = f'https://api.spotify.com/v1/audio-features?ids={song_ids}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" : "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        ).json()
        
        for song in response["audio_features"]: 
            if "id" not in song:
                continue
            
            # parse audio features
            song_id        = song["id"]
            key            = song["key"]
            time_signature = song["time_signature"]
            mode           = song["mode"]
            loudness       = song["loudness"]
            tempo          = song["tempo"]
            energy         = song["energy"]
            
            # insert data in table
            self.db.update_cell(
                table = "Song",
                column = "key",
                primary_keys = { "ID" : song_id },
                new_value = key
            )
            self.db.update_cell(
                table = "Song",
                column = "timeSignature",
                primary_keys = { "ID" : song_id },
                new_value = time_signature
            )
            self.db.update_cell(
                table = "Song",
                column = "mode",
                primary_keys = { "ID" : song_id },
                new_value = mode
            )
            self.db.update_cell(
                table = "Song",
                column = "loudness",
                primary_keys = { "ID" : song_id },
                new_value = loudness
            )
            self.db.update_cell(
                table = "Song",
                column = "tempo",
                primary_keys = { "ID" : song_id },
                new_value = tempo
            )
            
            self.db.update_cell(
                table = "Song",
                column = "energy",
                primary_keys = { "ID" : song_id },
                new_value = energy
            )
            
    def add_lyrics(self, song_number=30):       
        print("add lyrics info...")
        
        # get songs with trackNumber is NULL. These songs dont have an album associated with them
        rows = self.db.get_all(
            f"""
            select Song.ID, Song.title, Artist.name, Song.lyrics
            from Song
            join writtenBy on Song.ID = writtenBy.songID
            join Artist on writtenBy.artistID = Artist.ID 
            where Song.lyrics is null
            limit {song_number}
            """
        )
        
        if rows == []:
            return
        
        used_ids = []
        for song in rows:
            # the sql query lists song multible times of each assiociated artist.
            # This is hard to prevent in sql thus the used ids list
            if song["ID"] in used_ids:
                continue
            lyrics = retrieve_lyrics(
                artistname=song["name"], 
                songname=song["title"] 
            )
            
            if lyrics is not None:
                self.db.update_cell(
                    table = "Song",
                    column = "lyrics",
                    primary_keys = { "ID" : song["ID"] },
                    new_value = lyrics
                )
            
            used_ids.append(song["ID"])
            
        
        

  
if __name__ == "__main__":
    songs = FetchSongs()
    songs.recent_songs_to_database()
    songs.add_album_info()
    songs.add_artist_info()
    songs.add_audio_features()
    songs.add_lyrics()

    

