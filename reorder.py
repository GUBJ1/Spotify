import spotipy
import time
import random
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv         import load_dotenv

#from info import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE

load_dotenv()
print("CLIENT_ID set:", (os.getenv("CLIENT_ID")))
print("CLIENT_SECRET set:", (os.getenv("CLIENT_SECRET")))
print("REDIRECT_URI:", os.getenv("REDIRECT_URI"))

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id= os.getenv("CLIENT_ID"),
    client_secret= os.getenv("CLIENT_SECRET"),
    redirect_uri= os.getenv("REDIRECT_URI"),
    scope= os.getenv("SCOPE")
))

def safe_add_items(playlist_id, uris):
    while True:
        try:
            sp.playlist_add_items(playlist_id, uris)
            break
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 5))
                print(f"Rate limited. Väntar {retry_after} sekunder...")
                time.sleep(retry_after)
            else:
                print(f"Fel vid tillägg: {e}")
                break

def safe_remove_items(playlist_id, uris):
    for i in range(0, len(uris), 100):
        batch = uris[i:i + 100]
        try:
            sp.playlist_remove_all_occurrences_of_items(playlist_id, batch)
        except spotipy.exceptions.SpotifyException as e:
            print(f"Fel vid borttagning: {e}")

# Hämta användare och spellistor
user_id = sp.current_user()['id']
playlists = sp.current_user_playlists()
own_playlists = [p for p in playlists['items'] if p['owner']['id'] == user_id]

print("Dina skapade spellistor:")
for i, playlist in enumerate(own_playlists):
    print(f"{i}: {playlist['name']}")

val = int(input("Ange numret på spellistan du vill sortera: "))
playlist_id = own_playlists[val]['id']
playlist_name = own_playlists[val]['name']

# Hämta alla låtar med paginering
tracks = []
results = sp.playlist_tracks(playlist_id)
tracks.extend(results['items'])

while results['next']:
    results = sp.next(results)
    tracks.extend(results['items'])

print(f"Hämtade {len(tracks)} låtar.")

# Sorteringsval
print("Sortera efter:")
print("1: Artist")
print("2: Release date")
print("3: Slumpa ordningen")
choice = input("Ange 1, 2 eller 3: ")

reverse = False
if choice in ["1", "2"]:
    print("Sorteringsordning:")
    print("1: Stigande (äldst / A→Ö)")
    print("2: Fallande (nyast / Ö→A)")
    order = input("Ange 1 eller 2: ")
    reverse = True if order == "2" else False

# Sorteringslogik
def get_release_date(item):
    date_str = item['track']['album']['release_date']
    parts = date_str.split('-')
    while len(parts) < 3:
        parts.append('00')
    return int("".join(parts))

if choice == "1":
    # Artist, albumdatum, låttitel
    sorted_tracks = sorted(
        tracks,
        key=lambda item: (
            item['track']['artists'][0]['name'].lower(),
            get_release_date(item),
            item['track']['name'].lower()
        ),
        reverse=reverse
    )
elif choice == "2":
    sorted_tracks = sorted(tracks, key=get_release_date, reverse=reverse)
elif choice == "3":
    sorted_tracks = tracks[:]
    random.shuffle(sorted_tracks)
else:
    print("Ogiltigt val. Sorterar efter artistnamn som standard.")
    sorted_tracks = sorted(
        tracks,
        key=lambda item: (
            item['track']['artists'][0]['name'].lower(),
            get_release_date(item),
            item['track']['name'].lower()
        )
    )

# Val: sortera om eller skapa ny spellista
print("\nVad vill du göra med den sorterade listan?")
print("1: Sortera om den befintliga spellistan")
print("2: Skapa en ny sorterad kopia")
action = input("Ange 1 eller 2: ")

batch_size = 100
if action == "1":
    print("Sorterar om befintlig spellista...")

    uris_to_remove = [item['track']['uri'] for item in tracks]
    print("Tar bort låtar...")
    safe_remove_items(playlist_id, uris_to_remove)

    print("Lägger till låtar i ny ordning...")
    for i in range(0, len(sorted_tracks), batch_size):
        batch_uris = [item['track']['uri'] for item in sorted_tracks[i:i+batch_size]]
        safe_add_items(playlist_id, batch_uris)

    print("Den befintliga spellistan har sorterats om!")

elif action == "2":
    new_name = f"{playlist_name} (sorterad)"
    new_playlist = sp.user_playlist_create(user_id, name=new_name, public=False)
    print(f"Skapar ny spellista: {new_name}")

    for i in range(0, len(sorted_tracks), batch_size):
        batch_uris = [item['track']['uri'] for item in sorted_tracks[i:i+batch_size]]
        safe_add_items(new_playlist['id'], batch_uris)

    print("Ny sorterad spellista skapad!")

else:
    print("Ogiltigt val. Inga ändringar har gjorts.")
