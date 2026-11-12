"""File system watcher daemon for the voice recording pipeline.

Uses watchdog's PollingObserver (NOT FSEvents) because iCloud Drive
directories require polling for reliable change detection.
"""

import logging
import os
import signal
import sys
import threading
import time
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from watchdog.observers.polling import PollingObserver

logger = logging.getLogger(__name__)


class RecordingHandler(FileSystemEventHandler):
    """Handles new audio file events from watched directories."""

    def __init__(
        self,
        process_callback: Callable[[str], None],
        extensions: tuple = (".m4a", ".wav", ".mp3"),
    ):
        """
        Args:
            process_callback: Function to call with new file path.
            extensions: Tuple of audio file extensions to watch for.
        """
        super().__init__()
        self._callback = process_callback
        self._extensions = extensions
        self._seen: dict = {}  # path -> timestamp, bounded with LRU eviction
        self._max_seen = 10000
        self._lock = threading.Lock()

    def _should_process(self, path: str) -> bool:
        """Check if a file should be processed."""
        # Skip hidden files and iCloud stubs
        basename = os.path.basename(path)
        if basename.startswith("."):
            return False

        # Skip non-audio files (unless extensionless, which JPR uses)
        _, ext = os.path.splitext(basename)
        if ext and ext.lower() not in self._extensions:
            return False

        # Skip waveform files, DB files
        if ".waveform" in basename.lower() or basename.endswith(".db"):
            return False

        # Deduplicate events with bounded LRU eviction
        with self._lock:
            now = time.time()
            if path in self._seen:
                return False
            # Evict oldest entries if at capacity
            if len(self._seen) >= self._max_seen:
                oldest = sorted(self._seen, key=self._seen.get)[:self._max_seen // 4]
                for old_path in oldest:
                    del self._seen[old_path]
            self._seen[path] = now

        return True

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            logger.info("New file detected: %s", event.src_path)
            try:
                self._callback(event.src_path)
            except Exception as e:
                logger.error("Error processing new file %s: %s", event.src_path, e)

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events (for completed downloads)."""
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            logger.info("File modified (likely download complete): %s", event.src_path)
            try:
                self._callback(event.src_path)
            except Exception as e:
                logger.error("Error processing modified file %s: %s", event.src_path, e)


class PipelineWatcher:
    """Watches source directories for new recordings and triggers processing.

    Uses PollingObserver because FSEvents does not reliably detect changes
    in iCloud Drive directories.
    """

    def __init__(
        self,
        config: dict,
        process_callback: Callable[[str], None],
    ):
        """
        Args:
            config: Full pipeline config dict.
            process_callback: Function to call when a new recording is found.
                             Receives the file path as argument.
        """
        self._config = config
        self._callback = process_callback
        self._observer: Optional[PollingObserver] = None
        self._running = False
        self._stop_event = threading.Event()

    def _get_watch_dirs(self) -> list:
        """Get list of directories to watch from config."""
        sources = self._config.get("sources", {})
        dirs = []
        for name, source in sources.items():
            if not source.get("enabled", False):
                continue
            path = source.get("path", "")
            if path and os.path.isdir(path):
                dirs.append(path)
            else:
                logger.warning("Source '%s' path does not exist: %s", name, path)
        return dirs

    def start(self, once: bool = False) -> None:
        """Start watching for new recordings.

        Args:
            once: If True, do a single scan pass then exit.
        """
        watch_dirs = self._get_watch_dirs()
        if not watch_dirs:
            logger.error("No valid source directories to watch")
            return

        poll_interval = self._config.get("watcher", {}).get("poll_interval_secs", 30)

        if once:
            # Single pass mode: just trigger a process run
            logger.info("Single-pass mode: scanning all sources")
            self._callback("")  # Empty path signals "scan all"
            return

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Create polling observer
        self._observer = PollingObserver(timeout=poll_interval)
        handler = RecordingHandler(self._callback)

        for watch_dir in watch_dirs:
            self._observer.schedule(handler, watch_dir, recursive=True)
            logger.info("Watching directory: %s (poll every %ds)", watch_dir, poll_interval)

        self._running = True
        self._observer.start()
        logger.info("Pipeline watcher started (poll interval: %ds)", poll_interval)

        try:
            while self._running and not self._stop_event.is_set():
                self._stop_event.wait(timeout=1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        self._running = False
        self._stop_event.set()

        if self._observer is not None:
            logger.info("Stopping pipeline watcher...")
            self._observer.stop()
            self._observer.join(timeout=10)
            self._observer = None
            logger.info("Pipeline watcher stopped")

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle SIGTERM and SIGINT for graceful shutdown."""
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down...", sig_name)
        self.stop()
