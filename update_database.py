from recently import RecentSongs


songs = RecentSongs()
songs.update_song_database_with_history_data()
songs.update_artists_with_similar_known_names()
songs.update_song_database_with_audio_features()
songs.update_song_database_with_artists()
songs.update_history_with_similar_artist_name()