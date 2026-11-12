#!/usr/bin/env python3
"""
Execute the full Apple Music to Spotify migration
"""

import subprocess
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add the package to path
sys.path.append(str(Path(__file__).parent))

from ty_music_bridge.models import Track
from ty_music_bridge.spotify_client import SpotifyClient
from ty_music_bridge.config import Settings
from ty_music_bridge.log import logger


class FullMigrationExecutor:
    """Execute the complete migration with progress tracking"""

    def __init__(self):
        self.settings = Settings.load()
        self.spotify = SpotifyClient(self.settings)
        self.migration_log = []
        self.start_time = datetime.now()

    def log_progress(self, message: str, level: str = "info"):
        """Log migration progress"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.migration_log.append({"time": timestamp, "message": message, "level": level})

    def get_filtered_playlists(self):
        """Get all playlists excluding test playlists"""
        self.log_progress("🔍 Scanning Apple Music playlists...")

        test_playlist_patterns = [
            'applescript-sync-test', 'spotify-sync-test', 'test-sync-from-spotify',
            'tymusicbridge-test', 'enhanced-sync-test', 'enhanced-test-final'
        ]

        # Get total count
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Music" to get count of user playlists'],
                capture_output=True, text=True, timeout=10
            )
            total_count = int(result.stdout.strip()) if result.returncode == 0 else 0
        except:
            total_count = 50

        playlists = []
        for i in range(1, total_count + 1):
            try:
                # Get playlist name
                name_result = subprocess.run(
                    ['osascript', '-e', f'tell application "Music" to get name of user playlist {i}'],
                    capture_output=True, text=True, timeout=3
                )

                if name_result.returncode == 0:
                    playlist_name = name_result.stdout.strip()

                    # Skip test playlists
                    is_test_playlist = any(pattern in playlist_name.lower() for pattern in test_playlist_patterns)
                    if is_test_playlist:
                        self.log_progress(f"  ❌ SKIPPING: {playlist_name} (test playlist)")
                        continue

                    # Get track count
                    count_result = subprocess.run(
                        ['osascript', '-e', f'tell application "Music" to get count of tracks of user playlist {i}'],
                        capture_output=True, text=True, timeout=3
                    )
                    track_count = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

                    playlists.append({
                        'index': i,
                        'name': playlist_name,
                        'track_count': track_count,
                        'is_favorites': playlist_name.lower() in ['favorite songs', 'favorites', 'liked']
                    })

                    self.log_progress(f"  ✅ FOUND: {playlist_name} ({track_count} tracks)")

            except Exception as e:
                self.log_progress(f"  ⚠️ Error reading playlist {i}: {e}", "warning")

        return playlists

    def export_apple_playlist(self, playlist_index: int, playlist_name: str) -> List[Track]:
        """Export tracks from Apple Music playlist"""
        self.log_progress(f"📤 Exporting: {playlist_name}")

        applescript = f'''
        tell application "Music"
            try
                set targetPlaylist to user playlist {playlist_index}
                set trackList to {{}}

                repeat with t in tracks of targetPlaylist
                    try
                        set trackInfo to (name of t) & "|" & (artist of t) & "|" & (album of t)
                        set end of trackList to trackInfo
                    end try
                end repeat

                set AppleScript's text item delimiters to "~~~"
                set result to trackList as string
                set AppleScript's text item delimiters to ""
                return result
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0 and not result.stdout.startswith("ERROR:"):
                tracks = []
                track_data = result.stdout.strip()
                if track_data:
                    for track_info in track_data.split("~~~"):
                        if "|" in track_info:
                            parts = track_info.split("|")
                            if len(parts) >= 3:
                                tracks.append(Track(
                                    title=parts[0].strip(),
                                    artist=parts[1].strip(),
                                    album=parts[2].strip(),
                                    isrc=None
                                ))

                self.log_progress(f"  ✅ Exported {len(tracks)} tracks")
                return tracks
            else:
                self.log_progress(f"  ❌ Export failed: {result.stdout}", "error")
                return []

        except Exception as e:
            self.log_progress(f"  ❌ Export error: {e}", "error")
            return []

    def migrate_to_spotify_liked(self, tracks: List[Track]) -> dict:
        """Migrate to Spotify Liked Songs"""
        self.log_progress(f"💖 Migrating {len(tracks)} tracks to Spotify Liked Songs")

        added = 0
        failed = 0

        for i, track in enumerate(tracks, 1):
            if i % 50 == 0:  # Progress update every 50 tracks
                self.log_progress(f"  💖 Progress: {i}/{len(tracks)} liked songs processed")

            try:
                # Search Spotify
                query = f'artist:"{track.artist}" track:"{track.title}"'
                results = self.spotify.sp.search(q=query, type='track', limit=1)

                if results['tracks']['items']:
                    spotify_track = results['tracks']['items'][0]
                    self.spotify.sp.current_user_saved_tracks_add([spotify_track['id']])
                    added += 1
                    if i <= 10:  # Show first 10 for detail
                        self.log_progress(f"    💖 Liked: {track.artist} - {track.title}")
                else:
                    failed += 1
                    if failed <= 5:  # Show first 5 failures
                        self.log_progress(f"    ❌ Not found: {track.artist} - {track.title}")

            except Exception as e:
                failed += 1
                if failed <= 3:
                    self.log_progress(f"    ❌ Error: {track.artist} - {track.title} ({e})")

        success_rate = (added / len(tracks)) * 100 if tracks else 0
        self.log_progress(f"  💖 Liked Songs: {added}/{len(tracks)} added ({success_rate:.1f}% success)")

        return {
            'name': 'Liked Songs',
            'total': len(tracks),
            'added': added,
            'failed': failed,
            'success_rate': success_rate
        }

    def migrate_to_spotify_playlist(self, playlist_name: str, tracks: List[Track]) -> dict:
        """Migrate to Spotify playlist"""
        self.log_progress(f"📁 Creating Spotify playlist: {playlist_name}")

        try:
            # Delete existing playlist if it exists
            user_playlists = self.spotify.sp.current_user_playlists(limit=50)
            for existing in user_playlists['items']:
                if existing['name'] == playlist_name:
                    self.spotify.sp.user_playlist_unfollow(self.spotify.sp.me()['id'], existing['id'])
                    self.log_progress(f"  🗑️ Deleted existing playlist")
                    break

            # Create new playlist
            new_playlist = self.spotify.sp.user_playlist_create(
                self.spotify.sp.me()['id'],
                playlist_name,
                public=False,
                description=f"Migrated from Apple Music on {datetime.now().strftime('%Y-%m-%d')}"
            )

            added = 0
            failed = 0
            batch_size = 100  # Spotify API limit

            track_ids = []
            for i, track in enumerate(tracks, 1):
                try:
                    # Search Spotify
                    query = f'artist:"{track.artist}" track:"{track.title}"'
                    results = self.spotify.sp.search(q=query, type='track', limit=1)

                    if results['tracks']['items']:
                        track_ids.append(results['tracks']['items'][0]['id'])
                        added += 1
                    else:
                        failed += 1

                    # Add in batches
                    if len(track_ids) >= batch_size or i == len(tracks):
                        if track_ids:
                            self.spotify.sp.user_playlist_add_tracks(
                                self.spotify.sp.me()['id'],
                                new_playlist['id'],
                                track_ids
                            )
                            track_ids = []

                    # Progress update
                    if i % 100 == 0:
                        self.log_progress(f"  📁 Progress: {i}/{len(tracks)} tracks processed ({added} added)")

                except Exception as e:
                    failed += 1

            success_rate = (added / len(tracks)) * 100 if tracks else 0
            self.log_progress(f"  ✅ Playlist complete: {added}/{len(tracks)} tracks added ({success_rate:.1f}% success)")

            return {
                'name': playlist_name,
                'spotify_id': new_playlist['id'],
                'total': len(tracks),
                'added': added,
                'failed': failed,
                'success_rate': success_rate
            }

        except Exception as e:
            self.log_progress(f"  ❌ Failed to create playlist: {e}", "error")
            return {
                'name': playlist_name,
                'error': str(e),
                'total': len(tracks),
                'added': 0,
                'failed': len(tracks),
                'success_rate': 0
            }

    def execute_full_migration(self):
        """Execute the complete migration"""
        self.log_progress("🚀 STARTING FULL APPLE MUSIC → SPOTIFY MIGRATION")
        self.log_progress("=" * 60)

        # Get all playlists
        playlists = self.get_filtered_playlists()
        self.log_progress(f"📊 Found {len(playlists)} playlists to migrate")

        migration_results = []
        total_tracks = 0
        total_added = 0
        total_failed = 0

        for i, playlist in enumerate(playlists, 1):
            self.log_progress(f"\n🎵 [{i}/{len(playlists)}] PROCESSING: {playlist['name']}")

            # Export from Apple Music
            tracks = self.export_apple_playlist(playlist['index'], playlist['name'])
            total_tracks += len(tracks)

            if not tracks:
                self.log_progress(f"  ⚠️ Skipping empty playlist")
                continue

            # Migrate to Spotify
            if playlist['is_favorites']:
                result = self.migrate_to_spotify_liked(tracks)
            else:
                result = self.migrate_to_spotify_playlist(playlist['name'], tracks)

            migration_results.append(result)
            total_added += result.get('added', 0)
            total_failed += result.get('failed', 0)

            # Show running totals
            elapsed = datetime.now() - self.start_time
            self.log_progress(f"  ⏱️ Elapsed: {elapsed} | Total added: {total_added:,} | Failed: {total_failed:,}")

        # Final summary
        overall_success = (total_added / total_tracks) * 100 if total_tracks > 0 else 0
        total_elapsed = datetime.now() - self.start_time

        self.log_progress("\n" + "=" * 60)
        self.log_progress("🎉 MIGRATION COMPLETE!")
        self.log_progress("=" * 60)
        self.log_progress(f"📊 FINAL RESULTS:")
        self.log_progress(f"   Playlists processed: {len(playlists)}")
        self.log_progress(f"   Total tracks: {total_tracks:,}")
        self.log_progress(f"   Successfully migrated: {total_added:,}")
        self.log_progress(f"   Failed: {total_failed:,}")
        self.log_progress(f"   Overall success rate: {overall_success:.1f}%")
        self.log_progress(f"   Total time: {total_elapsed}")
        self.log_progress("🎵 Your Apple Music library has been migrated to Spotify!")

        return {
            'total_playlists': len(playlists),
            'total_tracks': total_tracks,
            'total_added': total_added,
            'total_failed': total_failed,
            'success_rate': overall_success,
            'duration': str(total_elapsed),
            'results': migration_results
        }


if __name__ == "__main__":
    executor = FullMigrationExecutor()
    executor.execute_full_migration()