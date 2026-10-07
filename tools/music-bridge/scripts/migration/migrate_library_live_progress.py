#!/usr/bin/env python3
"""
Apple Music library to Spotify Liked Songs migration with live progress
Shows progress as it happens and adds songs immediately
"""

import subprocess
import sys
import time
from pathlib import Path

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings


def migrate_library_live_progress():
    """Migrate with live progress updates"""
    print("💖 Apple Music Library → Spotify Liked Songs (Live Progress)")
    print("=" * 65)

    # Get total count
    print("📊 Getting Apple Music library size...")
    try:
        count_result = subprocess.run(
            ['osascript', '-e', 'tell application "Music" to get count of tracks of library playlist 1'],
            capture_output=True,
            text=True,
            timeout=30
        )
        total_tracks = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0
        print(f"✅ Your Apple Music library: {total_tracks:,} tracks")
    except Exception as e:
        print(f"❌ Could not get library size: {e}")
        return

    # Connect to Spotify
    print("\n🎵 Connecting to Spotify...")
    settings = Settings.load()
    spotify = SpotifyClient(settings)

    user = spotify.sp.current_user()
    liked_initial = spotify.sp.current_user_saved_tracks(limit=1)
    initial_count = liked_initial['total']

    print(f"✅ Connected as: {user['display_name']}")
    print(f"📊 Current Spotify Liked Songs: {initial_count:,}")
    print(f"\n🚀 Starting migration of {total_tracks:,} tracks...")
    print("📈 You'll see progress updates in real-time!")

    # Process in very small batches with immediate feedback
    batch_size = 5  # Very small for quick feedback
    total_added = 0
    total_already_liked = 0
    total_failed = 0

    for batch_start in range(1, total_tracks + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, total_tracks)
        batch_num = ((batch_start - 1) // batch_size) + 1
        total_batches = ((total_tracks - 1) // batch_size) + 1

        print(f"\n🔄 Batch {batch_num}/{total_batches}: Tracks {batch_start}-{batch_end}")

        # Get tracks from Apple Music
        applescript = f'''
        tell application "Music"
            try
                set trackList to {{}}
                repeat with i from {batch_start} to {batch_end}
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
                timeout=15  # Short timeout for small batches
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse tracks
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

                print(f"  📤 Extracted {len(batch_tracks)} tracks")

                # Process each track immediately
                batch_added = 0
                batch_already = 0
                batch_failed = 0

                for i, track in enumerate(batch_tracks, 1):
                    track_display = f"{track['artist']} - {track['title']}"

                    try:
                        # Search on Spotify
                        query = f'artist:"{track["artist"]}" track:"{track["title"]}"'
                        results = spotify.sp.search(q=query, type='track', limit=1)

                        if results['tracks']['items']:
                            spotify_track = results['tracks']['items'][0]
                            track_id = spotify_track['id']
                            spotify_display = f"{spotify_track['artists'][0]['name']} - {spotify_track['name']}"

                            # Check if already liked
                            is_liked = spotify.sp.current_user_saved_tracks_contains([track_id])[0]

                            if not is_liked:
                                # Add to Liked Songs
                                spotify.sp.current_user_saved_tracks_add([track_id])
                                batch_added += 1
                                total_added += 1
                                print(f"    💖 Added: {spotify_display}")
                            else:
                                batch_already += 1
                                total_already_liked += 1
                                print(f"    ℹ️ Already liked: {spotify_display}")
                        else:
                            batch_failed += 1
                            total_failed += 1
                            print(f"    ❌ Not found: {track_display}")

                        # Small delay to be nice to APIs
                        time.sleep(0.1)

                    except Exception as e:
                        batch_failed += 1
                        total_failed += 1
                        print(f"    ❌ Error: {track_display} ({e})")

                # Batch summary
                processed = batch_start + len(batch_tracks) - 1
                print(f"  📊 Batch: +{batch_added} liked, {batch_already} already had, {batch_failed} failed")
                print(f"  📈 Total: {total_added} newly added, {total_already_liked} already had, {total_failed} failed")
                print(f"  📍 Progress: {processed:,}/{total_tracks:,} tracks processed")

                # Show current Spotify count every few batches
                if batch_num % 10 == 0:
                    current_liked = spotify.sp.current_user_saved_tracks(limit=1)
                    current_count = current_liked['total']
                    print(f"  🎵 Spotify Liked Songs now: {current_count:,} (started with {initial_count:,})")

                # Pause between batches
                time.sleep(1)

            else:
                print(f"  ❌ AppleScript failed for this batch")

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Batch timed out - skipping")
        except Exception as e:
            print(f"  ❌ Batch error: {e}")

    # Final results
    final_liked = spotify.sp.current_user_saved_tracks(limit=1)
    final_count = final_liked['total']
    net_increase = final_count - initial_count

    print(f"\n💖 MIGRATION COMPLETE!")
    print("=" * 40)
    print(f"📊 Results:")
    print(f"   Newly added to Liked Songs: {total_added:,}")
    print(f"   Already in Liked Songs: {total_already_liked:,}")
    print(f"   Could not find on Spotify: {total_failed:,}")
    print(f"   Spotify Liked Songs before: {initial_count:,}")
    print(f"   Spotify Liked Songs after: {final_count:,}")
    print(f"   Net increase: +{net_increase:,}")
    print(f"\n🎉 Check your Spotify Liked Songs - you should see the new additions!")


if __name__ == "__main__":
    migrate_library_live_progress()