#!/usr/bin/python3

import json
import csv
import sys

data = []

with open('history.csv', 'r') as fd:
    reader = csv.reader(fd)
    for line in reader:
        data.append(line)
        
with open('song_database.json', 'r') as fd:
    song_db = json.load(fd)


def main(argv):
    elements = []
    results = []
    header = ''
    print_limit = 20

    for arg in argv:
        if arg not in ['-t', '--title', '-r', '--record', '--sum','-e', '--explicit', '-a', '--artist','-g', '--genre','--mode','--tempo','--key', '-o', '--order', '-c', '-count', '--reverse', '--all']:
            if not arg.strip('-').isdigit():
                print(arg, 'is not a known argument. Check for "-" and "--" errors.')
                quit()


    # Daten in elementliste einfügen, mit Dopplungen
    if '-t' in argv or '--title' in argv:
        header = 'Song'
        for row in data:
            elements.append(row[2])

    elif '-r' in argv or '--record' in argv:
        header = 'Record'
        for row in data:
            elements.append(row[4])

    elif '-e' in argv or '--explicit' in argv:
        header = 'Record'
        for row in data:
            elements.append(row[6])

    elif '-a' in argv or '--artist' in argv:
        header = 'Artist'
        for row in data:
            artist_list = row[7].split(',')
            for artist in artist_list:
                elements.append(artist.strip())
     
    elif '-g' in argv or '--genre' in argv:
        header = 'Genre'
        for row in data:
            for artist in song_db[row[1]]['artist']:
                if type(artist) is dict:
                    for genre in artist['genres']:
                        elements.append(genre)

        
    elif '--tempo' in argv:
        header = 'Tempo'
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                elements.append(song['audio-features']['tempo'])
        
        
    elif '--key' in argv:
        header = 'Key'
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'G', 'G#', 'A', 'A#', 'B']
                key_of_song = keys[song['audio-features']['key'] - 1]
                if '--mode' in argv:
                    modes = [' ', 'm']
                    key_of_song += modes[song['audio-features']['mode']]     

                    while len(key_of_song) < 3: # damit alle gleich breit formatiert werden
                        key_of_song += ' ' 
                
                elements.append(key_of_song)
                
        
    elif '--mode' in argv:
        header = 'Tempo'
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                modes = ['Major', 'Minor']
                elements.append(modes[song['audio-features']['mode']])
        
        

    # Daten zählen
    for el in elements:
        containes_el = False
        if results == []:
            results.append([el, 1])
            continue
        for res in results:
            if el == res[0]:
                res[1] += 1
                containes_el = True
                break
        if not containes_el:
            results.append([el, 1])

    # Daten sortieren
    if '-o' in argv or '--order' in argv:
        if '--reverse' in argv:
            results.sort(key=lambda res: (-res[1], res[0].lower()), reverse=True)
        else:
            results.sort(key=lambda res: (-res[1], res[0].lower()))
    else:
        results.sort(key=lambda res: res[0].lower())



    if '-c' in argv or '--count' in argv:
        print(f"\n{len(results)} {header}s found")

    if '--sum' in argv:
        print('\nSum of all Results:', sum([res[1] for res in results]))

    # set number of results to print
    for arg in argv:
        if arg.strip('-').isdigit():
            print_limit = int(arg.strip('-'))
            break
        elif arg == '--all':
            print_limit = len(results)
    print('\nshowing', print_limit, 'results (specify with --<int> or --all)\n')

    # output results
    print('{0:>30} | Plays'.format(header))
    print('-'*40)
    for i, res in enumerate(results):
        if i == print_limit:
            break
        total = sum([res[1] for res in results])
        highest_value = max([res[1] for res in results])
        print('{0:>30} | {1:<4} {2}'.format(
            res[0] if len(res[0]) <= 30 else res[0][:27] + "…", res[1], '#' * int((res[1]*50)/highest_value)
            )
        )




if __name__ == '__main__':
    main(sys.argv[1:])
