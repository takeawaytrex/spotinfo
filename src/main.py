import json
from flask import Flask, request, redirect, g, render_template
import requests
import base64
import urllib
import urllib.parse
import os
import sqlite3
import errno


# TODO: generate session cookie
# TODO: store session cookie
# TODO: when auth key received from spotify, store alongside session cookie
# TODO:                       so that this can be used for further API keys


# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.

app = Flask(__name__)

#  Client Keys
CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8080
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private ugc-image-upload user-follow-modify user-follow-read user-library-read user-library-modify user-read-private user-read-birthdate user-read-email user-top-read user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key,urllib.parse.quote(val)) for key,val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI
    }

    base64encoded = base64.urlsafe_b64encode("{}:{}".format(CLIENT_ID, CLIENT_SECRET).encode('UTF-8')).decode('ascii')
    headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

    if (post_request.ok == False):
        return index()

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    print("Access token: {}".format(access_token))
    print("Refresh token: {}".format(refresh_token))
    print("Token type: {}".format(token_type))
    print("Expires in: {}".format(expires_in))

    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}

    # Get profile data
    user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)

    fields = ['birthdate', 'country', 'email', 'followers', 'id', 'images', 'product']

    data_dict = {}
    for field in fields:
        data_dict[field] = profile_data[field]

    # Get user playlist data
    playlist_items = []
    playlist_api_endpoint = "{}/playlists?limit=50".format(profile_data["href"])
    playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
    playlist_data = json.loads(playlists_response.text)
    playlist_items += playlist_data['items']

    while (playlist_data['next'] != None):
        playlist_api_endpoint = "{}/playlists?limit=50&offset={}".format(profile_data["href"], str(int(playlist_data['offset'])+int(playlist_data['limit'])))
        playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
        playlist_data = json.loads(playlists_response.text)
        playlist_items += playlist_data['items']

    user_playlists = []
    user_playlist_total = 0
    follow_playlists = []
    follow_playlist_total = 0
    max_size = 0
    for playlist in playlist_items:
        max_size = max(playlist['tracks']['total'], max_size)
        if (playlist['owner']['id'] == profile_data['id']):
            user_playlists += [playlist]
            user_playlist_total += playlist['tracks']['total']
        else:
            follow_playlists += [playlist]
            follow_playlist_total += playlist['tracks']['total']

    data_dict['user_playlists'] = user_playlists
    data_dict['user_playlists_len'] = len(user_playlists)
    data_dict['user_playlist_total'] = user_playlist_total
    data_dict['user_playlist_top'] = get_most_followed(user_playlists, authorization_header)
    data_dict['follow_playlists'] = follow_playlists
    data_dict['follow_playlists_len'] = len(follow_playlists)
    data_dict['follow_playlist_total'] = follow_playlist_total
    data_dict['max_size'] = max_size
    return render_template("index.html",sorted_array=data_dict)


def get_most_followed(playlists, authorization_header):
    for playlist in playlists:
        endpoint = "{}".format(playlist["href"])
        response = requests.get(endpoint, headers=authorization_header)
        data = json.loads(response.text)
    return ""
        


if __name__ == "__main__":
    app.run(debug=True,port=PORT)


def goodbye():
    print("Goodbye")

import atexit
atexit.register(goodbye)

