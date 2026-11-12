#!/usr/bin/env python3
"""Voice Recording Pipeline — Main CLI entry point.

Processes voice recordings from Apple Watch apps (Just Press Record + Voice Memos)
into an organized iCloud Drive archive with transcription, categorization,
and denoising.

Usage:
    pipeline.py process [--limit N] [--source jpr|voice_memos] [--dry-run]
    pipeline.py watch [--foreground] [--once]
    pipeline.py status [--json]
    pipeline.py reprocess [--file PATH] [--failed] [--diarize]
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

# Ensure the tool directory is on the Python path
_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOL_DIR not in sys.path:
    sys.path.insert(0, _TOOL_DIR)

from config import load_config
from db import (
    get_connection,
    upsert_recording,
    get_unprocessed,
    update_status,
    increment_retry,
    mark_failed,
    recording_exists,
    get_recording,
    create_pipeline_run,
    finish_pipeline_run,
    get_stats,
)
from discovery import discover
from denoiser import denoise
from transcriber import Transcriber
from categorizer import categorize as classify_recording
from writer import write_output, tag_source_file
from diarizer import should_diarize, diarize, count_speakers

logger = logging.getLogger("voice-pipeline")

# Lazily initialized transcriber
_transcriber: Optional[Transcriber] = None


def _setup_logging(config: dict) -> None:
    """Configure logging based on config settings."""
    log_cfg = config.get("logging", {})
    log_path = log_cfg.get("path", "")
    log_level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stderr)]

    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def _get_transcriber(config: dict) -> Transcriber:
    """Get or create the lazy-loaded transcriber singleton."""
    global _transcriber
    if _transcriber is None:
        tc = config.get("transcriber", {})
        _transcriber = Transcriber(
            model=tc.get("model", "large-v3-turbo"),
            batch_size=12,
        )
    return _transcriber


def _find_ffprobe() -> Optional[str]:
    """Find ffprobe binary, checking common Homebrew paths."""
    import shutil
    candidates = [
        shutil.which("ffprobe"),
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _get_duration(filepath: str) -> float:
    """Get audio duration in seconds via ffprobe.

    Args:
        filepath: Path to audio file.

    Returns:
        Duration in seconds, or 0.0 if ffprobe fails.
    """
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return 0.0

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return 0.0

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        for stream in streams:
            if stream.get("codec_type") == "audio":
                duration = stream.get("duration")
                if duration:
                    return float(duration)

        # Fallback: try format-level duration
        fmt = data.get("format", {})
        duration = fmt.get("duration")
        if duration:
            return float(duration)

        return 0.0
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return 0.0


def _process_single(
    recording: dict,
    config: dict,
    conn,
    dry_run: bool = False,
) -> bool:
    """Process a single recording through the full pipeline.

    Steps:
    1. Get duration via ffprobe
    2. If <3s, mark ambient, skip to write
    3. Denoise
    4. Transcribe
    5. (Optional) Diarize
    6. Categorize
    7. Write output
    8. Finder tag source

    Args:
        recording: Recording dict from DB or discovery.
        config: Full pipeline config.
        conn: Database connection.
        dry_run: If True, only log what would happen.

    Returns:
        True if processing completed successfully.
    """
    source_path = recording["source_path"]
    max_retries = config.get("retry", {}).get("max_retries", 3)

    if not os.path.exists(source_path):
        logger.warning("Source file missing: %s", source_path)
        update_status(conn, source_path, "error", error_message="Source file missing")
        return False

    logger.info("Processing: %s", source_path)

    # Step 1: Get duration
    duration = _get_duration(source_path)
    if duration > 0:
        update_status(conn, source_path, recording.get("status", "discovered"),
                      duration_secs=duration)
    else:
        logger.warning("Could not determine duration for: %s", source_path)
        duration = 0.0

    # Step 2: Ambient pre-filter
    ambient_max = config.get("categorizer", {}).get("ambient_max_duration", 3.0)
    if 0 < duration < ambient_max:
        logger.info("Short recording (%.1fs) -- marking as ambient", duration)
        update_status(
            conn, source_path, "categorized",
            category="ambient",
            confidence=0.95,
            summary=f"Short recording ({duration:.1f}s)",
            duration_secs=duration,
        )
        # Write output for ambient too
        rec = get_recording(conn, source_path)
        if rec and not dry_run:
            output_dir = write_output(rec, config)
            if output_dir:
                update_status(conn, source_path, "written", output_dir=output_dir)
                tagged = tag_source_file(source_path, config)
                update_status(conn, source_path, "complete",
                              finder_tagged=1 if tagged else 0,
                              processed_at=datetime.now().isoformat())
        return True

    if dry_run:
        logger.info("[DRY-RUN] Would process: %s (%.1fs)", source_path, duration)
        return True

    # Step 3: Denoise
    denoiser_cfg = config.get("denoiser", {})
    denoised_path = denoise(source_path, denoiser_cfg)
    if denoised_path:
        update_status(conn, source_path, "denoised", denoised_path=denoised_path)
        logger.info("Denoised: %s -> %s", source_path, denoised_path)
    else:
        logger.error("Denoising failed for: %s", source_path)
        retry_count = increment_retry(conn, source_path, "Denoising failed")
        if retry_count >= max_retries:
            mark_failed(conn, source_path)
        return False

    # Step 4: Transcribe
    transcriber = _get_transcriber(config)
    language = config.get("transcriber", {}).get("language", "en")
    result = transcriber.transcribe(denoised_path, language=language)
    if result:
        transcript = result["text"]
        word_count = result.get("word_count", len(transcript.split()))
        segments = result.get("segments", [])
        update_status(
            conn, source_path, "transcribed",
            transcript=transcript,
            word_count=word_count,
        )
        logger.info("Transcribed: %d words", word_count)
    else:
        logger.error("Transcription failed for: %s", source_path)
        retry_count = increment_retry(conn, source_path, "Transcription failed")
        if retry_count >= max_retries:
            mark_failed(conn, source_path)
        return False

    # Step 5: Optional diarization
    speakers = 1
    diarized = False
    if should_diarize(transcript, duration, segments):
        logger.info("Running diarization...")
        diar_result = diarize(denoised_path)
        if diar_result:
            speakers = count_speakers(diar_result)
            diarized = True
            logger.info("Diarization: %d speakers detected", speakers)
        else:
            logger.info("Diarization skipped or failed")

    # Step 6: Categorize
    cat_cfg = config.get("categorizer", {})
    cat_result = classify_recording(transcript, duration, cat_cfg)
    category = cat_result["category"]
    confidence = cat_result["confidence"]
    summary = cat_result["summary"]

    update_status(
        conn, source_path, "categorized",
        category=category,
        confidence=confidence,
        summary=summary,
        speakers=speakers,
        diarized=1 if diarized else 0,
    )
    logger.info("Categorized as '%s' (confidence=%.2f)", category, confidence)

    # Step 7: Write output
    rec = get_recording(conn, source_path)
    if rec:
        output_dir = write_output(rec, config)
        if output_dir:
            update_status(conn, source_path, "written", output_dir=output_dir)
        else:
            logger.error("Output write failed for: %s", source_path)
            retry_count = increment_retry(conn, source_path, "Output write failed")
            if retry_count >= max_retries:
                mark_failed(conn, source_path)
            return False

    # Step 8: Finder tag source file
    tagged = tag_source_file(source_path, config)
    update_status(
        conn, source_path, "complete",
        finder_tagged=1 if tagged else 0,
        processed_at=datetime.now().isoformat(),
    )

    logger.info("Complete: %s -> %s (%s)", source_path, category, summary[:60])
    return True


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_process(args, config: dict) -> int:
    """Process unprocessed recordings.

    Returns exit code (0 = success, 1 = errors occurred).
    """
    db_path = config["database"]["path"]
    conn = get_connection(db_path)

    start_time = time.time()
    run_id = create_pipeline_run(conn, "process" if not args.dry_run else "process-dry-run")

    # Step 1: Discover new files
    logger.info("Discovering new recordings...")
    discovered = discover(config)
    logger.info("Discovered %d recordings from sources", len(discovered))

    # Step 2: Insert into DB
    new_count = 0
    for rec in discovered:
        if not recording_exists(conn, rec["source_path"]):
            upsert_recording(conn, rec)
            new_count += 1

    logger.info("New recordings added to DB: %d", new_count)

    # Step 3: Get unprocessed recordings
    max_retries = config.get("retry", {}).get("max_retries", 3)
    source_filter = getattr(args, "source", None)
    unprocessed = get_unprocessed(
        conn,
        limit=args.limit or 0,
        source_app=source_filter,
        max_retries=max_retries,
    )

    total = len(unprocessed)
    logger.info("Files to process: %d", total)

    if args.dry_run:
        print(f"\n[DRY RUN] Discovered {len(discovered)} recordings, {new_count} new")
        print(f"[DRY RUN] Would process {total} recordings\n")
        for rec in unprocessed:
            source = rec["source_path"]
            app = rec["source_app"]
            recorded = rec["recorded_at"]
            status = rec["status"]
            print(f"  [{status:>12s}] {app:<12s} {recorded}  {os.path.basename(source)}")
        print()
        finish_pipeline_run(conn, run_id, len(discovered), 0, 0, time.time() - start_time)
        conn.close()
        return 0

    # Step 4: Process each recording
    processed = 0
    errored = 0
    for i, rec in enumerate(unprocessed, 1):
        logger.info("--- [%d/%d] ---", i, total)
        try:
            success = _process_single(rec, config, conn)
            if success:
                processed += 1
            else:
                errored += 1
        except Exception as e:
            logger.error("Unhandled error processing %s: %s", rec["source_path"], e)
            try:
                increment_retry(conn, rec["source_path"], str(e))
            except Exception:
                pass
            errored += 1

    duration = time.time() - start_time
    finish_pipeline_run(conn, run_id, len(discovered), processed, errored, duration)

    logger.info(
        "Pipeline complete: %d processed, %d errors (%.1fs)",
        processed, errored, duration,
    )

    conn.close()
    return 1 if errored > 0 else 0


def cmd_watch(args, config: dict) -> int:
    """Start the watcher daemon."""
    from watcher import PipelineWatcher
    from discovery import _compute_file_hash

    db_path = config["database"]["path"]
    # Shared DB connection for daemon mode (avoids per-file connection overhead)
    _daemon_conn = get_connection(db_path)

    def _identify_source(filepath: str) -> tuple:
        """Identify source app and parse timestamp from file path."""
        sources = config.get("sources", {})
        jpr_path = sources.get("jpr", {}).get("path", "")
        vm_path = sources.get("voice_memos", {}).get("path", "")

        if jpr_path and filepath.startswith(jpr_path):
            # Parse JPR timestamp: .../YYYY-MM-DD/HH-MM-SS[.m4a]
            import re
            match = re.search(r"(\d{4}-\d{2}-\d{2})/(\d{2}-\d{2}-\d{2})", filepath)
            if match:
                date_str, time_str = match.group(1), match.group(2).replace("-", ":")
                return "jpr", f"{date_str}T{time_str}"
            return "jpr", datetime.now().isoformat()

        if vm_path and filepath.startswith(vm_path):
            # Parse Voice Memos timestamp: YYYYMMDD HHMMSS-HEX.m4a
            import re
            match = re.search(r"(\d{8})\s+(\d{6})", os.path.basename(filepath))
            if match:
                d, t = match.group(1), match.group(2)
                ts = f"{d[:4]}-{d[4:6]}-{d[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}"
                return "voice_memos", ts
            return "voice_memos", datetime.now().isoformat()

        return "unknown", datetime.now().isoformat()

    def _on_new_file(filepath: str) -> None:
        """Callback when watcher detects a new file."""
        if not filepath:
            # Empty path = "scan all" signal from --once mode
            logger.info("Running full scan...")
            discovered = discover(config)
            for rec in discovered:
                if not recording_exists(_daemon_conn, rec["source_path"]):
                    upsert_recording(_daemon_conn, rec)
            unprocessed = get_unprocessed(_daemon_conn, max_retries=config.get("retry", {}).get("max_retries", 3))
            for rec in unprocessed:
                try:
                    _process_single(rec, config, _daemon_conn)
                except Exception as e:
                    logger.error("Error processing %s: %s", rec["source_path"], e)
            return

        # Single file processing
        if recording_exists(_daemon_conn, filepath):
            logger.debug("Already in DB, skipping: %s", filepath)
            return

        # Proper source identification + hash computation
        source_app, recorded_at = _identify_source(filepath)
        file_info = {
            "source_path": filepath,
            "source_app": source_app,
            "recorded_at": recorded_at,
            "file_size": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            "file_hash": _compute_file_hash(filepath),
        }
        upsert_recording(_daemon_conn, file_info)
        rec = get_recording(_daemon_conn, filepath)
        if rec:
            try:
                _process_single(rec, config, _daemon_conn)
            except Exception as e:
                logger.error("Error processing %s: %s", filepath, e)

    watcher = PipelineWatcher(config, _on_new_file)

    if args.once:
        logger.info("Running single scan pass...")
        watcher.start(once=True)
    else:
        logger.info("Starting watcher daemon (foreground=%s)...", args.foreground)
        watcher.start()

    return 0


def cmd_status(args, config: dict) -> int:
    """Show pipeline statistics."""
    db_path = config["database"]["path"]

    if not os.path.exists(db_path):
        if args.json:
            print(json.dumps({"error": "No database found", "total": 0}))
        else:
            print("\nNo database found. Run 'process' first to initialize.\n")
        return 0

    conn = get_connection(db_path)
    stats = get_stats(conn)
    conn.close()

    if args.json:
        print(json.dumps(stats, indent=2, default=str))
        return 0

    # Human-readable output
    print()
    print("Voice Pipeline Status")
    print("\u2501" * 22)
    print(f"  Total recordings tracked:  {stats['total']:>3d}")
    print(f"    Complete:                {stats['complete']:>3d}")
    print(f"    Pending:                 {stats['pending']:>3d}")
    print(f"    Errors:                  {stats['errors']:>3d}")
    print(f"    Failed:                  {stats['failed']:>3d}")
    print()

    categories = stats.get("categories", {})
    if categories:
        print("  By category:")
        cat_display = {
            "prayer": "Prayer",
            "daily-log": "Daily log",
            "meditation": "Meditation",
            "ambient": "Ambient",
            "uncategorized": "Uncategorized",
        }
        for cat, count in categories.items():
            name = cat_display.get(cat, cat.title())
            print(f"    {name + ':':<20s} {count:>3d}")
        print()

    last_run = stats.get("last_run")
    if last_run:
        started = last_run.get("started_at", "")
        duration = last_run.get("duration_secs", 0)
        processed = last_run.get("files_processed", 0)
        if duration > 0:
            dur_str = f"{int(duration // 60)}m {int(duration % 60)}s"
        else:
            dur_str = "N/A"
        print(f"  Last run: {started} (processed {processed} files in {dur_str})")
    else:
        print("  Last run: Never")
    print()

    return 0


def cmd_reprocess(args, config: dict) -> int:
    """Force reprocessing of recordings."""
    db_path = config["database"]["path"]
    conn = get_connection(db_path)

    if args.file:
        # Reprocess specific file
        rec = get_recording(conn, args.file)
        if not rec:
            logger.error("Recording not found in DB: %s", args.file)
            conn.close()
            return 1

        # Reset status to trigger reprocessing
        update_status(conn, args.file, "discovered", retry_count=0, error_message="")
        logger.info("Reset status for reprocessing: %s", args.file)
        rec = get_recording(conn, args.file)

        if args.diarize:
            # Force diarization flag for this recording
            logger.info("Diarization will be forced for: %s", args.file)

        success = _process_single(rec, config, conn)
        conn.close()
        return 0 if success else 1

    if args.failed:
        # Reprocess all failed recordings
        rows = conn.execute(
            "SELECT * FROM recordings WHERE status = 'failed'"
        ).fetchall()

        if not rows:
            logger.info("No failed recordings to reprocess")
            conn.close()
            return 0

        logger.info("Reprocessing %d failed recordings", len(rows))
        processed = 0
        for row in rows:
            rec = dict(row)
            update_status(conn, rec["source_path"], "discovered",
                          retry_count=0, error_message="")
            rec = get_recording(conn, rec["source_path"])
            try:
                if _process_single(rec, config, conn):
                    processed += 1
            except Exception as e:
                logger.error("Error reprocessing %s: %s", rec["source_path"], e)

        logger.info("Reprocessed: %d/%d succeeded", processed, len(rows))
        conn.close()
        return 0

    logger.error("Specify --file PATH or --failed")
    conn.close()
    return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        prog="voice-pipeline",
        description="Process voice recordings from Apple Watch into organized iCloud archive",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to config.yaml (default: config.yaml in tool directory)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # process
    p_process = subparsers.add_parser("process", help="Batch process unprocessed recordings")
    p_process.add_argument("--limit", "-n", type=int, default=0,
                           help="Process at most N files")
    p_process.add_argument("--source", choices=["jpr", "voice_memos"],
                           help="Only process from one source")
    p_process.add_argument("--dry-run", action="store_true",
                           help="Discover only, don't process")

    # watch
    p_watch = subparsers.add_parser("watch", help="Start watcher daemon")
    p_watch.add_argument("--foreground", action="store_true",
                         help="Run in foreground (for LaunchAgent)")
    p_watch.add_argument("--once", action="store_true",
                         help="Single pass, then exit")

    # status
    p_status = subparsers.add_parser("status", help="Show pipeline statistics")
    p_status.add_argument("--json", action="store_true",
                          help="Machine-readable JSON output")

    # reprocess
    p_reprocess = subparsers.add_parser("reprocess", help="Force reprocessing")
    p_reprocess.add_argument("--file", help="Specific file path to reprocess")
    p_reprocess.add_argument("--failed", action="store_true",
                             help="Reprocess all failed recordings")
    p_reprocess.add_argument("--diarize", action="store_true",
                             help="Force diarization on reprocessed files")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Load config
    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Setup logging
    _setup_logging(config)

    # Dispatch
    commands = {
        "process": cmd_process,
        "watch": cmd_watch,
        "status": cmd_status,
        "reprocess": cmd_reprocess,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args, config)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
