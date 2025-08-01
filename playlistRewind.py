import spotipy
import time
import random
import config
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from spotipy.oauth2 import SpotifyOAuth

from flask import Flask, request, url_for, session, redirect

#init flask
app = Flask(__name__)

#need to save token to session, which will allow user to not have to log in all the time
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
app.secret_key = config.secret_key #used to prevent unauthorized access to the cookie
TOKEN_INFO = 'token_info'

#home page
@app.route('/')
def login():
    auth_url = create_spotify_oauth(show_dialog=True).get_authorize_url() #generates an auth url
    return redirect(auth_url) #sending user to the authorization url

#log out page
@app.route('/logout')
def logout():
    session.clear()
    auth_url = create_spotify_oauth(show_dialog=True).get_authorize_url()
    return redirect(auth_url)

#redirecting after logging in
@app.route('/redirect')
def redirect_page():
    session.clear() #makes sure user data that may be stored is all cleared
    code = request.args.get('code') #getting users auth code to use as the access token
    token_info = create_spotify_oauth().get_access_token(code) 
    session[TOKEN_INFO] = token_info #storing the token in our session
    return redirect(url_for('save_playlist_rewind', external= True))

#helper function to get all of the users playlists
def get_all_playlists(sp):
    results = sp.current_user_playlists()
    playlists = results['items']
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])
    return playlists

#helper function to randomly pick 50 playlists out of their library
def rand_select_playlists(all_playlists):
    num_to_select = min(50, len(all_playlists))
    random_playlists = random.sample(all_playlists, num_to_select)
    return random_playlists

#helper function to clear the old pr
def clear_old_playlist_rewind(sp, playlist_rewind_id):
    sp.playlist_replace_items(playlist_rewind_id, []) #clearing the playlist

#helper function to check if pr already exists
def pr_exist_check(sp, user_id, all_playlists):
    pr_id = None
    #out of all playlists, see if already exists
    for playlist in all_playlists:
        if (playlist['name'] == "Playlist Rewind"): #if we found one, clear it
            pr_id = playlist['id']
            clear_old_playlist_rewind(sp, pr_id)

    if not pr_id: # if we didn't find playlist rewind, create one
        new_playlist = sp.user_playlist_create(user_id, 'Playlist Rewind', public= True)
        pr_id = new_playlist['id']
    return pr_id

#helper function to add rand tracks to pr playlist
def add_tracks(sp, song_uris, user_id, pr_id, rand_playlists):
    
    for playlist in rand_playlists:
        playlist_id = playlist['id']
        total_num_of_tracks = playlist['tracks']['total']

        if total_num_of_tracks > 0: #if the playlist has at least one track
            random_index = random.randint(0, total_num_of_tracks - 1)
            response = sp.playlist_tracks(playlist_id, limit= 1, offset= random_index) #choosing a random track from the playlist
            items = response.get('items', [])

            if items:
                track = items[0].get('track')
                if track and track.get('uri'):
                    song_uris.append(track['uri'])
            else:
                print("Playlist does not have any tracks")

        else:
            print("Playlist does not have any tracks")

    if not song_uris:
        return 0
    else:
        sp.user_playlist_add_tracks(user_id, pr_id, song_uris)
        return 1


#saving the new playlist to the logged in user's profile
@app.route('/savePlaylistRewind')
def save_playlist_rewind():

    try: #making sure the user is logged in
        token_info = get_token()
    except:
        print("User not logged in!")
        return redirect('/')
    
    #getting auth token, user id from user that is logged in
    sp = spotipy.Spotify(auth= token_info['access_token'], requests_timeout=20)
    user_id = sp.current_user()['id']
    song_uris = []

    #want to randomize all the playlists within their library, and only pick out 50 of them
    all_playlists = get_all_playlists(sp)
    rand_playlists = rand_select_playlists(all_playlists)

    pr_id = pr_exist_check(sp, user_id, all_playlists) #checking if pr exists, if not, create one
    result = add_tracks(sp, song_uris, user_id, pr_id, rand_playlists) #add in random tracks from the rand playlists

    if result == 1:
        return "Success"
    else:
        return "Failure"

def get_token():
    token_info = session.get(TOKEN_INFO, None) #retrieving the token

    #need a refresh token incase the token expires or does not exist
    if not token_info:
        return redirect(url_for('login', external= False))

    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info)
    return token_info

def create_spotify_oauth(show_dialog=False):
    return SpotifyOAuth(client_id= config.client_id,
                        client_secret= config.client_secret,
                        redirect_uri= url_for('redirect_page', _external= True),
                        scope= 'user-library-read playlist-modify-public playlist-modify-private',
                        show_dialog=show_dialog
                        )

app.run(debug=True)