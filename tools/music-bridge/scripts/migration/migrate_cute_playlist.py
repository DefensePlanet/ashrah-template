#!/usr/bin/env python3
"""
Migrate "this song is so cute" playlist from Apple Music to Spotify
Creates a new playlist on Spotify
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings


def migrate_cute_playlist():
    """Migrate the 'this song is so cute' playlist"""
    playlist_name = "this song is so cute"
    print(f"💖 Migrating '{playlist_name}' from Apple Music to Spotify")
    print("=" * 60)

    # Extract playlist tracks using simpler AppleScript
    print(f"📤 Extracting tracks from '{playlist_name}' playlist...")

    # First, get the track count
    try:
        count_script = f'''
        tell application "Music"
            try
                set targetPlaylist to playlist "{playlist_name}"
                return count of tracks of targetPlaylist
            on error
                return 0
            end try
        end tell
        '''

        count_result = subprocess.run(
            ['osascript', '-e', count_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if count_result.returncode == 0 and count_result.stdout.strip():
            track_count = int(count_result.stdout.strip())
            print(f"✅ Found playlist with {track_count} tracks")
        else:
            print(f"❌ Could not find playlist '{playlist_name}'")
            return

    except Exception as e:
        print(f"❌ Error getting track count: {e}")
        return

    if track_count == 0:
        print(f"❌ Playlist '{playlist_name}' is empty")
        return

    # Get tracks one by one (reliable method)
    tracks = []
    print(f"📤 Extracting {track_count} tracks...")

    for i in range(1, track_count + 1):
        try:
            track_script = f'''
            tell application "Music"
                try
                    set targetPlaylist to playlist "{playlist_name}"
                    set t to track {i} of targetPlaylist
                    return (name of t) & "|" & (artist of t) & "|" & (album of t)
                on error
                    return ""
                end try
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', track_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                track_info = result.stdout.strip()
                if "|" in track_info:
                    parts = track_info.split("|")
                    if len(parts) >= 3:
                        track = {
                            "title": parts[0].strip(),
                            "artist": parts[1].strip(),
                            "album": parts[2].strip()
                        }
                        tracks.append(track)
                        print(f"  ✅ Track {i}: {track['artist']} - {track['title']}")
                    else:
                        print(f"  ❌ Track {i}: Malformed data")
                else:
                    print(f"  ❌ Track {i}: No separator found")
            else:
                print(f"  ❌ Track {i}: AppleScript failed")

        except Exception as e:
            print(f"  ❌ Track {i}: Error: {e}")

    print(f"\n✅ Successfully extracted {len(tracks)} tracks")

    if not tracks:
        print("❌ No tracks extracted")
        return

    # Connect to Spotify
    print(f"\n🎵 Connecting to Spotify...")
    settings = Settings.load()
    spotify = SpotifyClient(settings)

    user = spotify.sp.current_user()
    print(f"✅ Connected as: {user['display_name']}")

    # Create new playlist on Spotify
    print(f"\n📋 Creating playlist '{playlist_name}' on Spotify...")
    try:
        spotify_playlist = spotify.sp.user_playlist_create(
            user=user['id'],
            name=playlist_name,
            public=False,
            description=f"Migrated from Apple Music • {len(tracks)} tracks"
        )
        playlist_id = spotify_playlist['id']
        print(f"✅ Created Spotify playlist: {spotify_playlist['external_urls']['spotify']}")
    except Exception as e:
        print(f"❌ Error creating playlist: {e}")
        return

    # Process tracks and add to playlist
    print(f"\n🔍 Processing {len(tracks)} tracks...")

    found_track_ids = []
    added_count = 0
    failed_count = 0

    for i, track in enumerate(tracks, 1):
        track_display = f"{track['artist']} - {track['title']}"
        print(f"\n[{i}/{len(tracks)}] Processing: {track_display}")

        try:
            # Search on Spotify
            query = f'artist:"{track["artist"]}" track:"{track["title"]}"'
            results = spotify.sp.search(q=query, type='track', limit=1)

            if results['tracks']['items']:
                spotify_track = results['tracks']['items'][0]
                track_id = spotify_track['id']
                spotify_display = f"{spotify_track['artists'][0]['name']} - {spotify_track['name']}"
                print(f"  ✅ Found: {spotify_display}")

                found_track_ids.append(track_id)
                added_count += 1
            else:
                failed_count += 1
                print(f"  ❌ Not found on Spotify")

            time.sleep(0.1)  # Be gentle with API

        except Exception as e:
            failed_count += 1
            print(f"  ❌ Error: {e}")

    # Add all found tracks to the playlist
    if found_track_ids:
        print(f"\n📋 Adding {len(found_track_ids)} tracks to Spotify playlist...")
        try:
            # Add tracks in batches of 100 (Spotify limit)
            batch_size = 100
            for i in range(0, len(found_track_ids), batch_size):
                batch = found_track_ids[i:i + batch_size]
                spotify.sp.playlist_add_items(playlist_id, batch)
                print(f"  ✅ Added batch of {len(batch)} tracks")
                time.sleep(1)

            print(f"✅ Successfully added all {len(found_track_ids)} tracks to playlist!")
        except Exception as e:
            print(f"❌ Error adding tracks to playlist: {e}")

    # Final summary
    print(f"\n💖 PLAYLIST MIGRATION COMPLETE!")
    print("=" * 40)
    print(f"📊 Results:")
    print(f"   Playlist: {playlist_name}")
    print(f"   Total tracks: {len(tracks)}")
    print(f"   Found on Spotify: {added_count}")
    print(f"   Not found: {failed_count}")
    print(f"   Success rate: {(added_count/len(tracks)*100):.1f}%")
    print(f"\n🎵 Playlist URL: {spotify_playlist['external_urls']['spotify']}")
    print(f"🎉 Check your Spotify playlists!")


if __name__ == "__main__":
    migrate_cute_playlist()