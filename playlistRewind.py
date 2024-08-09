import spotipy
import time
import random
import config
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
    auth_url = create_spotify_oauth().get_authorize_url() #generates an auth url
    return redirect(auth_url) #sending user to the authorization url

#redirecting after logging in
@app.route('/redirect')
def redirect_page():
    session.clear() #makes sure user data that may be stored is all cleared
    code = request.args.get('code') #getting users auth code to use as the access token
    token_info = create_spotify_oauth().get_access_token(code) 
    session[TOKEN_INFO] = token_info #storing the token in our session
    return redirect(url_for('save_playlist_rewind', external= True))


#saving the new playlist to the logged in user's profile
@app.route('/savePlaylistRewind')
def save_playlist_rewind():

    try: #making sure the user is logged in
        token_info = get_token()
    except:
        print("User not logged in!")
        return redirect('/')
    
    #getting auth token, user id from user that is logged in
    sp = spotipy.Spotify(auth= token_info['access_token'])
    user_id = sp.current_user()['id']
    song_uris = []
    playlist_rewind_id = None

    current_playlists = sp.current_user_playlists()['items'] #getting list of user's playlists
    for playlist in current_playlists:

        playlist_id = playlist['id']

        if (playlist['name'] == "Playlist Rewind"): #if playlist rewind playlist already exists then we need to clear it to refresh everytime we run the function
            playlist_rewind_id = playlist_id
            sp.playlist_replace_items(playlist_rewind_id, []) #clearing the playlist
            continue

        total_num_of_tracks = playlist['tracks']['total']

        if total_num_of_tracks > 0: #if the playlist has at least one track
            random_index = random.randint(0, total_num_of_tracks - 1)
            rand_track = sp.playlist_tracks(playlist_id, limit= 1, offset= random_index)['items'][0] #choosing a random track from the playlist

            print('Saving ' + rand_track['track']['name'] + '...')
            track_uri = rand_track['track']['uri'] #saving that track's uri to insert later
            song_uris.append(track_uri)

        else:
            print("Playlist does not have any tracks")
        
    #if the user does not have a playlist rewind playlist already then we need to make one
    if not playlist_rewind_id:
        new_playlist = sp.user_playlist_create(user_id, 'Playlist Rewind', public= True)
        playlist_rewind_id = new_playlist['id']

    sp.user_playlist_add_tracks(user_id, playlist_rewind_id, song_uris)

    return "Success"



def get_token():
    token_info = session.get(TOKEN_INFO, None) #retrieving the token

    #need a refresh token incase the token expires or does not exist
    if not token_info:
        redirect(url_for('login', external= False))

    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info)
    return token_info



def create_spotify_oauth():
    return SpotifyOAuth(client_id= config.client_id,
                        client_secret= config.client_secret,
                        redirect_uri= url_for('redirect_page', _external= True),
                        scope= 'user-library-read playlist-modify-public playlist-modify-private'
                        )

app.run(debug=True)