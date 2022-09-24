from bs4 import BeautifulSoup
import requests
import json
import time

def retrieve_lyrics(artistname, songname):
    # prepare text for url
    feat_index = songname.find('feat.') # removes (feat. xyz) from title
    if  feat_index > 0:
        songname = songname[:feat_index-1].strip()
    
    switch = [
        [' - ', '-'],
        [' ', '-'],
        ['\'', ''],
        ['/' , '-'],
        ['.',  ''],
        ['(',  ''],
        [')',  ''],
        [',',  ''],
        ['?',  ''],
        ['!',  ''],
        ['ü', 'u'],
        ['ä', 'a'],
        ['ö', 'o']
    ]
    
    for i in range(len(switch)):        # removes ceratin characters
        artistname = artistname.lower().replace(switch[i][0], switch[i][1])
        songname   = songname.lower().replace(switch[i][0], switch[i][1])    
        
    
    # make request
    resp = requests.get(f'https://genius.com/{artistname}-{songname}-lyrics')
    
    if resp.status_code != 200:
        if resp.status_code == 404:
            print(f'\t404: {artistname}-{songname}-lyrics')
        else:
            print('\t->', resp.status_code, resp)
        return
        
    soup_html = BeautifulSoup(resp.text, 'html.parser')
    lyrics = soup_html.find("div", class_="Lyrics__Container-sc-1ynbvzw-6 YYrds")
    
    if lyrics:
        lines_list = lyrics.get_text(separator="\n").splitlines()
        for i in range(len(lines_list)-1, -1, -1):
            if '[' in lines_list[i].lower():
                lines_list.pop(i)

        return '\n'.join(lines_list)
                
                
                
if __name__ == "__main__":
    with open('song_database.json', 'r') as fd:
        song_db = json.load(fd)
    
    
    try:    
        for i, song in enumerate(song_db):
            # abort if lyrics are known
            if 'lyrics' in song_db[song]:
                continue          

            # retrieve lyrics
            artist_name = song_db[song]["artist"][0]["name"]
            song_name   = song_db[song]["titel"]
            
            print(i, artist_name, song_name)
            res = retrieve_lyrics(artist_name, song_name)
            
            # case not a string response
            if not isinstance(res, str):
                continue
            
            # enter in database
            song_db[song]["lyrics"] = res
            
            if i % 20 == 0:
                time.sleep(10)
            else:            
                time.sleep(1)
            
    except:
        pass
        
    with open('song_database.json', 'w') as fd:
        json.dump(song_db, fd)
    
        
    
    
