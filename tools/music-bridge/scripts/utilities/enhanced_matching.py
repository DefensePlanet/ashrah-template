#!/usr/bin/env python3
"""
Enhanced Music Matching Framework
Inspired by SongShift's multi-stage matching approach with industry best practices
"""

import subprocess
import re
import json
import unicodedata
from typing import List, Dict, Tuple, Optional, Set
from rapidfuzz import fuzz, process
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class MatchStrategy(Enum):
    """Matching strategies in order of preference"""
    ISRC_EXACT = "isrc_exact"
    METADATA_EXACT = "metadata_exact"
    NORMALIZED_EXACT = "normalized_exact"
    FUZZY_HIGH = "fuzzy_high"
    FUZZY_MEDIUM = "fuzzy_medium"
    ARTIST_TITLE_SPLIT = "artist_title_split"
    TITLE_ONLY = "title_only"
    ARTIST_ONLY = "artist_only"


@dataclass
class MatchResult:
    """Enhanced match result with detailed scoring"""
    title: str
    artist: str
    album: str
    isrc: Optional[str] = None
    match_score: float = 0.0
    strategy: MatchStrategy = MatchStrategy.TITLE_ONLY
    confidence: float = 0.0
    search_query: str = ""
    normalized_title: str = ""
    normalized_artist: str = ""


class EnhancedMusicMatcher:
    """
    Enhanced music matching using SongShift-inspired multi-stage approach:
    1. ISRC-first matching (highest accuracy)
    2. Exact metadata matching
    3. Normalized exact matching
    4. Fuzzy matching with multiple strategies
    5. Fallback searches with progressive loosening
    """

    def __init__(self):
        self.search_cache = {}
        self.isrc_cache = {}

        # Artist name variations and aliases
        self.artist_aliases = self._load_artist_aliases()

        # Common words to remove/normalize
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'into', 'during', 'including', 'until',
            'against', 'among', 'throughout', 'despite', 'towards', 'upon'
        }

    def _load_artist_aliases(self) -> Dict[str, List[str]]:
        """Load common artist name variations and aliases"""
        return {
            # Add common artist aliases - this could be loaded from a file
            "p!nk": ["pink", "p ink", "p-ink"],
            "ke$ha": ["kesha", "ke sha"],
            "will.i.am": ["will i am", "william"],
            # Add more as needed
        }

    def advanced_normalize_string(self, text: str) -> str:
        """Advanced string normalization using multiple techniques"""
        if not text:
            return ""

        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)

        # Convert to lowercase
        text = text.lower()

        # Remove featuring/collaboration indicators with variations
        patterns_to_remove = [
            r'\b(?:feat\.?|ft\.?|featuring|with|and|x|vs\.?|versus)\s+[^)]*',
            r'\([^)]*(?:feat\.?|ft\.?|featuring|remix|version|edit|remaster|live|acoustic|radio|explicit|clean)[^)]*\)',
            r'\[[^\]]*(?:feat\.?|ft\.?|featuring|remix|version|edit|remaster|live|acoustic|radio|explicit|clean)[^\]]*\]',
            r'\b(?:remix|version|edit|remaster|live|acoustic|radio|explicit|clean|instrumental)\b.*',
            r'\b(?:single|album|deluxe|extended|special)\s+(?:version|edition)\b',
            r'\b\d{4}\s*(?:remaster|version|edit)\b'
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Handle special characters and punctuation
        # Keep apostrophes for contractions like "don't"
        text = re.sub(r'[^\w\s\']', ' ', text)

        # Normalize apostrophes
        text = re.sub(r'['''']', "'", text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove stop words from the beginning/end
        words = text.split()
        while words and words[0] in self.stop_words:
            words.pop(0)
        while words and words[-1] in self.stop_words:
            words.pop()

        return ' '.join(words).strip()

    def extract_isrc_from_metadata(self, track_data: Dict[str, str]) -> Optional[str]:
        """Extract ISRC from track metadata if available"""
        # Check common ISRC field names
        isrc_fields = ['isrc', 'ISRC', 'international_standard_recording_code']
        for field in isrc_fields:
            if field in track_data and track_data[field]:
                return track_data[field].strip().upper()
        return None

    def generate_search_variations(self, title: str, artist: str, isrc: Optional[str] = None) -> List[Dict[str, str]]:
        """Generate comprehensive search variations with weighted priorities"""
        variations = []

        # Normalize inputs
        norm_title = self.advanced_normalize_string(title)
        norm_artist = self.advanced_normalize_string(artist)

        # Strategy 1: ISRC-based search (highest priority)
        if isrc:
            variations.append({
                "query": isrc,
                "strategy": MatchStrategy.ISRC_EXACT,
                "weight": 100,
                "description": "ISRC exact match"
            })

        # Strategy 2: Exact metadata matching
        variations.extend([
            {
                "query": f'"{artist}" "{title}"',
                "strategy": MatchStrategy.METADATA_EXACT,
                "weight": 95,
                "description": "Exact artist and title"
            },
            {
                "query": f"{artist} {title}",
                "strategy": MatchStrategy.METADATA_EXACT,
                "weight": 90,
                "description": "Artist + title"
            }
        ])

        # Strategy 3: Normalized exact matching
        if norm_title != title or norm_artist != artist:
            variations.extend([
                {
                    "query": f'"{norm_artist}" "{norm_title}"',
                    "strategy": MatchStrategy.NORMALIZED_EXACT,
                    "weight": 85,
                    "description": "Normalized exact match"
                },
                {
                    "query": f"{norm_artist} {norm_title}",
                    "strategy": MatchStrategy.NORMALIZED_EXACT,
                    "weight": 80,
                    "description": "Normalized artist + title"
                }
            ])

        # Strategy 4: Artist aliases and variations
        artist_variations = self._get_artist_variations(artist)
        for alt_artist in artist_variations[:3]:  # Limit to top 3 variations
            variations.append({
                "query": f"{alt_artist} {title}",
                "strategy": MatchStrategy.FUZZY_HIGH,
                "weight": 75,
                "description": f"Artist alias: {alt_artist}"
            })

        # Strategy 5: Title-focused searches
        variations.extend([
            {
                "query": f'"{title}"',
                "strategy": MatchStrategy.TITLE_ONLY,
                "weight": 70,
                "description": "Exact title only"
            },
            {
                "query": norm_title,
                "strategy": MatchStrategy.TITLE_ONLY,
                "weight": 65,
                "description": "Normalized title only"
            }
        ])

        # Strategy 6: Artist-focused searches (for popular artists)
        if len(artist.split()) <= 2:  # Only for short artist names
            variations.extend([
                {
                    "query": f'"{artist}"',
                    "strategy": MatchStrategy.ARTIST_ONLY,
                    "weight": 60,
                    "description": "Exact artist only"
                },
                {
                    "query": norm_artist,
                    "strategy": MatchStrategy.ARTIST_ONLY,
                    "weight": 55,
                    "description": "Normalized artist only"
                }
            ])

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            query_key = var["query"].lower().strip()
            if query_key and query_key not in seen:
                seen.add(query_key)
                unique_variations.append(var)

        return unique_variations

    def _get_artist_variations(self, artist: str) -> List[str]:
        """Get artist name variations and aliases"""
        variations = []

        # Check predefined aliases
        artist_lower = artist.lower()
        if artist_lower in self.artist_aliases:
            variations.extend(self.artist_aliases[artist_lower])

        # Generate common variations
        variations.extend([
            # Remove "The" prefix
            re.sub(r'^the\s+', '', artist, flags=re.IGNORECASE),
            # Add "The" prefix if not present
            f"the {artist}" if not artist.lower().startswith('the ') else artist,
            # Handle punctuation variations
            re.sub(r'[^\w\s]', '', artist),
            re.sub(r'[^\w\s]', ' ', artist),
        ])

        # Remove duplicates and empty strings
        return list(filter(None, list(dict.fromkeys(variations))))

    def search_apple_music_enhanced(self, query: str, strategy: MatchStrategy) -> List[Dict[str, str]]:
        """Enhanced Apple Music search with strategy-specific handling"""
        if query in self.search_cache:
            return self.search_cache[query]

        # Handle ISRC searches differently
        if strategy == MatchStrategy.ISRC_EXACT:
            return self._search_by_isrc(query)

        # Standard AppleScript search
        safe_query = query.replace('"', '\\"')

        applescript = f'''
        tell application "Music"
            try
                set searchResults to (search playlist 1 for "{safe_query}")
                set resultList to {{}}

                repeat with track in searchResults
                    try
                        set trackInfo to (name of track) & "|" & (artist of track) & "|" & (album of track)
                        set end of resultList to trackInfo
                    end try
                end repeat

                set AppleScript's text item delimiters to "~~~"
                set resultString to resultList as string
                set AppleScript's text item delimiters to ""

                return resultString
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
                timeout=20
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

                self.search_cache[query] = tracks
                return tracks

        except Exception as e:
            print(f"Search error for '{query}': {e}")

        self.search_cache[query] = []
        return []

    def _search_by_isrc(self, isrc: str) -> List[Dict[str, str]]:
        """Search by ISRC code (if supported by the music service)"""
        # Note: AppleScript may not support ISRC search directly
        # This is a placeholder for future ISRC-based search implementation
        return []

    def calculate_enhanced_match_score(self, original: Dict[str, str], found: Dict[str, str],
                                     strategy: MatchStrategy) -> Tuple[float, float]:
        """Calculate enhanced similarity score with confidence rating"""

        # Normalize for comparison
        orig_title = self.advanced_normalize_string(original.get("title", ""))
        orig_artist = self.advanced_normalize_string(original.get("artist", ""))

        found_title = self.advanced_normalize_string(found.get("title", ""))
        found_artist = self.advanced_normalize_string(found.get("artist", ""))

        # Multiple scoring algorithms
        title_ratio = fuzz.ratio(orig_title, found_title)
        title_partial = fuzz.partial_ratio(orig_title, found_title)
        title_token_sort = fuzz.token_sort_ratio(orig_title, found_title)
        title_token_set = fuzz.token_set_ratio(orig_title, found_title)

        artist_ratio = fuzz.ratio(orig_artist, found_artist)
        artist_partial = fuzz.partial_ratio(orig_artist, found_artist)
        artist_token_sort = fuzz.token_sort_ratio(orig_artist, found_artist)
        artist_token_set = fuzz.token_set_ratio(orig_artist, found_artist)

        # Weighted scoring based on strategy
        if strategy == MatchStrategy.ISRC_EXACT:
            # ISRC match gets highest confidence
            base_score = 100.0
            confidence = 95.0
        elif strategy in [MatchStrategy.METADATA_EXACT, MatchStrategy.NORMALIZED_EXACT]:
            # Exact matches get high weight
            title_score = max(title_ratio, title_partial, title_token_sort, title_token_set)
            artist_score = max(artist_ratio, artist_partial, artist_token_sort, artist_token_set)
            base_score = (title_score * 0.7) + (artist_score * 0.3)
            confidence = min(90.0, base_score * 0.9)
        else:
            # Fuzzy matches use comprehensive scoring
            title_score = (title_ratio * 0.4 + title_partial * 0.2 +
                          title_token_sort * 0.2 + title_token_set * 0.2)
            artist_score = (artist_ratio * 0.4 + artist_partial * 0.2 +
                           artist_token_sort * 0.2 + artist_token_set * 0.2)
            base_score = (title_score * 0.75) + (artist_score * 0.25)
            confidence = min(85.0, base_score * 0.8)

        return base_score, confidence

    def find_best_match_enhanced(self, track_data: Dict[str, str],
                               min_score: float = 60.0) -> Optional[MatchResult]:
        """Enhanced matching using multi-stage approach"""

        title = track_data.get("title", "")
        artist = track_data.get("artist", "")
        isrc = self.extract_isrc_from_metadata(track_data)

        print(f"   🔍 Enhanced Search: {artist} - {title}")
        if isrc:
            print(f"   📟 ISRC: {isrc}")

        # Generate search variations with strategies
        variations = self.generate_search_variations(title, artist, isrc)

        best_match = None
        best_score = 0
        search_results_count = 0

        for i, variation in enumerate(variations):
            query = variation["query"]
            strategy = variation["strategy"]
            weight = variation["weight"]
            description = variation["description"]

            print(f"   🔄 Try {i+1}: {description} - '{query[:50]}...'")

            # Search Apple Music
            results = self.search_apple_music_enhanced(query, strategy)
            search_results_count += len(results)

            if not results:
                print(f"   ❌ No results")
                continue

            print(f"   📊 Found {len(results)} results")

            # Evaluate each result
            for result in results:
                score, confidence = self.calculate_enhanced_match_score(
                    track_data, result, strategy
                )

                # Apply strategy weight
                weighted_score = score * (weight / 100)

                if weighted_score > best_score and score >= min_score:
                    best_score = weighted_score
                    best_match = MatchResult(
                        title=result["title"],
                        artist=result["artist"],
                        album=result["album"],
                        isrc=isrc,
                        match_score=score,
                        strategy=strategy,
                        confidence=confidence,
                        search_query=query,
                        normalized_title=self.advanced_normalize_string(result["title"]),
                        normalized_artist=self.advanced_normalize_string(result["artist"])
                    )
                    print(f"   ✅ New best: {score:.1f}% via {strategy.value}")

            # Early exit for very high confidence matches
            if best_match and best_match.confidence > 90:
                print(f"   🎯 High confidence match found, stopping search")
                break

        if best_match:
            print(f"   🏆 Final Match: {best_match.artist} - {best_match.title}")
            print(f"   📈 Score: {best_match.match_score:.1f}% | Confidence: {best_match.confidence:.1f}%")
            print(f"   🔧 Strategy: {best_match.strategy.value}")
        else:
            print(f"   ❌ No suitable match found (searched {search_results_count} results)")

        return best_match

    def add_track_to_playlist_enhanced(self, match_result: MatchResult,
                                     playlist_name: str, dry_run: bool = False) -> bool:
        """Enhanced playlist addition with better error handling"""

        safe_title = match_result.title.replace('"', '\\"')
        safe_artist = match_result.artist.replace('"', '\\"')
        safe_playlist = playlist_name.replace('"', '\\"')

        applescript = f'''
        tell application "Music"
            try
                -- Search for the exact track we found
                set searchResults to (search playlist 1 for "{safe_artist} {safe_title}")

                if (count of searchResults) > 0 then
                    set foundTrack to item 1 of searchResults

                    -- Get or create playlist
                    try
                        set targetPlaylist to playlist "{safe_playlist}"
                    on error
                        set targetPlaylist to (make new playlist with properties {{name:"{safe_playlist}"}})
                    end try

                    -- Add track (unless dry run)
                    {"-- DRY RUN MODE" if dry_run else "duplicate foundTrack to targetPlaylist"}

                    return "SUCCESS"
                else
                    return "NOTFOUND"
                end if
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=25
            )

            success = result.returncode == 0 and result.stdout.strip() == "SUCCESS"
            if success:
                print(f"   ✅ {'Would add' if dry_run else 'Added'} to playlist: {playlist_name}")
            else:
                print(f"   ⚠️ Failed to add: {result.stdout.strip()}")

            return success

        except Exception as e:
            print(f"   ⚠️ Error adding track: {e}")
            return False


def enhanced_sync_test(export_file: str, playlist_name: str, dry_run: bool = True):
    """Test the enhanced matching system"""

    print("🚀 Enhanced Multi-Stage Matching Framework")
    print("=" * 60)
    print("Strategies: ISRC → Exact → Normalized → Fuzzy → Fallback")
    print()

    # Load Spotify export
    if not Path(export_file).exists():
        print(f"❌ Export file not found: {export_file}")
        return

    with open(export_file, 'r') as f:
        tracks = json.load(f)

    print(f"📋 Loaded {len(tracks)} tracks from Spotify export")
    print(f"🎯 Target playlist: {playlist_name}")
    print(f"🧪 Mode: {'DRY RUN' if dry_run else 'LIVE SYNC'}")
    print()

    matcher = EnhancedMusicMatcher()

    results = {
        "total": len(tracks),
        "matched": 0,
        "added": 0,
        "failed": 0,
        "by_strategy": {}
    }

    for i, track_data in enumerate(tracks, 1):
        print(f"🎶 [{i}/{len(tracks)}] Processing track...")

        # Find best match using enhanced algorithm
        best_match = matcher.find_best_match_enhanced(track_data, min_score=50.0)

        if best_match:
            results["matched"] += 1

            # Track strategy usage
            strategy_name = best_match.strategy.value
            if strategy_name not in results["by_strategy"]:
                results["by_strategy"][strategy_name] = 0
            results["by_strategy"][strategy_name] += 1

            # Add to playlist
            if matcher.add_track_to_playlist_enhanced(best_match, playlist_name, dry_run):
                results["added"] += 1
            else:
                print(f"   ⚠️ Match found but failed to add to playlist")
        else:
            results["failed"] += 1

        print()

    # Enhanced summary
    match_rate = (results["matched"] / results["total"]) * 100
    success_rate = (results["added"] / results["total"]) * 100

    print("📊 Enhanced Matching Results:")
    print("-" * 50)
    print(f"Total tracks: {results['total']}")
    print(f"Matched: {results['matched']} ({match_rate:.1f}%)")
    print(f"{'Would be added' if dry_run else 'Added'}: {results['added']} ({success_rate:.1f}%)")
    print(f"Failed: {results['failed']}")
    print()

    print("🔧 Strategy Breakdown:")
    for strategy, count in results["by_strategy"].items():
        percentage = (count / results["matched"]) * 100 if results["matched"] > 0 else 0
        print(f"  {strategy}: {count} ({percentage:.1f}%)")

    print()
    print(f"🎵 Check Apple Music for '{playlist_name}' playlist!")


if __name__ == "__main__":
    # Test with enhanced matching
    enhanced_sync_test("spotify_export_Nolantunes.json", "Enhanced-Sync-Test-v2", dry_run=True)