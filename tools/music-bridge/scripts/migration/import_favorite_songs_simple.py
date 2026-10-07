#!/usr/bin/env python3
"""
Import Favorite Songs using the same approach as Charles Wesley Godwin
"""

import subprocess
import sys
from pathlib import Path

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings


def import_favorite_songs_simple():
    """Import Favorite Songs using simple AppleScript approach like Charles Wesley Godwin"""
    print("⭐ Importing Apple Music Favorite Songs to Spotify")
    print("=" * 60)

    # First get the count
    try:
        count_result = subprocess.run(
            ['osascript', '-e', 'tell application "Music" to get count of tracks of playlist "Favorite Songs"'],
            capture_output=True,
            text=True,
            timeout=10
        )
        total_tracks = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0
        print(f"📊 Favorite Songs contains {total_tracks} tracks")
    except:
        print("❌ Could not get track count")
        return

    if total_tracks == 0:
        print("❌ No tracks found in Favorite Songs")
        return

    print("📤 Getting tracks from Apple Music Favorite Songs...")

    # Export in batches to avoid timeouts
    all_tracks = []
    batch_size = 100

    for batch_start in range(1, total_tracks + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, total_tracks)
        print(f"🔄 Exporting tracks {batch_start}-{batch_end}...")

        applescript = f'''
        tell application "Music"
            try
                set favoritePlaylist to playlist "Favorite Songs"
                set trackList to {{}}

                repeat with i from {batch_start} to {batch_end}
                    try
                        set t to track i of favoritePlaylist
                        set trackInfo to (name of t) & "|" & (artist of t) & "|" & (album of t)
                        set end of trackList to trackInfo
                    end try
                end repeat

                set AppleScript's text item delimiters to "~~~"
                set result to trackList as string
                set AppleScript's text item delimiters to ""
                return result
            on error
                return ""
            end try
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and result.stdout.strip():
                batch_tracks = []
                for track_info in result.stdout.strip().split("~~~"):
                    if "|" in track_info:
                        parts = track_info.split("|")
                        if len(parts) >= 3:
                            batch_tracks.append({
                                "title": parts[0].strip(),
                                "artist": parts[1].strip(),
                                "album": parts[2].strip()
                            })

                all_tracks.extend(batch_tracks)
                print(f"  ✅ Exported {len(batch_tracks)} tracks")
            else:
                print(f"  ⚠️ Batch failed")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"✅ Found {len(all_tracks)} favorite songs")

    if not all_tracks:
        print("❌ No tracks exported")
        return

    # Initialize Spotify
    settings = Settings.load()
    spotify = SpotifyClient(settings)

    playlist_name = "Favorite Songs (from Apple Music)"

    # Delete existing playlist if it exists
    try:
        user_playlists = spotify.sp.current_user_playlists(limit=50)
        for existing in user_playlists['items']:
            if existing['name'] == playlist_name:
                spotify.sp.user_playlist_unfollow(spotify.sp.me()['id'], existing['id'])
                print(f"🗑️ Deleted existing playlist")
                break
    except Exception as e:
        print(f"⚠️ Error checking existing playlists: {e}")

    # Create new playlist
    new_playlist = spotify.sp.user_playlist_create(
        spotify.sp.me()['id'],
        playlist_name,
        public=False,
        description="Your favorite songs imported from Apple Music"
    )
    print(f"✅ Created Spotify playlist: {playlist_name}")

    # Add tracks
    added = 0
    failed = 0
    track_ids = []

    for i, track in enumerate(all_tracks, 1):
        print(f"🔍 [{i}/{len(all_tracks)}] Searching: {track['artist']} - {track['title']}")

        try:
            # Search with quotes for better matching
            query = f'artist:"{track["artist"]}" track:"{track["title"]}"'
            results = spotify.sp.search(q=query, type='track', limit=1)

            if results['tracks']['items']:
                spotify_track = results['tracks']['items'][0]
                track_ids.append(spotify_track['id'])
                added += 1
                print(f"  ✅ Found: {spotify_track['artists'][0]['name']} - {spotify_track['name']}")

                # Add in batches of 100
                if len(track_ids) >= 100:
                    spotify.sp.user_playlist_add_tracks(
                        spotify.sp.me()['id'],
                        new_playlist['id'],
                        track_ids
                    )
                    track_ids = []
                    print(f"  📦 Added batch to playlist ({added} total so far)")

            else:
                failed += 1
                print(f"  ❌ Not found in Spotify")

        except Exception as e:
            failed += 1
            print(f"  ❌ Search error: {e}")

    # Add remaining tracks
    if track_ids:
        spotify.sp.user_playlist_add_tracks(
            spotify.sp.me()['id'],
            new_playlist['id'],
            track_ids
        )

    success_rate = (added / len(all_tracks)) * 100
    print(f"\n⭐ FAVORITE SONGS IMPORT COMPLETE")
    print(f"   Total tracks: {len(all_tracks)}")
    print(f"   Successfully added: {added}")
    print(f"   Failed: {failed}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"\n🎵 Your '{playlist_name}' playlist is now available in Spotify!")


if __name__ == "__main__":
    import_favorite_songs_simple()