#!/usr/bin/python3

import json
import csv
import sys
from tkinter import EXCEPTION

data = []

with open('history.csv', 'r') as fd:
    reader = csv.reader(fd)
    for line in reader:
        data.append(line)
        
with open('song_database.json', 'r') as fd:
    song_db = json.load(fd)


def main(argv):
    countable_attribute = True  # should all occurences be counted and sorted by that (=True) OR False for atributes that are sortable by nature, i.e. song duration
    
    elements = []
    results = []
    header = ''
    values = 'Plays'
    print_limit = 20

    for arg in argv:
        if arg not in ['-t', '--title', '-r', '--record', '--sum','-e', '--explicit', '-a', '-d', '--duration','--tempo', '--artist','-g', '--genre','--mode','--tempo','--key', '-o', '--order', '-c', '-count', '--reverse', '--all']:
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
        values = 'Artists'
        for row in data:
            for artist in song_db[row[1]]['artist']:
                if type(artist) is dict:
                    for genre in artist['genres']:
                        elements.append(genre)

        
    elif '--tempo' in argv:
        header = 'Song'
        values = 'BPM'
        countable_attribute = False
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                elements.append([song["titel"], round(song['audio-features']['tempo'])])

    elif '-d' in argv or '--duration' in argv:
        header = 'Song'
        values = 'Duration'
        countable_attribute = False
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                elements.append([song["titel"], round(song['audio-features']['duration_ms'])])

       
        
    elif '--key' in argv:
        header = 'Key'
        values = 'Occurences'
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
        header = 'Mode'
        values = 'Occurences'
        for row in data:
            song = song_db[row[1]]
            if 'audio-features' in song:
                modes = ['Minor', 'Major']
                elements.append(modes[song['audio-features']['mode']])
        
        

    # Daten zählen
    
    # Die Häufigkeit eines Elements wird gezählt
    if countable_attribute:
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
                
    # Das Element hat bereits einen Wert nach dem es sich sortieren lässt, es werden nur Duplikate entfernt
    else:
        elements.sort()
        for i in range(len(elements)-2, 0, -1):
            if elements[i] == elements[i+1]:
                elements.pop(i+1)
        results = elements

            
            
            

        

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
    print('{0:>30} | {1}'.format(header, values))
    print('-'*50)
    for i, res in enumerate(results):
        if i == print_limit:
            break
        highest_value = max([res[1] for res in results])
        print_value = res[1]

        if values == "Duration":
            milis = res[1]
            secs = milis / 1000
            mins = secs / 60
            in_minutes = int(mins)
            in_secs = str(int(secs) - 60 * in_minutes)
            print_value = str(in_minutes) + " min " + (in_secs + " s" if in_secs else "")
  
        print('{0:>30} | {1:<10} {2}'.format(
            res[0] if len(res[0]) <= 30 else res[0][:27]+ "…",
            print_value,
            '#' * int((res[1]*50)/highest_value)
            )
        )




if __name__ == '__main__':
    main(sys.argv[1:])
