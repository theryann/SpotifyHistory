import requests
import json
import time
from bs4 import BeautifulSoup

def retrieve_lyrics(artistname, songname):
    resp = requests.get(f'https://genius.com/{artistname}-{songname}-lyrics')
    
    if resp.status_code != 200:
        print(resp.status_code, resp)
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
        for song in song_db:
            # abort if lyrics are known
            if 'lyrics' in song_db[song]:
                continue          

            # retrieve lyrics
            artist_name = song_db[song]["artist"][0]["name"].replace(' ','-')
            song_name   = song_db[song]["titel"].replace(' ', '-') 
            
            print(artist_name, song_name)
            res = retrieve_lyrics(artist_name, song_name)
            
            # case not a string response
            if not isinstance(res, str):
                continue
            
            # enter in database
            song_db[song]["lyrics"] = res
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        pass
        
    with open('song_database.json', 'w') as fd:
        json.dump(song_db, fd)
    
        
    
    