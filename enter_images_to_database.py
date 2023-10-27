from database import Database
import os

db: Database = Database('darian.db')

local_path = '/media/pi/DATADRIVE/Spotify/images/'
url_start  = 'https://i.scdn.co/image/'

local_albums:  list = os.listdir( os.path.join(local_path, 'albums' ) ) 
local_artists: list = os.listdir( os.path.join(local_path, 'artists') ) 

db_albums_big    = list( map( lambda a: a['imgBig'][24:],   db.get_all('select imgBig from Album where imgBigLocal is null ') ) )
db_albums_small  = list( map( lambda a: a['imgSmall'][24:], db.get_all('select imgSmall from Album where imgSmallLocal is null') ) )
db_artists_big   = list( map( lambda a: a['imgBig'][24:],   db.get_all('select imgBig from Artist where imgBig is not null and imgBigLocal is null') ) )
db_artists_small = list( map( lambda a: a['imgSmall'][24:], db.get_all('select imgSmall from Artist where imgSmall is not null and imgSmallLocal is null') ) )

#insert data

print('Album Cover')
for i, file in enumerate(local_albums):
    file = file[:-4]
    if i % 100 == 0:
        print(f'\r{i/len(local_albums)*100:.2f}%', end='')

    if file in db_albums_big:
        size = 'imgBig'
    elif file in db_albums_small:
        size = 'imgSmall'
    else:
        continue
    db.update_cell(
         table='Album',
         column= size + 'Local',
         primary_keys={ size: url_start + file },
         new_value='images/albums/' + file + '.jpg' 
     )

print('\r100.00%')

print('Artist Picture')
for i, file in enumerate(local_artists):
    file = file[:-4]
    if i % 100 == 0:
        print(f'\r{i/len(local_artists)*100:.2f}%', end='')

    if file in db_artists_big:
        size = 'imgBig'
    elif file in db_artists_small:
        size = 'imgSmall'
    else:
        continue
    db.update_cell(
         table='Artist',
         column= size + 'Local',
         primary_keys={ size: url_start + file },
         new_value='images/artists/' + file + '.jpg' 
     )

print('\r100.00%')






