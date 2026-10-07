#!/usr/bin/env python3
"""
Simple test to add a few Apple Music tracks to Spotify Liked Songs
Uses direct API calls to bypass the auth flow issues
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings


def simple_test_liked():
    """Simple test with just 5 tracks"""
    print("🧪 SIMPLE TEST: Add 5 Apple Music Tracks to Spotify Liked Songs")
    print("=" * 60)

    # Get first 5 tracks from Apple Music
    print("📤 Getting first 5 tracks from Apple Music...")
    applescript = '''
    tell application "Music"
        try
            set trackList to {}
            repeat with i from 1 to 5
                try
                    set t to track i of library playlist 1
                    set trackInfo to (name of t) & "|" & (artist of t) & "|" & (album of t)
                    set end of trackList to trackInfo
                end try
            end repeat

            set AppleScript's text item delimiters to "~~~"
            set result to trackList as string
            set AppleScript's text item delimiters to ""
            return result
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and result.stdout.strip():
            tracks = []
            for track_info in result.stdout.strip().split("~~~"):
                if "|" in track_info:
                    parts = track_info.split("|")
                    if len(parts) >= 3:
                        tracks.append({
                            "title": parts[0].strip(),
                            "artist": parts[1].strip(),
                            "album": parts[2].strip()
                        })

            print(f"✅ Found {len(tracks)} tracks")
            for i, track in enumerate(tracks, 1):
                print(f"  {i}. {track['artist']} - {track['title']}")

            if not tracks:
                print("❌ No tracks found")
                return

            # Try connecting to Spotify
            print(f"\n🎵 Connecting to Spotify...")
            settings = Settings.load()

            try:
                spotify = SpotifyClient(settings)
                user = spotify.sp.current_user()
                print(f"✅ Connected as: {user['display_name']}")

                # Get current liked count
                liked_info = spotify.sp.current_user_saved_tracks(limit=1)
                initial_count = liked_info['total']
                print(f"📊 Current Liked Songs: {initial_count:,}")

                print(f"\n🔍 Searching and adding tracks...")
                added_count = 0

                for i, track in enumerate(tracks, 1):
                    try:
                        # Search for track
                        query = f'artist:"{track["artist"]}" track:"{track["title"]}"'
                        print(f"\n[{i}/5] Searching: {track['artist']} - {track['title']}")

                        results = spotify.sp.search(q=query, type='track', limit=1)

                        if results['tracks']['items']:
                            spotify_track = results['tracks']['items'][0]
                            track_id = spotify_track['id']
                            spotify_name = f"{spotify_track['artists'][0]['name']} - {spotify_track['name']}"
                            print(f"  ✅ Found: {spotify_name}")

                            # Check if already liked
                            is_liked = spotify.sp.current_user_saved_tracks_contains([track_id])[0]

                            if not is_liked:
                                # Add to liked songs
                                print(f"  💖 Adding to Liked Songs...")
                                spotify.sp.current_user_saved_tracks_add([track_id])
                                added_count += 1
                                print(f"  ✅ Successfully added!")
                            else:
                                print(f"  ℹ️ Already in Liked Songs")

                        else:
                            print(f"  ❌ Not found on Spotify")

                        time.sleep(0.5)  # Be gentle with API

                    except Exception as e:
                        print(f"  ❌ Error processing track: {e}")

                # Final check
                final_liked = spotify.sp.current_user_saved_tracks(limit=1)
                final_count = final_liked['total']

                print(f"\n🎉 TEST COMPLETE!")
                print(f"=" * 30)
                print(f"📊 Results:")
                print(f"   Tracks processed: {len(tracks)}")
                print(f"   Successfully added: {added_count}")
                print(f"   Liked Songs before: {initial_count:,}")
                print(f"   Liked Songs after: {final_count:,}")
                print(f"   Increase: +{final_count - initial_count}")

                if added_count > 0:
                    print(f"\n✅ SUCCESS! The migration is working correctly!")
                    print(f"🚀 Ready to run full migration: migrate_library_to_liked_fixed.py")
                else:
                    print(f"\n⚠️ No new tracks were added (may already be in your library)")

            except Exception as e:
                print(f"❌ Spotify connection failed: {e}")
                # The error might give us a clue about the auth issue
                print(f"🔧 You may need to complete the OAuth flow manually")

        else:
            print(f"❌ AppleScript failed: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    simple_test_liked()