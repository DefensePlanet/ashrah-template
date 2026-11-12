#!/usr/bin/env python3
"""
Quick test to add a single known song to Spotify Liked Songs
"""

import sys
from pathlib import Path

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings


def test_add_single_song():
    """Test adding a single song to verify our auth works"""
    print("🧪 Quick Test: Add Single Song to Spotify Liked Songs")
    print("=" * 55)

    try:
        # Connect to Spotify
        settings = Settings.load()
        spotify = SpotifyClient(settings)

        # Get current user info
        user = spotify.sp.current_user()
        print(f"✅ Connected as: {user['display_name']}")

        # Get current liked songs count
        liked_before = spotify.sp.current_user_saved_tracks(limit=1)
        count_before = liked_before['total']
        print(f"📊 Current Liked Songs: {count_before:,}")

        # Search for a well-known song to test with
        print(f"\n🔍 Searching for a test song...")
        test_query = 'track:"Shape of You" artist:"Ed Sheeran"'
        results = spotify.sp.search(q=test_query, type='track', limit=1)

        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            track_id = track['id']
            track_name = f"{track['artists'][0]['name']} - {track['name']}"
            print(f"✅ Found: {track_name}")

            # Check if already liked
            is_liked = spotify.sp.current_user_saved_tracks_contains([track_id])[0]
            print(f"💖 Already liked: {is_liked}")

            if not is_liked:
                # Try to add it
                print(f"🔄 Adding to Liked Songs...")
                spotify.sp.current_user_saved_tracks_add([track_id])
                print(f"✅ Successfully added!")

                # Verify it was added
                print(f"🔍 Verifying addition...")
                import time
                time.sleep(2)  # Give Spotify a moment to update

                # Check count again
                liked_after = spotify.sp.current_user_saved_tracks(limit=1)
                count_after = liked_after['total']

                # Check if this specific track is now liked
                is_now_liked = spotify.sp.current_user_saved_tracks_contains([track_id])[0]

                print(f"📊 Results:")
                print(f"   Before: {count_before:,} liked songs")
                print(f"   After: {count_after:,} liked songs")
                print(f"   Increase: +{count_after - count_before}")
                print(f"   Test track now liked: {is_now_liked}")

                if is_now_liked and count_after > count_before:
                    print(f"\n🎉 SUCCESS! Authentication and Liked Songs API is working!")
                    return True
                else:
                    print(f"\n❌ Something went wrong - track wasn't properly added")
                    return False
            else:
                print(f"\n⚠️ Test song already in your Liked Songs")
                print(f"✅ But this confirms our authentication works!")
                return True

        else:
            print(f"❌ Could not find test song")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_add_single_song()
    if success:
        print(f"\n🚀 Authentication confirmed - ready for full migration!")
    else:
        print(f"\n⚠️ There may be an authentication issue")