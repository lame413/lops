#!/usr/bin/env python3.7

import ytSync as yts 
import sys

from kivy.core.window import Window
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout 
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.effects.scroll import ScrollEffect
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.image import Image, AsyncImage    
from kivy.config import Config

reduct = 2.8
Config.set('graphics', 'width', int(1080/reduct))
Config.set('graphics', 'height',int(1920/reduct))
Config.write()

# since kivy messes with printing out stderr after some crashes, 
# redirect and log errors to a file instead
sys.stderr = open('./stderr', 'w')

class Song():
    internal_id = None
    youtube_id = None
    url = None
    img_url = None
    title = None
    duration = None

    def __init__(self, intID, ytID, img):
        self.internal_id = intID
        self.youtube_id = ytID 
        self.img_url = img

class SongList(StackLayout):
    songs = []
    thumbHeight = 100
    albums = []
    albumHeight = 100

    def __init__(self, **kwargs):
        super(SongList, self).__init__(**kwargs)
        self.orientation = 'bt-lr'
        self.size_hint_y = None
        #self.minimum_height: self.height
        

#    def _update_rect(self, instance):
#        self.img.pos = instance.pos
#        self.img.size = instance.size

    def _update_height(self):
        self.height = len(self.songs) * self.thumbHeight + len(self.albums) * self.albumHeight + 5

    def _add_album(self, albumTitle):
        album_pos = BoxLayout(
            orientation='horizontal',
            size_hint = (1,None)
        )

        self.albums.append(albumTitle)

        titleLabel = Label(text=albumTitle)
        album_pos.add_widget(titleLabel)

        self._update_height()

        self.add_widget(album_pos)
    
    def _add_song(self, songData):
        songTitle = songData[0]
        songID = songData[1]

        song_pos = BoxLayout(
            orientation='horizontal',
            size_hint = (1,None)
        )

        img_url = yts.getThumbnailURL(songID)
        img = AsyncImage(source=img_url,
            #pos=(10, 50*self.songs),
            allow_stretch = True,
            height = 100,
            #width = self.parent.width,
            size_hint = (None, None)
        )
        self.songs.append((songTitle, songID))
        song_pos.add_widget(img)
        self._update_height()
        
        print("Added ", songTitle, "to visible playlist")
        titleLabel = Label(text=songTitle)
        song_pos.add_widget(titleLabel)

        self.add_widget(song_pos)
        #self.add_widget(img)

class thumbnails(Widget):
    thmb = ''

    def newThumbnail(self, url):
        thb = AsyncImage(source=url)
        self.thmb = thb
    
    def getThumbnail(self):
        return self.thmb

class YtApp(App):
    def build(self):
        self.parent = BoxLayout(orientation='vertical',
            padding=10,
            spacing=10
            )

        self.urlField = TextInput(
            multiline=False,
            text='https://www.youtube.com/playlist?list=PLWPsjpCBYRUkA2ubLZ5-riZfdZog3iE9H',
            size_hint=(1, None),
            height = 64,
            #pos = (100, 500)
            )

        self.oBtn = Button(
            text='Add song to list',
            size_hint=(1, None),
            height = 100,
            #pos=(100, 1000)
        )

        self.slist = SongList(
            size_hint=(1,1)
        )

        self.oBtn.bind(on_press=self.addSong)
        
        self.parent.add_widget(self.urlField)
        self.parent.add_widget(self.oBtn)

        self.songsRoot = ScrollView(
            #size_hint=(1, None), 
            #size=(100, 70),        
            do_scroll_x = False,
            effect_cls = ScrollEffect,
        )

        self.songsRoot.add_widget(self.slist)
        self.parent.add_widget(self.songsRoot)

        #self.parent.add_widget(self.slist)

        return self.parent

    def addSong(self, instance):
        url = str(self.urlField.text)
        if (yts._quickGetVideoID(url) != None):
            songData = yts.getSongInfo(url)
            self.slist._add_song(songData)
        elif (yts._returnVideoOrPlaylistID(url) != None):
            plinfo = yts.getPlaylistInfo(url)
            plTitle = yts.pyjq.first(".title", plinfo)
            
            #plSongs = yts.pyjq.all(".entries[]", plinfo)
            missingSongs = yts.getMissingSongs(plinfo)
            plSongs = yts.reducePlaylistToMissingSongs(plinfo, missingSongs)
            for song in plSongs:
                songData = yts.getSongInfoJson(song)
                self.slist._add_song(songData)

            self.slist._add_album(plTitle)

    def dlStuff(self, instance):
        img = yts.getThumbnailURL(str(self.urlField.text))
        if (yts._quickGetVideoID(self.urlField.text) != None):
            #thb = thumbnail()
            #thb.newThumbnail(img)
            #self.parent.add_widget(thb)
            self.i.source=img
        print(self.urlField.text)
        print(yts.getThumbnailURL(str(self.urlField.text)))
        #playlistsChannelJSON = yts.getPlaylistInfo("https://www.youtube.com/user/" + self.urlField.text + "/playlists")
        #print(playlistsChannelJSON)
        #playlistsChannelJSON = getPlaylistInfo("https://www.youtube.com/playlist?list=FL75RC_71yrBxjGGig7GEnDg")
        #print(yts.pyjq.first('.extractor', playlistsChannelJSON))

if __name__ == '__main__':
    #yts.updateYoutubeDL()
    YtApp().run()