# -*- coding: utf-8 -*-
import datetime
import itertools
import requests
from xbmcswift2 import Plugin

import pprint

plugin = Plugin()

STRINGS = {
    'Sveriges_Radio': 30000,
    'unable_to_communicate': 30010,
    'unable_to_parse': 30011,
    'no_stream_found': 30012,
    'live': 30013,
    'channels': 30014,
    'categories': 30015,
    'all_programs': 30016,
    'sports': 30017,
    'all_broadcasts': 30018,
    'leagues': 30019,
    'teams': 30020,
}

QUALITIES = ["lo", "normal", "hi"]
FORMATS = ["mp3", "aac"]


def json_date_as_datetime(jd):
    sign = jd[-7]
    if sign not in '-+' or len(jd) == 13:
        millisecs = int(jd[6:-2])
    else:
        millisecs = int(jd[6:-7])
        hh = int(jd[-7:-4])
        mm = int(jd[-4:-2])
        if sign == '-': mm = -mm
        millisecs += (hh * 60 + mm) * 60000
    return datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=millisecs * 1000)


def format_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def _(string_id):
    return plugin.get_string(STRINGS[string_id])


def show_error(error):
    dialog = xbmcgui.Dialog()
    ok = dialog.ok(_('Sveriges_Radio'), error)


def load_url(url, params=None, headers=None):
    try:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r
    except Exception, e:
        plugin.log.error("plugin.audio.sverigesradio: unable to load url: '%s' due to '%s'" % (url, e))
        show_error(_('unable_to_communicate'))
        return None


def load_json(url, params):
    try:
        headers = {'Accept': 'application/json', 'Accept-Charset': 'utf-8'}
        r = load_url(url, params, headers)
        if r:
            return r.json()
    except Exception, e:
        plugin.log.error("plugin.audio.sverigesradio: unable to parse result from url: '%s' due to '%s'" % (url, e))
        show_error(_('unable_to_parse'))
        return None


def load_channels():
    SRAPI_CHANNEL_URL = "http://api.sr.se/api/v2/channels"
    quality = plugin.get_setting('quality', choices=QUALITIES)
    params = {'format': 'json', 'pagination': 'false', 'audioquality': quality, 'liveaudiotemplateid': 5}
    channels = load_json(SRAPI_CHANNEL_URL, params)
    return channels


def load_sports_broadcasts(team=None, league=None):
    SRAPI_SPORTS_URL = "http://api.sr.se/api/v2/sport/broadcasts"
    quality = plugin.get_setting('quality', choices=QUALITIES)
    params = {'format': 'json', 'pagination': 'false', 'audioquality': quality, 'liveaudiotemplateid': 5}
    if team:
        params['teamIds'] = team
    if league:
        params['filter'] = "league.id"
        params['filterValue'] = league
    broadcasts = load_json(SRAPI_SPORTS_URL, params)
    return broadcasts


def load_sports_leagues():
    SRAPI_SPORTS_LEAGUES_URL = "http://api.sr.se/api/v2/sport/leagues"
    params = {'format': 'json', 'pagination': 'false'}
    leagues = load_json(SRAPI_SPORTS_LEAGUES_URL, params)
    return leagues


def load_sports_teams():
    SRAPI_SPORTS_TEAMS_URL = "http://api.sr.se/api/v2/sport/teams"
    params = {'format': 'json', 'pagination': 'false'}
    teams = load_json(SRAPI_SPORTS_TEAMS_URL, params)
    return teams


@plugin.cached()
def load_programs(channel_id='', category_id=''):
    SRAPI_PROGRAM_URL = "http://api.sr.se/api/v2/programs/index"
    params = {'format': 'json', 'pagination': 'false', 'filter': 'program.hasondemand', 'filterValue': 'true'}
    if channel_id:
        params['channelid'] = channel_id
    if category_id:
        params['programcategoryid'] = category_id
    programs = load_json(SRAPI_PROGRAM_URL, params)
    return programs


@plugin.cached()
def load_program_episodes(program_id, quality):
    SRAPI_EPISODE_URL = "http://api.sr.se/api/v2/episodes"
    params = {'format': 'json', 'pagination': 'false', 'audioquality': quality, 'programid': program_id}
    episodes = load_json(SRAPI_EPISODE_URL, params)
    return episodes


@plugin.cached()
def load_program_info(program_id):
    SRAPI_PROGRAM_URL = "http://api.sr.se/api/v2/programs/{0}"
    params = {'format': 'json', 'pagination': 'false'}
    url = SRAPI_PROGRAM_URL.format(program_id)
    program_info = load_json(url, params)
    return program_info


@plugin.cached()
def load_categories():
    SRAPI_PROGRAM_CATEGORIES = "http://api.sr.se/api/v2/programcategories"
    params = {'format': 'json', 'pagination': 'false'}
    categories = load_json(SRAPI_PROGRAM_CATEGORIES, params)
    return categories


def create_live_channel(channel):
    name = channel['name']
    url = channel['liveaudio']['url']
    logo = channel['image']
    item = {'label': name, 'path': url, 'icon': logo, 'is_playable': True}
    return item


def create_sports_broadcast(broadcast):
    date = json_date_as_datetime(broadcast['localstarttime'])
    name = broadcast['name'] + " - " + format_datetime(date)
    url = broadcast['liveaudio']['url']
    date_strftime = date.strftime("%d.%m.%Y")
    info = {'date': date_strftime, 'title': name, 'artist': _('Sveriges_Radio')}

    item = {'label': name, 'path': url, 'is_playable': True, 'info': info}
    pprint.pprint(broadcast['localstarttime'])
    return item


def create_sports_league(league):
    id = league['id']
    name = league['name']
    item = {'label': name, 'path': plugin.url_for('list_sports_league_broadcasts', id=id), 'is_playable': False}
    return item


def create_sports_team(team):
    id = team['id']
    name = team['name'] + " - " + team['league']['name']
    item = {'label': name, 'path': plugin.url_for('list_sports_team_broadcasts', id=id), 'is_playable': False}
    return item


def create_channel(channel):
    name = channel['name']
    logo = channel['image']
    id = channel['id']
    item = {'label': name, 'path': plugin.url_for('list_channel_programs', id=id), 'icon': logo, 'is_playable': False}
    return item


def create_program(program):
    name = program['name']
    logo = program['programimage']
    id = program['id']
    item = {'label': name, 'path': plugin.url_for('list_program', id=id), 'icon': logo, 'is_playable': False}
    return item


def create_category(category):
    name = category['name']
    id = category['id']
    item = {'label': name, 'path': plugin.url_for('list_category', id=id), 'is_playable': False}
    return item


def create_broadcast(episode, program_name, prefer_broadcasts):
    name = episode['title']
    logo = episode['imageurl']
    description = episode['description']
    name = "%s - %s" % (name, description)
    items = []
    if prefer_broadcasts and 'broadcast' in episode:
        extract_broadcasts(items, episode['broadcast'], logo, name, program_name)
    elif 'listenpodfile' in episode:
        extract_pod_file(items, episode['listenpodfile'], logo, name, program_name)
    elif 'downloadpodfile' in episode:
        extract_pod_file(items, episode['downloadpodfile'], logo, name, program_name)
    elif not prefer_broadcasts and 'broadcast' in episode:
        extract_broadcasts(items, episode['broadcast'], logo, name, program_name)
    return items


def extract_pod_file(items, pod_info, logo, name, program_name):
    url = pod_info['url']
    date_str = pod_info['publishdateutc']
    date_object = datetime.datetime.fromtimestamp(float(int(date_str[6:-2]) / 1000)).date()
    date_strftime = date_object.strftime("%d.%m.%Y")
    duration = pod_info['duration']
    size = pod_info['filesizeinbytes']
    info = {'duration': duration, 'date': date_strftime, 'title': name, 'size': size, 'album': program_name,
            'artist': _('Sveriges_Radio')}
    item = {'label': name, 'path': url, 'icon': logo, 'is_playable': True, 'info': info}
    items.append(item)


def extract_broadcasts(items, broadcast, logo, name, program_name):
    for file in broadcast['broadcastfiles']:
        url = file['url']
        date_str = file['publishdateutc']
        date_object = datetime.datetime.fromtimestamp(float(int(date_str[6:-2]) / 1000)).date()
        date_strftime = date_object.strftime("%d.%m.%Y")
        duration = file['duration']
        info = {'duration': duration, 'date': date_strftime, 'title': name, 'album': program_name,
                'artist': _('Sveriges_Radio')}
        item = {'label': name, 'path': url, 'icon': logo, 'is_playable': True, 'info': info}
        items.append(item)


@plugin.route('/channel/<id>')
def list_channel_programs(id):
    response = load_programs(channel_id=id)
    if response:
        items = [create_program(program) for program in response['programs']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/program/<id>')
def list_program(id):
    QUALITIES = ["lo", "normal", "hi"]
    quality = plugin.get_setting('quality', choices=QUALITIES)
    response = load_program_episodes(id, quality)
    program_info = load_program_info(id)
    program_name = program_info["program"]["name"]
    if response:
        PREFERENCE_CHOICES = [True, False]
        prefer_broadcasts = plugin.get_setting('preference', choices=PREFERENCE_CHOICES)
        items = [create_broadcast(episode, program_name, prefer_broadcasts) for episode in response['episodes']]
        items = list(itertools.chain(*items))
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        plugin.add_sort_method('date')
        return items


@plugin.route('/category/<id>')
def list_category(id):
    response = load_programs(category_id=id)
    if response:
        items = [create_program(program) for program in response['programs']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/live/')
def list_live():
    response = load_channels()
    if response:
        items = [create_live_channel(channel) for channel in response['channels']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/channels/')
def list_channels():
    response = load_channels()
    if response:
        items = [create_channel(channel) for channel in response['channels']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/categories/')
def list_categories():
    response = load_categories()
    if response:
        items = [create_category(category) for category in response['programcategories']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/sports/league/<id>')
def list_sports_league_broadcasts(id):
    # get broadcasts for league=id
    response = load_sports_broadcasts(league=id)
    if response:
        items = [create_sports_broadcast(broadcast) for broadcast in response['broadcasts']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        plugin.add_sort_method('date')
        return items


@plugin.route('/sports/team/<id>')
def list_sports_team_broadcasts(id):
    # get broadcasts for team=id
    response = load_sports_broadcasts(team=id)
    if response:
        items = [create_sports_broadcast(broadcast) for broadcast in response['broadcasts']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        plugin.add_sort_method('date')
        return items


@plugin.route('/sports/broadcasts/')
def list_sports_broadcasts():
    response = load_sports_broadcasts()
    if response:
        items = [create_sports_broadcast(broadcast) for broadcast in response['broadcasts']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        plugin.add_sort_method('date')
        return items


@plugin.route('/sports/leagues/')
def list_sports_leagues():
    response = load_sports_leagues()
    if response:
        items = [create_sports_league(league) for league in response['leagues']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/sports/teams/')
def list_sports_teams():
    response = load_sports_teams()
    if response:
        items = [create_sports_team(team) for team in response['teams']]
        plugin.add_sort_method('playlist_order')
        plugin.add_sort_method('label')
        return items


@plugin.route('/sports/')
def list_sports():
    items = [
        {'label': _('all_broadcasts'), 'path': plugin.url_for('list_sports_broadcasts')},
        {'label': _('leagues'), 'path': plugin.url_for('list_sports_leagues')},
        {'label': _('teams'), 'path': plugin.url_for('list_sports_teams')}
    ]
    return items


@plugin.route('/allprograms/')
def list_all_programs():
    response = load_programs()
    if response:
        items = [create_program(program) for program in response['programs']]
        plugin.add_sort_method('label')
        return items


@plugin.route('/')
def index():
    items = [
        {'label': _('live'), 'path': plugin.url_for('list_live')},
        {'label': _('channels'), 'path': plugin.url_for('list_channels')},
        {'label': _('categories'), 'path': plugin.url_for('list_categories')},
        {'label': _('sports'), 'path': plugin.url_for('list_sports')},
        {'label': _('all_programs'), 'path': plugin.url_for('list_all_programs')},
    ]
    return items


if __name__ == '__main__':
    plugin.run()
