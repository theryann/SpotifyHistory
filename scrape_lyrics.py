from bs4 import BeautifulSoup, NavigableString
import requests
import re

chrome_header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

pattern_timestamp = re.compile("\d{2}:\d{2}-\d{2}:\d{2}")

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

    for i in range(len(switch)):        # removes certain characters
        artistname = artistname.lower().replace(switch[i][0], switch[i][1])
        songname   = songname.lower().replace(switch[i][0], switch[i][1])


    # make request
    resp = requests.get(f'https://genius.com/{artistname}-{songname}-lyrics', headers=chrome_header)

    if resp.status_code != 200:
        print(f'{artistname}-{songname}-lyrics')
        print('\t->', resp.status_code, resp)
        return

    soup_html = BeautifulSoup(resp.text, 'html.parser')
    lyrics_container = soup_html.find_all("div", attrs={"data-lyrics-container" : True} )

    if lyrics_container:
        lyrics = []

        for section in lyrics_container:
            lines_list = section.get_text(separator="\n").splitlines()
            for i in range(len(lines_list)-1, -1, -1):      # iterate backwards to pop all unwanted lines
                if  '[' in lines_list[i] or ']' in lines_list[i]:
                    lines_list.pop(i)
                elif re.match( pattern_timestamp, lines_list[i] ):
                    lines_list.pop(i)
            lyrics += lines_list

        return '\n'.join(lyrics)

    else:
        return None




if __name__ == "__main__":
    print( retrieve_lyrics("Breaking Benjamin", "Torn in Two") )
