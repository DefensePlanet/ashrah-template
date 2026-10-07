#!/usr/bin/env python3
"""CLI for ty-music-bridge"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import typer
from rich import print
from rich.console import Console
from rich.table import Table

from .config import Settings
from .spotify_client import SpotifyClient
from .apple_client import AppleClient
from .matching import resolve_to_apple_ids, resolve_to_spotify_ids
from .sync_engine import sync_one_way, sync_two_way
from .apple_applescript_client import resolve_to_apple_ids_applescript, AppleScriptMusicClient
from .store import Store
from .log import logger, set_debug
from .models import Track

app = typer.Typer(name="tymb", help="Two-way ISRC-first Apple Music ⇄ Spotify sync")
console = Console()


def dev_token_from_node(settings: Settings) -> str:
    """Generate Apple Developer Token using Node script"""
    env = os.environ.copy()
    env.update({
        "APPLE_TEAM_ID": settings.apple_team_id,
        "APPLE_KEY_ID": settings.apple_key_id,
        "APPLE_PRIVATE_KEY_PATH": str(settings.get_apple_private_key_path())
    })

    script_path = settings.repo_root / "scripts" / "gen_apple_dev_token.js"

    try:
        result = subprocess.run(
            ["node", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(settings.repo_root)
        )
        if result.returncode != 0:
            raise RuntimeError(f"Token generation failed: {result.stderr}")
        return result.stdout.strip()
    except FileNotFoundError:
        print("[red]Error: Node.js not found. Please install Node.js first.[/red]")
        print("Run: cd scripts && npm install")
        sys.exit(1)


# Export commands
@app.command("export-spotify")
def export_spotify(
    playlist: str = typer.Argument(..., help="Playlist name or ID"),
    out: Path = typer.Option("data/export_spotify.json", "--out", help="Output file path"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Export Spotify playlist tracks to JSON"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    sp = SpotifyClient(settings)

    try:
        playlist_id = sp.get_playlist_by_name_or_id(playlist)
        tracks = sp.export_playlist_tracks(playlist_id)

        # Save to file
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump([t.to_dict() for t in tracks], f, indent=2)

        print(f"[green]✅ Exported {len(tracks)} tracks to {out}[/green]")

    except Exception as e:
        print(f"[red]❌ Export failed: {e}[/red]")
        sys.exit(1)


@app.command("export-apple")
def export_apple(
    playlist: str = typer.Argument(..., help="Playlist name or ID"),
    out: Path = typer.Option("data/export_apple.json", "--out", help="Output file path"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Export Apple Music library playlist tracks to JSON"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    dev_token = dev_token_from_node(settings)
    am = AppleClient(settings, dev_token)

    try:
        tracks = am.export_library_playlist_items(playlist)

        # Save to file
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump([t.to_dict() for t in tracks], f, indent=2)

        print(f"[green]✅ Exported {len(tracks)} tracks to {out}[/green]")

    except Exception as e:
        print(f"[red]❌ Export failed: {e}[/red]")
        sys.exit(1)


# Import commands
@app.command("import-spotify")
def import_spotify(
    input_file: Path = typer.Option(..., "--in", help="Input JSON file"),
    target: str = typer.Option(..., "--target", help="Target playlist name"),
    public: bool = typer.Option(False, "--public", help="Make playlist public"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Import tracks to Spotify playlist"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    sp = SpotifyClient(settings)

    try:
        # Load tracks
        with open(input_file) as f:
            data = json.load(f)
        tracks = [Track.from_dict(d) for d in data]

        # Resolve to Spotify IDs
        matches = resolve_to_spotify_ids(sp, tracks)

        # Sync
        result = sync_one_way(sp, "spotify", target, matches, dry_run=dry_run, public=public)
        print(result.summary())

    except Exception as e:
        print(f"[red]❌ Import failed: {e}[/red]")
        sys.exit(1)


@app.command("import-apple")
def import_apple(
    input_file: Path = typer.Option(..., "--in", help="Input JSON file"),
    target: str = typer.Option(..., "--target", help="Target playlist name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Import tracks to Apple Music library playlist"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    dev_token = dev_token_from_node(settings)
    am = AppleClient(settings, dev_token)

    try:
        # Load tracks
        with open(input_file) as f:
            data = json.load(f)
        tracks = [Track.from_dict(d) for d in data]

        # Resolve to Apple catalog IDs
        matches = resolve_to_apple_ids(am, tracks, settings.apple_storefront)

        # Sync
        result = sync_one_way(am, "apple", target, matches, dry_run=dry_run)
        print(result.summary())

    except Exception as e:
        print(f"[red]❌ Import failed: {e}[/red]")
        sys.exit(1)


# Sync commands
@app.command("spotify-to-apple")
def sync_spotify_to_apple(
    src: str = typer.Option(..., "--src", help="Source Spotify playlist"),
    dst: str = typer.Option(..., "--dst", help="Destination Apple Music playlist"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Sync from Spotify to Apple Music"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    dev_token = dev_token_from_node(settings)
    sp = SpotifyClient(settings)
    am = AppleClient(settings, dev_token)

    try:
        # Export source
        src_id = sp.get_playlist_by_name_or_id(src)
        src_tracks = sp.export_playlist_tracks(src_id)

        # Resolve to Apple IDs
        resolved_ids = resolve_to_apple_ids(am, src_tracks, settings.apple_storefront)

        # Sync
        result = sync_one_way(am, "apple", dst, resolved_ids, dry_run=dry_run)
        print(result.summary())

        # Save to store
        if not dry_run:
            store = Store(settings)
            store.save_sync_history(
                "spotify-to-apple", src, dst,
                len(result.tracks_added),
                len(result.tracks_failed),
                dry_run
            )

    except Exception as e:
        print(f"[red]❌ Sync failed: {e}[/red]")
        sys.exit(1)


@app.command("apple-to-spotify")
def sync_apple_to_spotify(
    src: str = typer.Option(..., "--src", help="Source Apple Music playlist"),
    dst: str = typer.Option(..., "--dst", help="Destination Spotify playlist"),
    public: bool = typer.Option(False, "--public", help="Make Spotify playlist public"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Sync from Apple Music to Spotify"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    dev_token = dev_token_from_node(settings)
    sp = SpotifyClient(settings)
    am = AppleClient(settings, dev_token)

    try:
        # Export source
        src_tracks = am.export_library_playlist_items(src)

        # Resolve to Spotify IDs
        resolved_ids = resolve_to_spotify_ids(sp, src_tracks)

        # Sync
        result = sync_one_way(sp, "spotify", dst, resolved_ids, dry_run=dry_run, public=public)
        print(result.summary())

        # Save to store
        if not dry_run:
            store = Store(settings)
            store.save_sync_history(
                "apple-to-spotify", src, dst,
                len(result.tracks_added),
                len(result.tracks_failed),
                dry_run
            )

    except Exception as e:
        print(f"[red]❌ Sync failed: {e}[/red]")
        sys.exit(1)


@app.command("two-way")
def sync_two_way_cmd(
    a_name: str = typer.Option(..., "--a-name", help="Apple Music playlist name"),
    s_name: str = typer.Option(..., "--s-name", help="Spotify playlist name"),
    mode: str = typer.Option("union", "--mode", help="Sync mode: union, mirror-apple, mirror-spotify"),
    public: bool = typer.Option(False, "--public", help="Make Spotify playlist public"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Two-way sync between Apple Music and Spotify"""
    if debug:
        set_debug(True)

    if mode not in ["union", "mirror-apple", "mirror-spotify"]:
        print(f"[red]Invalid mode: {mode}[/red]")
        print("Valid modes: union, mirror-apple, mirror-spotify")
        sys.exit(1)

    settings = Settings.load()
    dev_token = dev_token_from_node(settings)
    sp = SpotifyClient(settings)
    am = AppleClient(settings, dev_token)

    try:
        result = sync_two_way(
            am, sp, a_name, s_name,
            mode=mode,
            dry_run=dry_run,
            public=public,
            storefront=settings.apple_storefront
        )
        print(result.summary())

        # Save to store
        if not dry_run:
            store = Store(settings)
            store.save_sync_history(
                f"two-way-{mode}", a_name, s_name,
                len(result.tracks_added),
                len(result.tracks_failed),
                dry_run
            )

    except Exception as e:
        print(f"[red]❌ Sync failed: {e}[/red]")
        sys.exit(1)


# Utility commands
@app.command("auth-spotify")
def auth_spotify():
    """Authenticate with Spotify (get tokens)"""
    settings = Settings.load()
    sp = SpotifyClient(settings)

    try:
        user = sp.sp.current_user()
        print(f"[green]✅ Authenticated as: {user['display_name']}[/green]")
        print(f"Tokens saved to: {settings.get_spotify_token_path()}")
    except Exception as e:
        print(f"[red]❌ Authentication failed: {e}[/red]")
        sys.exit(1)


@app.command("test-apple-token")
def test_apple_token():
    """Test Apple Developer Token generation"""
    settings = Settings.load()

    try:
        token = dev_token_from_node(settings)
        print("[green]✅ Token generated successfully[/green]")
        print(f"Token length: {len(token)} characters")
    except Exception as e:
        print(f"[red]❌ Token generation failed: {e}[/red]")
        sys.exit(1)


@app.command("export-cache")
def export_cache():
    """Export mapping cache to JSON"""
    settings = Settings.load()
    store = Store(settings)

    try:
        path = store.export_mappings()
        print(f"[green]✅ Exported cache to {path}[/green]")
    except Exception as e:
        print(f"[red]❌ Export failed: {e}[/red]")
        sys.exit(1)


# AppleScript-based commands (API alternative)
@app.command("spotify-to-apple-script")
def sync_spotify_to_apple_applescript(
    src: str = typer.Option(..., "--src", help="Source Spotify playlist"),
    dst: str = typer.Option(..., "--dst", help="Destination Apple Music playlist"),
    enhanced: bool = typer.Option(True, "--enhanced/--basic", help="Use enhanced multi-stage matching"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """Sync from Spotify to Apple Music using AppleScript (API alternative)"""
    if debug:
        set_debug(True)

    settings = Settings.load()
    sp = SpotifyClient(settings)

    try:
        matching_type = "Enhanced Multi-Stage" if enhanced else "Basic"
        print(f"🎵 {'[DRY RUN] ' if dry_run else ''}Syncing via AppleScript")
        print(f"   From Spotify: {src}")
        print(f"   To Apple Music: {dst}")
        print(f"   Matching: {matching_type}")
        print()

        # Export source
        src_id = sp.get_playlist_by_name_or_id(src)
        src_tracks = sp.export_playlist_tracks(src_id)

        print(f"📋 Loaded {len(src_tracks)} tracks from Spotify")

        # Use AppleScript to sync with enhanced matching option
        if enhanced:
            # Save temp export for enhanced matching
            import json
            temp_file = f"temp_export_{src_id}.json"
            with open(temp_file, 'w') as f:
                json.dump([t.to_dict() for t in src_tracks], f)

            # Use enhanced matching
            try:
                import sys
                sys.path.append(str(settings.repo_root))
                from enhanced_matching import enhanced_sync_test
                enhanced_sync_test(temp_file, dst, dry_run)
            except ImportError:
                print("[yellow]Enhanced matching not available, falling back to basic matching[/yellow]")
                results = resolve_to_apple_ids_applescript(src_tracks, dst, dry_run)
            finally:
                # Clean up temp file
                Path(temp_file).unlink(missing_ok=True)

            return
        else:
            # Use basic AppleScript matching
            results = resolve_to_apple_ids_applescript(src_tracks, dst, dry_run)

        # Summary
        matched = sum(1 for r in results if r.matched_id)
        failed = sum(1 for r in results if r.match_type == "failed")
        success_rate = (matched / len(results)) * 100 if results else 0

        print()
        print(f"📊 Sync Complete:")
        print(f"   Total tracks: {len(results)}")
        print(f"   {'Would be added' if dry_run else 'Added'}: {matched}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {success_rate:.1f}%")

        if failed > 0:
            print()
            print("❌ Failed tracks:")
            for result in results:
                if result.match_type == "failed":
                    print(f"   - {result.track.artist} - {result.track.title}")

    except Exception as e:
        print(f"[red]❌ Sync failed: {e}[/red]")
        sys.exit(1)


@app.command("list-apple-playlists")
def list_apple_playlists():
    """List Apple Music playlists using AppleScript"""
    client = AppleScriptMusicClient()

    try:
        playlists = client.get_library_playlists()

        print(f"🎵 Apple Music Playlists ({len(playlists)} total):")
        print("-" * 50)

        for i, playlist in enumerate(playlists, 1):
            print(f"{i:2d}. {playlist}")

    except Exception as e:
        print(f"[red]❌ Failed to get playlists: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()