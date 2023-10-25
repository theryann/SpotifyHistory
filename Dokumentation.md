# Spotify History

Das ist der Download Part des Projekts.

## Requirements
- Python (mindestens Version 3.9)
- eigenes SQLite Datenbank Modul [database](https://github.com/theryann/database) in Version 1.0
- ein Datenbank-File mit dem namen darian.db

## zu beachten
- die Datenbank ist durchdacht und sollte nicht verändert werden.
- am wichtigsten ist dass Stream funktioniert. Es ist möglich den Rest durch die API wieder zu rekreieren. Allerdings dauert das sehr lange.
- Album und Artistcover sind extern gespiechert und nur relativ als Pfad gespeichert. Wo das ist, muss in einer .env Datei hinter SPOTIFY_IMAGE_PATH= stehen.
