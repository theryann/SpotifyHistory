import requests
import time
import json

from scrape_lyrics import retrieve_lyrics

from credentials import tokens
from refresh import TokenRefresh

from database import Database



class FetchSongs:
    """
    class to support all the insertion and updates into the database.
    @param: user ...string that represents the name of the person as named in the credentials keys and database names
    """

    def __init__(self, user: str):
        Refresher = TokenRefresh(user)
        self.spotify_token = Refresher.refresh_spotify_token()  # update the API access token for the Spotify API (is only valid for an hour each time)

        self.db = Database(f"{user}.db")

    def recent_songs_to_database(self, song_number=50):
        print(f"\nadd recently played songs to database... 100%", end="")


        query = f'https://api.spotify.com/v1/me/player/recently-played?limit={song_number}'

        response = requests.get(
            query,
            headers = {
                "Content-Type" :  "application/json",
                "Authorization": f"Bearer {self.spotify_token}"
            }
        ).json()

        for i, song in enumerate(response['items']):
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
            print(f"\radd recently played songs to database... {int(i/len(response['items'])*100) if i < len(response['items'])-2 else 100}%", end="")

    def add_album_info(self, song_number=50):
        print(f"\nadd album info... 100%", end="")
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
                "Authorization": f"Bearer {self.spotify_token}"
            }
        ).json()

        # enter album data
        for i, song in enumerate(response["tracks"]):
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

            print(f"\radd album info... {int(i/len(response['tracks'])*100) if i < len(response['tracks'])-2 else 100}%", end="")

    def add_artist_info(self, artist_number=50):
        print(f"\nadd artist info... 100%", end="")


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
                "Authorization": f"Bearer {self.spotify_token}"
            }
        ).json()


        for i, artist in enumerate(response["artists"]):
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
            print(f"\radd artist info... {int(i/len(response['artists'])*100) if i < len(response['artists'])-2 else 100}%", end="")

    def add_audio_features(self, song_number=50):
        print(f"\nadd audio features... 100%", end="")


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
                "Authorization": f"Bearer {self.spotify_token}"
            }
        ).json()

        for i, song in enumerate(response["audio_features"]):
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
            print(f"\radd audio features... {int(i/len(response['audio_features'])*100) if i < len(response['audio_features'])-2 else 100}%", end="")

    def add_lyrics(self, song_number=30):
        print(f"\nadd lyrics info... 100%", end="")


        # get songs with trackNumber is NULL. These songs dont have an album associated with them
        rows = self.db.get_all(
            f"""
            select Song.ID, Song.title, Artist.name, Song.lyrics
            from Song
            join writtenBy on Song.ID = writtenBy.songID
            join Artist on writtenBy.artistID = Artist.ID
            where Song.lyrics is null or Song.lyrics = ''
            limit {song_number}
            """
        )

        if rows == []:
            return

        used_ids = []
        for i, song in enumerate(rows):
            # the sql query lists songs multiple times for each assiociated artist (artist name needed for api call).
            # This is hard to prevent in sql thus the used ids list
            if song["ID"] in used_ids:
                continue
            lyrics = retrieve_lyrics(
                artistname=song["name"],
                songname=song["title"],
                verbose=False
            )

            new_lyrics_info: str # value to send to database. either the lyrics or %not available%.
                                 # This prevents from always requesting the same 'broken' songs and never moving on

            if lyrics is not None:
                new_lyrics_info = lyrics
            else:
                new_lyrics_info = '%not available%'

            self.db.update_cell(
                table = "Song",
                column = "lyrics",
                primary_keys = { "ID" : song["ID"] },
                new_value = new_lyrics_info
            )

            used_ids.append(song["ID"])
            print(f"\radd lyrics info... {int(i/len(rows)*100) if i < len(rows)-2 else 100}%", end="")

            time.sleep(1)


class Analyzer:
    def __init__(self, user: str) -> None:
        self.db: Database = Database(f"{user}.db")
        self.user: str = user

    def rank_album_playthroughs(self) -> None:
        query: str = """
        SELECT
            timeStamp,
            Song.albumID, Song.trackNumber,
            Album.totalTracks, Album.name, Album.imgSmall
        FROM Stream
        JOIN Song ON Song.ID = Stream.songID
        JOIN Album ON Album.ID = Song.albumID
        WHERE Album.type != 'single'
        ORDER BY timeStamp
        LIMIT 100
        OFFSET {}
        """
        album_playthroughs: dict = {}

        offset: int = 0
        curr_album: dict = {}

        while True:
            rows: dict = self.db.get_all( query.format(offset) )

            if rows == []:
                try:
                    with open('analytics.json', 'r') as fd:
                        data = json.load(fd)
                        if self.user not in data:
                            data[self.user] = {}
                        data[self.user]['albumPlaythrough'] = album_playthroughs

                    with open('analytics.json', 'w') as fd:
                        json.dump(data, fd)

                except FileNotFoundError:
                    with open('analytics.json', 'w') as fd:
                        data = {}
                        data[self.user] = {}
                        data[self.user]['albumPlaythrough'] = album_playthroughs
                        json.dump(data, fd)

                break

            for i, stream in enumerate(rows):
                if i == 0:
                    if offset == 0:
                        curr_album = stream
                        continue

                if stream['albumID'] != curr_album['albumID']:
                    if stream['trackNumber'] == 1:
                        curr_album = stream
                    continue

                if stream['trackNumber'] != curr_album['trackNumber'] + 1:
                    if stream['trackNumber'] == 1:
                        curr_album = stream
                    continue

                else:
                    if stream['trackNumber'] == stream['totalTracks']:
                        if stream['albumID'] in album_playthroughs:
                            album_playthroughs[ stream['albumID'] ] += 1
                        else:
                            album_playthroughs[ stream['albumID'] ]  = 1
                    else:
                        curr_album = stream

            offset += 100



if __name__ == "__main__":
    # for user in tokens:
    #     songs = FetchSongs(user)
    #     songs.recent_songs_to_database()
    #     songs.add_album_info()
    #     songs.add_artist_info()
    #     songs.add_audio_features()
    #     songs.add_lyrics()

    for user in tokens:
        analyzer = Analyzer(user)
        analyzer.rank_album_playthroughs()




