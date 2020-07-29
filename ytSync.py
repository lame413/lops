#!/usr/bin/env python3.7

import os
import sys
import json
import pyjq
import youtube_dl
import mutagen
import argparse
import requests
import string

# for perf measuring
import time
import functools

#### TODO: implement error handling in everything, implement a logger

musicFolder = "playlists/"


if os.path.exists(musicFolder) != True:
    os.mkdir(musicFolder)
    os.chdir(musicFolder)

parser = argparse.ArgumentParser()

def my_hook(d):
    #### TODO: something actually useful with this lmao
    if d['status'] == 'finished':
        pass
        #print("Downloaded \"", d['filename'][:d['filename'].rindex('.')],"\"", sep='')
        #print(d)
    if d['status'] == 'downloading':
        pass # todo: prettify, since it's spammy
        #print(d['filename'], d['_percent_str'], d['_eta_str'])
   
def _returnVideoOrPlaylistID(url):
    """
    Returns a if a given link is a video or a playlist.
    
    Returns None if URL invalid or not a video.
    """
    id = _quickGetVideoID(url)
    
    if id is None:
            
        youtubeIDCharset = set(string.ascii_letters + string.digits + '-' + '_')
        if(len(url) == 34):
            if set(url).issubset(youtubeIDCharset):
                return url
            else:
                return None
        if(str(url).find("list=") != -1):
            tmp = str(url).partition("list=")[2][:34]
            if set(tmp).issubset(youtubeIDCharset):
                    return tmp
    else:
        return None
    
def _quickGetVideoID(url):
    """
    Returns the video's ID.

    Returns None if URL invalid or not a video.
    """

    # youtube video ID's are 11 chars long and consist of 
    # ascii lowercase, uppercase, digits, - and _
    youtubeIDCharset = set(string.ascii_letters + string.digits + '-' + '_')

    if(len(url) == 11): 
        if set(url).issubset(youtubeIDCharset):
            return url
        else:
            return None
    elif(len(url) < 11):
        return None
    else:
        if(str(url).find("youtu.be/") != -1):
            tmp = str(url).partition("youtu.be/")[2][:11]
            if set(tmp).issubset(youtubeIDCharset):
                return tmp
        elif(str(url).find("v=") != -1):
            tmp = str(url).partition("v=")[2][:11]
            if set(tmp).issubset(youtubeIDCharset):
                return tmp
        else:
            return None

def getPlaylistInfo(url):
    """
    Download playlist information as JSON and return it.

    If used with a channel URL as an argument, returns data on all of the 
    channels' playlists. Raises an error if no such channel exists.

    If used with a playlist, returns the data on all songs in the playlist.
    """

    ydl_opts = {
        'extract_flat': True, 
        'download': False, 
        'in_playlist': True, 
        'skip_download': True,
        'quiet': True
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url)

        # if it extracted user data, return the 'uploads' playlist
        if(pyjq.first('.extractor', data) == "youtube:user"):
            data = getPlaylistInfo(pyjq.first('.url', data))

    except Exception: # TODO: implement proper error handling, this assumes all errors as 404
        #raise requests.HTTPError("Playlist or channel not found; server returned 404.") from e
        print("Playlist or channel not found; server returned 404.")
        return None
    else:
        return data

def getIDMetadata(file):
    """
    Reads the "vidID" tag.
    """
    #### TODO: get some mp3's and test this shit, since ffmpeg loses metadata on recode
    #### and i can't be bothered to test those nested try excepts
    s = mutagen.File(file)

    try:
        id = s['vidID']
        if isinstance(id, list):
            id = id[0]            
        return id
    except TypeError:
        print("File",file,"does not support custom tags")
        return None
    except KeyError:
        try:
            id = s.tag['vidID']
        except AttributeError:
            print("File",file,"does not have a \'vidID\' tag set")
            return None
        except KeyError:
            print("File",file,"does not have a \'vidID\' tag set")
            return None
        return None

def setIDMetadata(file, id):
    """
    Creates and sets a "vidID" tag in the provided file.    
    """
    #### TODO: implement mp3 handling
    s = mutagen.File(file)

    try:
        s['vidID'] = id
        s.save()
    except TypeError:
        print("File",file,"does not support custom tags")    

def downloadSong(url):
    """
    Download a song, save the ID in 'vidID' metadata field.

    Returns the saved songs' path.
    """

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus'
            },
          #  {'key': 'EmbedThumbnail'}, # doesn't work, crashes ffmpeg
            {'key': 'FFmpegMetadata'}
        ],
        'progress_hooks': [my_hook],
        'quiet': True
    }

    filename = ''

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = str(ydl.prepare_filename(info))

    # if opus: change from .opus to .ogg, as some music players can't play .opus
    noExtension = filename[:filename.rindex('.')]
    filename = noExtension+".ogg"
    os.rename(noExtension+".opus", filename)

    setIDMetadata(filename, info['id'])

    return filename

def getSongsInDir(path):
    try:
        files = [f for f in os.listdir(path) if os.path.isfile(path + '/' + f)]
        return files
    except FileNotFoundError:
        return []

def getMissingSongs(playlistJson):
    """
    Returns a list json of song IDs for present in the 
    online playlist, but not found in the local version 
    of the playlist.
    """

    # load that into json, get title, songlist
    playlistTitle = pyjq.first('.title', playlistJson)
    
    # songs to be downloaded
    songIDs = pyjq.all('.entries[].id', playlistJson)

    if os.path.exists(playlistTitle) != True:
        os.mkdir(playlistTitle)
        os.chdir(playlistTitle)
    else:
        os.chdir(playlistTitle)
        # Compare local songs to songs in playlist, update songIDs accordingly
        localIDs = getIDsFromSongs(getSongsInDir('.'))
        for i in localIDs:
            if i in songIDs:
                songIDs.remove(i)

    os.chdir("..")

    return songIDs

def reducePlaylistToMissingSongs(playlistJson, ms):
    """
    Removes songs already present in storage from json data.
    """
    playlist = pyjq.all('.entries[]', playlistJson)

    playlistNew = []

    for song in playlist:
        if pyjq.first(".id", song) in ms:
            playlistNew.append(song)
    
    return playlistNew

def getThumbnailURL(url):
    """
    Gets and returns a URL pointing to a video's thumbnail.

    Returns the URL or None if url isn't a video link.
    """

    # youtube thumbnails can be accessed by 
    # plugging the video ID into the url below
    url_0 = "http://img.youtube.com/vi/"
    url_1 = "/0.jpg"

    id = _quickGetVideoID(url)

    if id:
        return url_0 + id + url_1
    else:
        return None

def getIDsFromSongs(files, *dirPath):
    """
    Get the 'vidID' metadata from a list of files.

    Use 'dirPath' to pass the full path to the songs directory.
    """
    ids = []

    if not dirPath:
        for f in files:
            ids.append(getIDMetadata(f))
    else:
        for f in files:
            ids.append(getIDMetadata(dirPath[0]+'/'+f))
        
    return ids

def syncPlaylist(url):
    """
    Compare a Youtube playlist to songs stored locally, in a folder
    named after said playlist. Download all missing songs.
    """

    # move to playlist folder where they should be downloaded
    playlistJson = getPlaylistInfo(url)

    # get list of missing songs
    songIDs = getMissingSongs(playlistJson)


    playlistTitle = pyjq.first('.title', playlistJson)
    
    # getMissingSongs() already checks for, 
    # and if missing - creates, the playlist folder,
    # so we can just cd into it
    os.chdir(playlistTitle)

    for i in songIDs:
        downloadSong(i)

    os.chdir("..")

def getChannelPlaylists():
    pass

def getSongInfo(url):
    
    """
    Gets url, returns tuple (TITLE, YT_ID)
    """

    ydl_opts = {
        'extract_flat': True, 
        'download': False, 
        'in_playlist': True, 
        'skip_download': True,
        'quiet': True,
        'youtube_include_dash_manifest': False,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        title = pyjq.first('.title', info)
        id = pyjq.first('.id', info)
        return (title, id)

def getSongInfoJson(songJson):
    
    """
    Gets json, returns tuple (TITLE, YT_ID)
    """
    print(songJson)

    title = pyjq.first(".title", songJson)
    id = pyjq.first(".id", songJson)

    return (title, id)

if __name__ == "__main__":
    print(getIDMetadata("chill~ 👌/Dust In Your Pocket.ogg"))
    st = time.perf_counter()

    #print(getSongInfo("https://www.youtube.com/watch?v=bByl2B3A3nE"))

    t1 = time.perf_counter()
    print("single song title: ", t1-st)

    currPlaylist = getPlaylistInfo("https://www.youtube.com/playlist?list=PLWPsjpCBYRUkA2ubLZ5-riZfdZog3iE9H")

    ms = getMissingSongs(currPlaylist)

    currPlaylist = reducePlaylistToMissingSongs(currPlaylist, ms)

    for song in currPlaylist:
        getThumbnailURL(pyjq.first(".id", song))

   # for x in currPlaylist:
    #    print(x)#

    #syncPlaylist("https://www.youtube.com/playlist?list=PLWPsjpCBYRUkA2ubLZ5-riZfdZog3iE9H")

    t2 = time.perf_counter()
    print("19 song album time:", t2-t1)




    #print(getSongInfo("https://www.youtube.com/watch?v=gJSxZel_HUg"))
    #getSongInfo("https://www.youtube.com/watch?v=dIyKy4A4kBU")
    #print(getThumbnailURL("https://youtu.be/3XB7PK2-lUc"))
    #print(getThumbnailURL("https://www.youtube.com/watch?v=vVv69Kv4UDE"))
    #print(getThumbnailURL("01234567890"))
    #print(getThumbnailURL("asdf"))

    #getThumbnailURL("https://www.youtube.com/playlist?list=PLWPsjpCBYRUkqWdahKBvqP3-wWhgP-Wu_")
    #playlistsChannelJSON = getPlaylistInfo("https://www.youtube.com/user/8GrejmoN8/playlists")
    #playlistsChannelJSON = getPlaylistInfo("https://www.youtube.com/user/8GrejmoN8")
    #print(playlistsChannelJSON)
    #playlistsChannelJSON = getPlaylistInfo("https://www.youtube.com/playlist?list=FL75RC_71yrBxjGGig7GEnDg")
    #print(pyjq.first('.extractor', playlistsChannelJSON))
    #playlistsURLs = pyjq.all('.entries[].url', playlistsChannelJSON)
    #playlistsJSON = []
    
    # for idx, i in enumerate(playlistsURLs):
    #     playlistsJSON.append(getPlaylistInfo(i))
    #     playlistTitle = pyjq.first('.title', playlistsJSON[idx])
    #     nOfSongs = len(pyjq.all('.entries[]', playlistsJSON[idx]))

    #     nOfSongsLocally = len(getSongsInDir(playlistTitle))

    #     print(idx+1, ") ", playlistTitle, ", ", nOfSongs, " songs ", sep='', end='')

    #     if nOfSongsLocally == 0:
    #         print("(not synced)")
    #     elif nOfSongsLocally < nOfSongs:
    #         print("(missing", nOfSongs - nOfSongsLocally, "songs)")
    #     else:
    #         print()

    # dl = int(input("Select which playlist to synchronize: "))

    # syncPlaylist(playlistsURLs[dl - 1])

#syncPlaylist(playlistURL)