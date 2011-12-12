#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#   Copyright (c) 2008-2011 Tobias Hieta <tobias@hieta.se>
#

import sc2casts
import cerealizer
import re

PLUGIN_PREFIX = "/video/sc2castscom"
VERSION="1.0"

ART = "art-default.jpg"
THUMB = 'icon-default.png'

TOP=0
BROWSE=1
SEARCH=2

BROWSE_EVENTS=0
BROWSE_PLAYERS=1
BROWSE_CASTERS=2
BROWSE_MATCHUPS=3

YTIMG_URL='http://i.ytimg.com/vi/%s/hqdefault.jpg'
YOUTUBE_VIDEO_PAGE = 'http://www.youtube.com/watch?v=%s'
YOUTUBE_VIDEO_FORMATS = ['Standard', 'Medium', 'High', '720p', '1080p']
YOUTUBE_FMT = [34, 18, 35, 22, 37]

USER_AGENT = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12'

def Start():
    Plugin.AddPrefixHandler(PLUGIN_PREFIX,
                            MainMenu,
                            u"SC2Casts",
                            THUMB,
                            ART)

    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    MediaContainer.art = R(ART)
    MediaContainer.title1 = "SC2Casts.com"
    MediaContainer.viewGroup = "List"
    DirectoryItem.thumb = R(THUMB)
    cerealizer.register(sc2casts.SC2Cast)
    HTTP.CacheTime = 3600
    HTTP.Headers['User-Agent'] = USER_AGENT
    Log("Started")


def MainMenu():
	dir = MediaContainer(viewMode="List", noCache=True)
	dir.Append(Function(DirectoryItem(RecentList, "Recent Casts")))
	dir.Append(Function(DirectoryItem(SubMenuList, "Top Casts"), page=TOP))
	dir.Append(Function(DirectoryItem(SubMenuList, "Browse Casts"), page=BROWSE))
	dir.Append(Function(InputDirectoryItem(SearchList, "Search Casts", "Search Casts", "Search Casts", thumb=R('icon-search.png'))))
	dir.Append(PrefsItem('Preferences', thumb=R('icon-prefs.png')))
	return dir

def SearchList(sender,query=''):
    cl=sc2casts.SC2CastsClient()
    return SeriesList('Search results', cl.search(query))

def getYtImage(id):
    url = YTIMG_URL % id
    Log("getting image %s", url)
    try:
        data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return Redirect(R(THUMB))

def GameInfo(sender, game):
    sc2casts.getCastDetails(game)
    dir = MediaContainer(viewMode='InfoList')
    dir.title2='%s vs %s (%s)' % (game.players[0], game.players[1], game.bestof)
    gamenr = 1
    rating = 0
    if game.rateup:
        rating = (float(game.rateup) * 10.0) / (float(game.rateup) + float(game.ratedown))
    Log(rating)
    for p in game.games:
        summary = "Casted by: %s\nAt %s, %s" % (game.caster, game.event, game.round)
 
        if len(p) > 1:
            partnr = 1
            for part in p:
                title = "Game %d, part %d" % (gamenr, partnr)
                dir.Append(VideoItem(Route(PlayVideo, video_id=part), title, rating=rating, summary=summary, thumb = Function(getYtImage, id=part)))
                partnr+=1
        else:
            dir.Append(VideoItem(Route(PlayVideo, video_id=p[0]), "Game %d" % gamenr, rating=rating, summary=summary, thumb=Function(getYtImage,id=p[0])))
        gamenr+=1

    return dir

def SeriesList(title, listOfGames):
    dir = MediaContainer(viewMode='InfoList')
    dir.title2=title
    Log("in SeriesList")

    for game in listOfGames:
        title = "%s vs %s (%s)" % (game.players[0], game.players[1], game.bestof)
        subtitle = "Casted by: %s\nAt %s, %s" % (game.caster, game.event, game.round)
        dir.Append(Function(DirectoryItem(GameInfo, title, summary=subtitle,thumb=R('%s.png' % game.matchup())), game=game))

    return dir

def RecentList(sender):
    cl = sc2casts.SC2CastsClient()
    return SeriesList('Recent casts', cl.getRecentCasts())

def TopList(sender, page):
    cl = sc2casts.SC2CastsClient()
    return SeriesList('Top casts', cl.getTopCasts(page))

def SubBrowseList(sender, id, section):
    cl=sc2casts.SC2CastsClient()
    return SeriesList('Browse : '+section, cl.subBrowse(section,id))

def BrowseList(sender, page):
    cl=sc2casts.SC2CastsClient()
    blist=cl.browse(page)

    dir=MediaContainer(viewMode='List', title2='Browse : '+page)
    for entry in blist:
        if page==sc2casts.SECTION_MATCHUP:
            dir.Append(Function(DirectoryItem(SubBrowseList, entry[1], thumb=R("%s.png" % entry[1])), id=entry[0], section=page))
        else:
            dir.Append(Function(DirectoryItem(SubBrowseList, entry[1]), id=entry[0], section=page))

    return dir
    

def SubMenuList(sender, page):
    dir = MediaContainer(viewMode="List")
    if page == TOP:
        dir.title2='Top casts'
        dir.Append(Function(DirectoryItem(TopList, "Last 24 Hours"), page=sc2casts.TIMEFRAME_DAY))
        dir.Append(Function(DirectoryItem(TopList, "This Week"), page=sc2casts.TIMEFRAME_WEEK))
        dir.Append(Function(DirectoryItem(TopList, "This Month"), page=sc2casts.TIMEFRAME_MONTH))
        dir.Append(Function(DirectoryItem(TopList, "All Time"), page=sc2casts.TIMEFRAME_ALL))
    if page == BROWSE:
        dir.title2='Browse'
        dir.Append(Function(DirectoryItem(BrowseList, "Browse Events"), page=sc2casts.SECTION_EVENT))
        dir.Append(Function(DirectoryItem(BrowseList, "Browse Players"), page=sc2casts.SECTION_PLAYER))
        dir.Append(Function(DirectoryItem(BrowseList, "Browse Casters"), page=sc2casts.SECTION_CASTER))
        dir.Append(Function(DirectoryItem(BrowseList, "Browse Matchups"), page=sc2casts.SECTION_MATCHUP))
    if page == SEARCH:
        pass

    return dir

@route('/video/sc2castscom/v/p')
def PlayVideo(video_id):
    Log("in PlayVideo")
    yt_page = HTTP.Request(YOUTUBE_VIDEO_PAGE % (video_id), cacheTime=1).content 

    fmt_url_map = re.findall('"url_encoded_fmt_stream_map".+?"([^"]+)', yt_page)[0]
    fmt_url_map = fmt_url_map.replace('\/', '/').split(',')

    fmts = []
    fmts_info = {}

    for f in fmt_url_map:
        map = {}
        params = f.split('\u0026')
        for p in params:
            (name, value) = p.split('=')
            map[name] = value
        quality = str(map['itag'])
        fmts_info[quality] = String.Unquote(map['url'])
        fmts.append(quality)

    index = YOUTUBE_VIDEO_FORMATS.index(Prefs['quality'])
    if YOUTUBE_FMT[index] in fmts:
        fmt = YOUTUBE_FMT[index]
    else:
        for i in reversed( range(0, index+1) ):
            if str(YOUTUBE_FMT[i]) in fmts:
                fmt = YOUTUBE_FMT[i]
                break
            else:
                fmt = 5

    url = (fmts_info[str(fmt)]).decode('unicode_escape')
    Log("  VIDEO URL --> " + url)
    return Redirect(url)
