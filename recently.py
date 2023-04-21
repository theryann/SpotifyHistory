import requests
import json
import csv
import re

from scrape_lyrics import retrieve_lyrics

from credentials import spotify_user_id
from refresh import TokenRefresh
from database import Database


class FetchSongs:
    """ class to support all the insertion and updates into the database """

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
                "Content-Type" :  "application/json",
                "Authorization": f"Bearer {self.spotify_token}"
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
            album_name     = song['track']['album']['name']
            album_id       = song['track']['album']['id']
            album_imgBig   = song['track']['album']['images'][0]["url"]
            album_imgSmall = song['track']['album']['images'][-1]["url"]
            album_type     = song['track']['album']['album_type']
            total_tracks   = song['track']['album']['total_tracks']
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
                    "imgBig" : album_imgBig,
                    "imgSmall" : album_imgSmall
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
            f"""
            select *
            from Song
            where
                trackNumber IS NULL
                or
                albumID IS NULL
            limit {song_number}"""
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
            album_imgBig = song['album']['images'][0]["url"]
            album_imgSmall = song['album']['images'][-1]["url"]
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
                    "imgBig" : album_imgBig,
                    "imgSmall" : album_imgSmall,
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
            f"""select * from Artist where imgBig is null limit {artist_number}"""
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
            if len(images) > 0:
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
    # songs.add_lyrics()



