import requests
import time
import json
import uuid
import sys

from datetime import datetime, timedelta

from credentials import tokens
from refresh import TokenRefresh

from scrape_lyrics import retrieve_lyrics
from database import Database



class FetchSongs:
    """
    class to support all the insertion and updates into the database.
    @param user: string that represents the name of the person as named in the credentials keys and database names
    @param offline: set online to false for maintanance work on the code or database
                    that doesn't require fetching of data or generation of tokens
    @param debug: in debug all responses are saved to json files
    """

    def __init__(self, user: str, offline: bool = False, debug: bool = False):
        self.debug: bool = debug
        self.offline: bool = offline

        if not self.offline:
            Refresher = TokenRefresh(user)
            self.spotify_token = Refresher.refresh_spotify_token()  # update the API access token for the Spotify API (is only valid for an hour each time)
            self.authentication_headers = {
                "Content-Type" :  "application/json",
                "Authorization": f"Bearer {self.spotify_token}"
            }

        self.db = Database(f"{user}.db")

    def recent_songs_to_database(self, song_number=50):
        print(f"\nadd recently played songs to database... 100%", end="")


        query = f'https://api.spotify.com/v1/me/player/recently-played?limit={song_number}'

        response = requests.get( query, headers=self.authentication_headers ).json()

        if self.debug:
            with open('debug_recently-played.json', 'w', encoding='utf-8') as fd:
                json.dump(response, fd, indent=4)

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
            song_artists: list   = song['track']['artists']  # LIST of all artists that made this song
            album_artist_id: str = song['track']['album']['artists'][0]['id']  # PRIMARY artist who made this album

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

    def dsgvo_data_to_database(self, path:str):
        """
        official requested data from spotify sort into database
        @param path: path where the json files are located
        """

        # make sure alle columns exist
        exisiting_columns: list = self.db.get_all('PRAGMA table_info(Stream);')

        def col_exists(name: str):
            return any( map(lambda col: col['name'] == name, exisiting_columns) )

        if not col_exists('msPlayed'):
            self.db.get_all('ALTER TABLE Stream ADD msPlayed INTEGER')

        if not col_exists('connCountry'):
            self.db.get_all('ALTER TABLE Stream ADD connCountry TEXT')

        if not col_exists('device'):
            self.db.get_all('ALTER TABLE Stream ADD device TEXT')

        if not col_exists('online'):
            self.db.get_all('ALTER TABLE Stream ADD online INTEGER')

        # insert data
        import os

        files: list = [
            os.path.join(path, file)
            for file in os.listdir(path)
                if os.path.splitext(file)[1] == '.json'
                and
                not 'Video' in file
        ]
        estimated_items: int = None
        items_in_one_file: int = None

        # for every json file
        print(f"\nadd dsgvo info... 100%", end="")

        for i, file in enumerate(files):
            with open(file, 'r', encoding='utf-8') as fd:
                data = json.load(fd)

            if i == 0:
                items_in_one_file = len(data)
                estimated_items = items_in_one_file * len(files)

            # for every track
            for j, track in enumerate(data):

                if track['spotify_track_uri'] is None:
                    continue
                if track['ms_played'] < 20_000:
                    continue

                played_at    = track['ts']
                device       = track['platform']
                ms_played    = track['ms_played']
                conn_country = track['conn_country']
                online       = 1 - int(track['offline'])
                song_id      = track['spotify_track_uri'].split(':')[2]
                song_title   = track['master_metadata_track_name']

                # enter stream infos

                # insert to Stream Table
                self.db.insert_row(
                    table = "Stream",
                    row = {
                        "timeStamp" : played_at,
                        "songID" : song_id,
                        "device": device,
                        "msPlayed": ms_played,
                        "connCountry": conn_country,
                        "online": online
                    }
                )

                self.db.update_cell(
                    table = "Stream",
                    column = "device",
                    primary_keys = {"timeStamp": played_at, "songID": song_id},
                    new_value = device
                )

                self.db.update_cell(
                    table = "Stream",
                    column = "connCountry",
                    primary_keys = {"timeStamp": played_at, "songID": song_id},
                    new_value = conn_country
                )

                self.db.update_cell(
                    table = "Stream",
                    column = "msPlayed",
                    primary_keys = {"timeStamp": played_at, "songID": song_id},
                    new_value = ms_played
                )

                self.db.update_cell(
                    table = "Stream",
                    column = "online",
                    primary_keys = {"timeStamp": played_at, "songID": song_id},
                    new_value = online
                )

                # insert to Song Table
                self.db.insert_row(
                    table = "Song",
                    row = {
                        "ID" : song_id,
                        "title" : song_title
                    }
                )


                if j % 100 == 0:
                    print(f"\radd dsgvo info... {( ((i*items_in_one_file)+j) / estimated_items*100):.2f}%", end="")

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

        response = requests.get( query, headers=self.authentication_headers ).json()

        if self.debug:
            with open('debug_tracks.json', 'w', encoding='utf-8') as fd:
                json.dump(response, fd, indent=4)

        # enter album data
        for i, song in enumerate(response["tracks"]):
            song_id      = song['id']

            # skip empty response data. Other indicators are relesedate of "0000", name: ""
            if len( song['album']['images'] ) == 0:
                continue

            # parse song info for dsgvo data that dont get this from elsewhere
            song_duration = song['duration_ms']
            track_number  = song['track_number']
            explicit      = song['explicit']
            popularity    = song['popularity']

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
            self.db.update_cell(
                table = "Song",
                column = "duration",
                primary_keys = { "ID" : song_id },
                new_value = song_duration
            )
            self.db.update_cell(
                table = "Song",
                column = "explicit",
                primary_keys = { "ID" : song_id },
                new_value = explicit
            )
            self.db.update_cell(
                table = "Song",
                column = "popularity",
                primary_keys = { "ID" : song_id },
                new_value = popularity
            )

            print(f"\radd album info... {int(i/len(response['tracks'])*100) if i < len(response['tracks'])-2 else 100}%", end="")

    def add_artist_info(self, artist_number=50):
        print(f"\nadd artist info... 100%", end="")

        # prepare date of last update to be inserted
        # Artist info can change over time. This should keep everything up to date
        self.db.ensure_column(
            table_name  = 'Artist',
            column_name = 'lastUpdated',
            data_type   = 'TEXT'
        )

        current_timedelta: str = datetime.now().strftime('%Y-%m-%d')
        oldest_timestamp:  str = ( datetime.now() - timedelta(100) ).strftime('%F') # 100 days is the oldest that artist information shall be

        # get ids
        rows = self.db.get_all(
            f"""
            select *
            from Artist
            where imgBig is null
                  or
                  lastUpdated < '{oldest_timestamp}'
                  or
                  lastUpdated is null
            limit {artist_number}"""
        )

        if rows == []:
            return

        # Spotify API call
        artist_ids = ','.join([artist["ID"] for artist in rows]) # string of artist IDS
        query = f'https://api.spotify.com/v1/artists?ids={artist_ids}'

        response = requests.get( query, headers=self.authentication_headers ).json()

        if self.debug:
            with open('debug_artists.json', 'w', encoding='utf-8') as fd:
                json.dump(response, fd, indent=4)


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

            self.db.update_cell(
                table = 'Artist',
                column ='lastUpdated',
                primary_keys = { "ID": artist_id },
                new_value = current_timedelta
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

        res: requests.Response = requests.get( query, headers=self.authentication_headers )

        if res.status_code != 200:
            if res.status_code == 403:
                print('[CAUTION] fetching aufio feature data is deprecated and Spotify forbids it')
                return

            print('[CAUTION] fetching audio features resulted in status code', res.status_code)
            print(res.text)

            if self.debug:
                with open('debug_audio-features.json', 'w', encoding='utf-8') as fd:
                    json.dump(res, fd, indent=4)
            print() # add newline since this doesn't finnish naturally
            return

        response: dict = res.json()

        for i, song in enumerate(response["audio_features"]):

            if song is None:
                continue

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
            print(f"\radd audio features... {int(i/len(response['audio_features'])*100) if i < len(response['audio_features'])-2 else 100}\t\t%", end="")

    def add_audio_analysis(self, song_number=20):
        print(f"\nadd audio grid features ... 0%\t", end="")

        # get songs that don't appear in the Sections table
        # those songs won't appear in the other audio tables as well
        # Sections is just the shortest
        rows = self.db.get_all(
            f"""
            SELECT ID as songID
            FROM Song
            WHERE Song.ID NOT IN (
                SELECT DISTINCT songID
                FROM Sections
            )
            LIMIT {song_number}"""
        )

        if rows == []:
            return

        song_ids: list[str] = [ row['songID'] for row in rows ]


        for i, song_id in enumerate( song_ids ):
            bars:  list[dict] = []
            beats: list[dict] = []
            sections: list[dict] = []
            segments: list[dict] = []

            # Spotify API Call
            query = f"https://api.spotify.com/v1/audio-analysis/{song_id}"

            response: requests.Response = requests.get( query, headers=self.authentication_headers )

            # handle bad response
            if response.status_code != 200:
                if response.status_code == 504:
                    # happens a lot.
                    # Spotify can't deliver the detailed analysis on time
                    # so the timeout expires. Just retry later
                    continue

                if response.status_code == 403:
                    print('[CAUTION] fetching audio analysis data is deprecated and Spotify forbids it')
                    return

                print('[CAUTION] fetching audio analysis data resulted in status code', response.status_code)
                print('songID:', song_id)
                print(response.text)

                if self.debug:
                    with open(f'debug_audio-analysis_{song_id}.json', 'w', encoding='utf-8') as fd:
                        json.dump(response.text, fd, indent=4)
                continue

            data: dict = response.json()

            # collect bars
            for bar in data['bars']:
                bars.append({
                    'songID':   song_id,
                    'start':    bar['start'],
                    'durationSec':  bar['duration'],
                })

            # collect beats
            for beat in data['beats']:
                beats.append({
                    'songID':   song_id,
                    'start':    beat['start'],
                    'durationSec':  beat['duration'],
                })

            # collect sections
            for section in data['sections']:
                sections.append({
                    'songID':   song_id,
                    'start':    section['start'],
                    'durationSec':   section['duration'],
                    'loudness':      section['loudness'],
                    'tempo':         section['tempo'],
                    'key':           section['key'],
                    'mode':          section['mode'],
                    'timeSignature': section['time_signature'],
                })

            # collect segments
            for segment in data['segments']:
                segments.append({
                    'songID':       song_id,
                    'start':        segment['start'],
                    'durationSec':  segment['duration'],
                    'loudnessStartSec':     segment['loudness_start'],
                    'loudnessMax':          segment['loudness_max'],
                    'loudnessMaxTimeSec':   segment['loudness_max_time'],
                    'loudnessEnd':          segment['loudness_end'],
                })

            # inserting data
            self.db.insert_many('Bars', bars)
            self.db.insert_many('Beats', beats)
            self.db.insert_many('Segments', segments)
            self.db.insert_many('Sections', sections)

            print(f"\radd audio grid features ... {round((i+1)/len(song_ids)*100) if i < len(song_ids)-1 else 100 }%\t", end="")

    def add_lyrics(self, song_number=30):
        print(f"\nadd lyrics info... 0%", end="")

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

            if lyrics:
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
            print(f"\radd lyrics info... " + str(int(i/len(rows)*100)) if i < len(rows)-2 else '100\n' + "%\t\t\t", end="")

            time.sleep(.2)
        print() # add newline cause that sometimes doesn't happen naturally

    def add_songs_to_writtenby_table(self, song_number=50):
        print(f"\nadd songs and artists to writtenBy table... 100%", end="")

        rows = self.db.get_all(
            f"""
            select Song.ID
            from Song
            where Song.ID NOT IN (select songID from writtenBy)
            limit {song_number}"""
        )

        if rows == []:
            return

        # spotify API request for multiple tracks
        song_ids: str = ','.join([song["ID"] for song in rows]) # string of song IDS

        query = f'https://api.spotify.com/v1/tracks?ids={song_ids}'

        res: requests.Response = requests.get( query, headers=self.authentication_headers )

        if res.status_code != 200:
            print('[CAUTION] fetching track data for writtenby table resulted in staus code:', res.status_code)
            print(res)
            return

        response: dict = res.json()

        if self.debug:
            with open('debug_tracks_not_in_writtenby_table.json', 'w', encoding='utf-8') as fd:
                json.dump(response, fd, indent=4)

        for i, song in enumerate(response['tracks']):
            song_id = song['id']
            song_artists: list[dict]   = song['artists']  # LIST of all artists that made this song

            ### insert data in databse ###

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
            print(f"\radd songs and artists to writtenBy table... {int(i/len(response['tracks'])*100) if i < len(response['tracks'])-2 else 100}%", end="")

    def save_images_locally(self, album_number=30, artist_number=30):
        print(f"\ndownload cover... 100%", end="")
        i = 0

        # GET LOCAL SAVE PATH
        local_path = self.read_env('SPOTIFY_IMAGE_PATH', '')

        def write_img_file(img_content, img_link, col_name):
            """
            function to actually save the img file (as opposed to writing its path to the database)
            @param img_content: is image a cover or an artist picture. this will decide the directory it is saved to
            @param img_link: link to image file
            @param col_name: how is the column named where the link is stored in
            """
            response = requests.get(img_link)

            if not response.ok:
                return

            img_data = response.content

            try:
                with open(f'{local_path}images/{img_content}/{ img_link.split("/")[-1] }.jpg', 'wb') as handler:  # this takes actual full path
                    handler.write(img_data)
            except:
                print('failed to save image to disc')


        # save ALBUM Cover
        album_rows = self.db.get_all(
            f"""
            SELECT ID, imgSmall, imgBig
            FROM Album
            WHERE
                (imgSmallLocal is NULL or imgBigLocal is NULL)
                and
                imgBig != '' and imgSmall != ''
            LIMIT {album_number}
            """
        )

        for album in album_rows:
            # Small Images
            write_img_file('albums', album['imgSmall'], 'imgSmall')
            self.db.update_cell(
                table = 'Album',
                column = 'imgSmallLocal',
                primary_keys = {'ID' : album['ID'] },
                new_value = f'images/albums/{ album["imgSmall"].split("/")[-1] }.jpg' # all database info contains only the only 'local' path.
            )                                                                         # starting with 'images/...'

            # Big Images
            write_img_file('albums', album['imgBig'], 'imgBig')
            self.db.update_cell(
                table = 'Album',
                column = 'imgBigLocal',
                primary_keys = {'ID' : album['ID'] },
                new_value = f'images/albums/{ album["imgBig"].split("/")[-1] }.jpg'
            )
            print(f"\rdownload cover... {int(i/len(album_rows)*100) if i < len(album_rows)-2 else 100}%", end="")
            i += 1



        # save ARTIST Cover
        print(f"\rdownload artist pics... 100%", end="")
        i = 0
        artist_rows = self.db.get_all(
            f"""
            SELECT ID, imgSmall, imgBig
            FROM Artist
            WHERE
                (imgSmallLocal is NULL or imgBigLocal is NULL)
                and
                imgBig != '' and imgSmall != ''
            LIMIT {artist_number}
            """
        )

        for artist in artist_rows:
            # Small Images
            write_img_file('artists', artist['imgSmall'], 'imgSmall')
            self.db.update_cell(
                table = 'Artist',
                column = 'imgSmallLocal',
                primary_keys = {'ID' : artist['ID'] },
                new_value = f'images/artists/{ artist["imgSmall"].split("/")[-1] }.jpg'
            )

            # Big Images
            write_img_file('artists', artist['imgBig'], 'imgBig')
            self.db.update_cell(
                table = 'Artist',
                column = 'imgBigLocal',
                primary_keys = {'ID' : artist['ID'] },
                new_value = f'images/artists/{ artist["imgBig"].split("/")[-1] }.jpg'
            )
            print(f"\rdownload artist pics... {int(i/len(artist_rows)*100) if i < len(artist_rows)-2 else 100}%", end="")
            i += 1

    def assign_uuids(self) -> None:
        """
        assigns unique IDs (UUIDs) to Songs and Albums so different Versions can be counted as one Song/Album
        it is not checked wether a UUID exists already because they are uique for all intents and purposes
        """
        print(f"\nadd UUIDs...100%", end="")
        num_cells_updated: int = 0


        self.db.ensure_column(
            table_name  = 'Song',
            column_name = 'UUID',
            data_type = 'TEXT'
        )
        self.db.ensure_column(
            table_name  = 'Album',
            column_name = 'UUID',
            data_type = 'TEXT'
        )

        songs_without_uuid = self.db.get_all(f"""
            SELECT DISTINCT title, artistID
            FROM Song
            JOIN writtenBy ON writtenBy.songID = Song.ID
            WHERE Song.UUID IS NULL
            LIMIT 500
        """)

        albums_without_uuid = self.db.get_all(f"""
            SELECT DISTINCT name, artistID
            FROM Album
            WHERE Album.UUID IS NULL
            LIMIT 500
        """)

        ##################
        # UUIDS for Songs
        ##################
        for song in songs_without_uuid:
            unique_id: str = uuid.uuid4().hex

            song_title = self.db.stringify( song['title'] )

            self.db.update_cell(
                table  = 'Song',
                column = 'UUID',
                new_value = unique_id,
                where = f""" ID IN (
                    SELECT ID
                    FROM Song
                    JOIN writtenBy ON writtenBy.songID = Song.ID
                    WHERE
                        writtenBy.artistID = '{song['artistID']}'
                        AND
                        title = {song_title}
                )
                """
            )

            num_cells_updated += 1
            if num_cells_updated % 50 == 0:
                print(f"\radd UUIDs... {num_cells_updated/10}%", end="")


        ##################
        # UUIDS for Albums
        ##################
        for album in albums_without_uuid:
            unique_id: str = uuid.uuid4().hex

            album_name = self.db.stringify( album['name'] )

            self.db.update_cell(
                table  = 'Album',
                column = 'UUID',
                new_value = unique_id,
                where = f""" ID IN (
                    SELECT ID
                    FROM Album
                    WHERE
                        artistID = '{album['artistID']}'
                        AND
                        name = {album_name}
                )
                """
            )

            num_cells_updated += 1
            if num_cells_updated % 50 == 0:
                print(f"\radd UUIDs... {num_cells_updated/10}%", end="")

    def read_env(self, variable_name: str, default=None) -> str:
        env_variables: dict = {}

        with open('.env', 'r', encoding='utf-8') as fd:
            for line in fd.readlines():
                if line.strip() == '':
                    continue

                key, value = line.split('=')
                env_variables[ key.strip() ] = value.strip()

        if variable_name in env_variables:
            return env_variables[variable_name]
        else:
            return default



class Analyzer:
    def __init__(self, user: str) -> None:
        self.db: Database = Database(f"{user}.db")
        self.user: str = user

    def rank_album_playthroughs(self) -> None:
        print(f'\n[{self.user}] rank album playhroughs', end='')

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
        LIMIT 1000
        OFFSET {}
        """
        album_playthroughs: dict = {}

        offset: int = 0
        curr_album: dict = {}

        row_count: int = self.db.get_all("SELECT count(*) as 'rows' FROM Stream")[0]['rows']

        while True:
            del self.db
            self.db: Database = Database(f"{self.user}.db")

            rows: dict = self.db.get_all( query.format(offset) )

            if rows == []:
                self.db.ensure_column(
                    table_name  = 'Album',
                    column_name = 'fullPlaythroughs',
                    data_type   = 'INTEGER'
                )

                for album_id in album_playthroughs:
                    self.db.update_cell(
                        table  = 'Album',
                        column = 'fullPlaythroughs',
                        primary_keys = { 'ID': album_playthroughs[ album_id ][ 'albumID' ] },
                        new_value    = album_playthroughs[ album_id ][ 'playthroughs' ]
                    )

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
                            album_playthroughs[ stream['albumID'] ]['playthroughs'] += 1
                        else:
                            album_playthroughs[ stream['albumID'] ] = stream
                            album_playthroughs[ stream['albumID'] ]['playthroughs']  = 1
                    else:
                        curr_album = stream

            offset += 1000
            print(f'\r[{self.user}] rank album playhroughs {offset/row_count*100:.2f}%', end='')

        print("\n")




if __name__ == "__main__":
    flags: list = sys.argv[1:]
    debug:   bool = '-d' in flags or '--debug'   in flags
    analyze: bool = '-a' in flags or '--analyze' in flags
    offline: bool = '--offline' in flags

    for user in tokens:
        songs = FetchSongs(user=user, offline=offline, debug=debug)
        #songs.dsgvo_data_to_database('Streaming/')
        songs.recent_songs_to_database()
        songs.add_songs_to_writtenby_table()
        songs.add_album_info()

        for _ in range(10):
            songs.add_artist_info()

        # songs.add_audio_features()  # deprecated
        # songs.add_audio_analysis()  # deprecated
        #songs.save_images_locally()
        #songs.assign_uuids()
        songs.add_lyrics()

        if debug:
            break

    if analyze:
        for user in tokens:
            analyzer = Analyzer(user)
            analyzer.rank_album_playthroughs()




