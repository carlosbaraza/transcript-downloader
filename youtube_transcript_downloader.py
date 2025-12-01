#!/usr/bin/env python3
"""
YouTube Channel Transcript Downloader

Downloads all transcripts from a YouTube channel and saves them as markdown files.
Each file is named with the upload date and video title.
"""

import os
import re
import json
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeTranscriptDownloader:
    def __init__(self, output_dir: str = "transcripts", use_claude: bool = True):
        """
        Initialize the YouTube Transcript Downloader
        
        Args:
            output_dir: Directory to save transcript files
            use_claude: Whether to use Claude API for summarization
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize YouTube Transcript API with Webshare proxy
        proxy_config = WebshareProxyConfig(
            proxy_username="jvzvvtlb-8",
            proxy_password="hn55bu8omqiv"
        )
        self.ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        self.formatter = TextFormatter()
        self.use_claude = use_claude
        
        # Initialize Claude client if API key is available
        self.claude_client = None
        if self.use_claude:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude API initialized successfully")
            else:
                logger.warning("ANTHROPIC_API_KEY not found in environment. Summarization disabled.")
                self.use_claude = False
        
        # Load channel-specific prompts
        self.channel_prompts = self.load_channel_prompts()
    
    def load_channel_prompts(self) -> Dict:
        """
        Load channel-specific prompts from configuration file
        
        Returns:
            Dictionary of channel prompts
        """
        prompt_file = Path("channel_prompts.json")
        if prompt_file.exists():
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load channel prompts: {e}")
        return {
            "default": {
                "system_prompt": "You are an expert content summarizer.",
                "user_prompt_template": "Please summarize this transcript:\n\n{transcript}"
            }
        }
    
    def generate_summary(self, transcript: str, channel_name: str, video_title: str) -> Optional[str]:
        """
        Generate a summary of the transcript using Claude API
        
        Args:
            transcript: The video transcript text
            channel_name: Name of the YouTube channel
            video_title: Title of the video
            
        Returns:
            Generated summary or None if failed
        """
        if not self.claude_client or not transcript:
            return None
        
        try:
            # Get channel-specific or default prompts
            prompts = self.channel_prompts.get(channel_name, self.channel_prompts.get("default"))
            
            # Format the user prompt
            user_prompt = prompts["user_prompt_template"].format(transcript=transcript)
            
            # Add video context to the prompt
            context_prompt = f"Video Title: {video_title}\nChannel: {channel_name}\n\n{user_prompt}"
            
            logger.info(f"Generating summary with Claude for: {video_title}")
            
            # Call Claude API with Sonnet model
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Using Claude 3.5 Sonnet
                max_tokens=4000,
                temperature=0,
                system=prompts["system_prompt"],
                messages=[
                    {
                        "role": "user",
                        "content": context_prompt
                    }
                ]
            )
            
            summary = response.content[0].text
            logger.info("Summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
        
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for filesystem compatibility
        
        Args:
            filename: Raw filename string
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        # Trim whitespace
        filename = filename.strip()
        # Limit length (leave room for date prefix and .md extension)
        max_length = 200
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit(' ', 1)[0]
        return filename
    
    def get_channel_videos(self, channel_url: str) -> List[Dict]:
        """
        Get all video information from a YouTube channel
        
        Args:
            channel_url: URL of the YouTube channel
            
        Returns:
            List of video information dictionaries
        """
        logger.info(f"Fetching videos from channel: {channel_url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Handle different URL formats
                if '/videos' not in channel_url:
                    channel_url = f"{channel_url.rstrip('/')}/videos"
                    
                info = ydl.extract_info(channel_url, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry and 'id' in entry:
                            video_info = {
                                'id': entry['id'],
                                'title': entry.get('title', 'Unknown'),
                                'url': f"https://www.youtube.com/watch?v={entry['id']}",
                                'duration': entry.get('duration', 0)  # Duration in seconds
                            }
                            videos.append(video_info)
                            
                logger.info(f"Found {len(videos)} videos")
                return videos
                
            except Exception as e:
                logger.error(f"Error fetching channel videos: {e}")
                return []
    
    def get_video_metadata(self, video_id: str) -> Optional[Dict]:
        """
        Get detailed metadata for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video metadata dictionary or None if error
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                # Parse upload date
                upload_date = info.get('upload_date', '')
                if upload_date:
                    upload_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
                else:
                    upload_date = datetime.now().strftime('%Y-%m-%d')
                
                return {
                    'id': video_id,
                    'title': info.get('title', 'Unknown'),
                    'upload_date': upload_date,
                    'duration': info.get('duration', 0),
                    'channel': info.get('channel', 'Unknown'),
                    'description': info.get('description', ''),
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
                
            except Exception as e:
                logger.warning(f"Could not fetch metadata for video {video_id}: {e}")
                return None
    
    def download_transcript(self, video_id: str, languages: List[str] = ['en']) -> Optional[Tuple[str, List[Dict]]]:
        """
        Download transcript for a video
        
        Args:
            video_id: YouTube video ID
            languages: List of language codes in order of preference
            
        Returns:
            Tuple of (formatted transcript text, raw transcript data) or None if not available
        """
        try:
            transcript_list = self.ytt_api.list(video_id)
            
            # Try to find transcript in preferred languages
            transcript = None
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    logger.info(f"Found transcript in language: {lang}")
                    break
                except:
                    continue
            
            # If no preferred language found, try to get any available transcript
            if not transcript:
                # Try manually created transcripts first
                try:
                    transcript = transcript_list.find_manually_created_transcript(languages)
                except:
                    # Fall back to generated transcripts
                    try:
                        transcript = transcript_list.find_generated_transcript(languages)
                    except:
                        # Get the first available transcript
                        if transcript_list:
                            transcript = transcript_list[0]
                        else:
                            logger.warning(f"No transcript available for video {video_id}")
                            return None
            
            # Fetch and format the transcript
            fetched = transcript.fetch()
            formatted = self.formatter.format_transcript(fetched)
            raw_data = fetched.to_raw_data()
            return formatted, raw_data
            
        except Exception as e:
            logger.warning(f"Error downloading transcript for {video_id}: {e}")
            return None
    
    def format_transcript_with_timestamps(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript with timestamps for each paragraph
        
        Args:
            transcript_data: Raw transcript data from API
            
        Returns:
            Formatted transcript with timestamps
        """
        formatted_lines = []
        current_paragraph = []
        current_start_time = None
        
        for i, entry in enumerate(transcript_data):
            text = entry['text'].strip()
            start = entry['start']
            
            if not text:
                continue
            
            # Format timestamp as [HH:MM:SS]
            hours = int(start // 3600)
            minutes = int((start % 3600) // 60)
            seconds = int(start % 60)
            timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
            
            # Start new paragraph if this is the first entry or there's a significant pause
            if current_start_time is None:
                current_start_time = timestamp
                current_paragraph = [text]
            else:
                # Check for natural paragraph break (e.g., long pause or sentence end)
                prev_end = transcript_data[i-1]['start'] + transcript_data[i-1]['duration']
                pause = start - prev_end
                
                # Start new paragraph if pause > 2 seconds or we have enough text
                if pause > 2.0 or (len(' '.join(current_paragraph)) > 300 and text[0].isupper()):
                    # Output current paragraph
                    formatted_lines.append(f"{current_start_time} {' '.join(current_paragraph)}")
                    formatted_lines.append("")  # Empty line between paragraphs
                    
                    # Start new paragraph
                    current_start_time = timestamp
                    current_paragraph = [text]
                else:
                    current_paragraph.append(text)
        
        # Don't forget the last paragraph
        if current_paragraph:
            formatted_lines.append(f"{current_start_time} {' '.join(current_paragraph)}")
        
        return '\n'.join(formatted_lines)
    
    def save_transcript(self, video_metadata: Dict, transcript: str, transcript_data: List[Dict], channel_name: str, summary: Optional[str] = None) -> str:
        """
        Save transcript as markdown file with optional AI summary
        
        Args:
            video_metadata: Video metadata dictionary
            transcript: Transcript text (unused, kept for compatibility)
            transcript_data: Raw transcript data for timestamp formatting
            channel_name: Name of the channel for organization
            summary: Optional AI-generated summary
            
        Returns:
            Path to saved file
        """
        # Create channel-specific directory
        channel_dir = self.output_dir / self.sanitize_filename(channel_name)
        channel_dir.mkdir(exist_ok=True)
        
        # Create filename with date prefix
        safe_title = self.sanitize_filename(video_metadata['title'])
        filename = f"{video_metadata['upload_date']}_{safe_title}.md"
        filepath = channel_dir / filename
        
        # Format transcript with timestamps
        timestamped_transcript = self.format_transcript_with_timestamps(transcript_data)
        
        # Build content with summary if available
        content_parts = [f"# {video_metadata['title']}"]
        
        content_parts.append(f"""
**Channel:** {video_metadata['channel']}
**Upload Date:** {video_metadata['upload_date']}
**URL:** {video_metadata['url']}
**Duration:** {video_metadata['duration'] // 60} minutes

## Description

{video_metadata.get('description', 'No description available')}""")
        
        # Add AI summary if available
        if summary:
            content_parts.append(f"""
## AI Summary

{summary}""")
        
        # Add transcript
        content_parts.append(f"""
## Transcript

{timestamped_transcript}""")
        
        content = '\n'.join(content_parts)
        
        # Save full file with transcript
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Saved transcript to: {filepath}")
        
        # Save summary-only version if summary exists
        if summary:
            summary_filename = f"summary_{video_metadata['upload_date']}_{safe_title}.md"
            summary_filepath = channel_dir / summary_filename
            
            summary_content = f"""# {video_metadata['title']}

**Channel:** {video_metadata['channel']}
**Upload Date:** {video_metadata['upload_date']}
**URL:** {video_metadata['url']}
**Duration:** {video_metadata['duration'] // 60} minutes

## Description

{video_metadata.get('description', 'No description available')}

## AI Summary

{summary}
"""
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            logger.info(f"Saved summary to: {summary_filepath}")
        
        return str(filepath)
    
    def get_existing_video_ids(self, channel_name: str) -> set:
        """
        Get list of video IDs that have already been downloaded
        
        Args:
            channel_name: Name of the channel
            
        Returns:
            Set of video IDs
        """
        channel_dir = self.output_dir / self.sanitize_filename(channel_name)
        if not channel_dir.exists():
            return set()
        
        video_ids = set()
        
        # Read existing markdown files to extract video IDs
        for md_file in channel_dir.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract URL from the markdown
                    url_match = re.search(r'\*\*URL:\*\* https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', content)
                    if url_match:
                        video_ids.add(url_match.group(1))
            except Exception as e:
                logger.warning(f"Could not read file {md_file}: {e}")
        
        return video_ids
    
    def merge_filtered_videos(self, channel_name: str, filtered_videos: List[Dict], 
                             merge_filename: str) -> Tuple[str, str]:
        """
        Merge all filtered videos (existing and new) into two files:
        1. Full transcripts merged file
        2. Summaries only merged file
        
        Args:
            channel_name: Name of the channel
            filtered_videos: List of filtered video dictionaries
            merge_filename: Name for the merged file
            
        Returns:
            Tuple of (full transcripts filepath, summaries filepath)
        """
        channel_dir = self.output_dir / self.sanitize_filename(channel_name)
        
        # Generate merge filenames
        if merge_filename == 'auto':
            current_date = datetime.now().strftime('%Y-%m-%d')
            merge_filename = f"{current_date}_merge.md"
            summary_merge_filename = f"summary_{current_date}_merge.md"
        else:
            if not merge_filename.endswith('.md'):
                merge_filename = f"{merge_filename}.md"
            # Create summary filename from the base name
            base_name = merge_filename[:-3] if merge_filename.endswith('.md') else merge_filename
            summary_merge_filename = f"summary_{base_name}.md"
            
        merge_filepath = channel_dir / merge_filename
        summary_merge_filepath = channel_dir / summary_merge_filename
        
        # Get all filtered video IDs
        filtered_video_ids = {video['id'] for video in filtered_videos}
        
        # Find existing transcript and summary files for filtered videos
        existing_full_files = []
        existing_summary_files = []
        seen_video_ids_full = set()  # Track which video IDs we've already added
        seen_video_ids_summary = set()
        
        if channel_dir.exists():
            for md_file in channel_dir.glob("*.md"):
                # Skip merge files themselves (any file with 'merge' in the name)
                if 'merge' in md_file.name.lower() or md_file.name in [merge_filename, summary_merge_filename]:
                    continue
                    
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract video ID from the markdown (only first match to avoid duplicates)
                        url_match = re.search(r'\*\*URL:\*\* https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', content)
                        
                        if url_match:
                            video_id = url_match.group(1)
                            if video_id in filtered_video_ids:
                                if md_file.name.startswith('summary_'):
                                    if video_id not in seen_video_ids_summary:
                                        existing_summary_files.append((md_file, content))
                                        seen_video_ids_summary.add(video_id)
                                else:
                                    if video_id not in seen_video_ids_full:
                                        existing_full_files.append((md_file, content))
                                        seen_video_ids_full.add(video_id)
                except Exception as e:
                    logger.warning(f"Could not read file {md_file}: {e}")
        
        # Sort files by upload date (extracted from filename)
        def extract_date(file_tuple):
            filename = file_tuple[0].name
            # Handle both regular and summary filenames
            filename = filename.replace('summary_', '')
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
            if date_match:
                return date_match.group(1)
            return '0000-00-00'  # Fallback for files without date
            
        existing_full_files.sort(key=extract_date)
        existing_summary_files.sort(key=extract_date)
        
        # Build merged content for FULL TRANSCRIPTS
        merged_content = [f"# {channel_name} - Merged Full Transcripts"]
        merged_content.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        merged_content.append(f"**Total Videos:** {len(existing_full_files)}")
        merged_content.append(f"**Type:** Full Transcripts with Timestamps")
        merged_content.append("\n" + "="*80 + "\n")
        
        for i, (file_path, content) in enumerate(existing_full_files, 1):
            logger.info(f"Adding full transcript {i}/{len(existing_full_files)} to merge: {file_path.name}")
            
            # Add separator
            merged_content.append(f"\n## Video {i}\n")
            
            # Add the full content
            merged_content.append(content)
            merged_content.append("\n" + "-"*80 + "\n")
        
        # Write merged FULL transcripts file
        if existing_full_files:
            final_content = '\n'.join(merged_content)
            with open(merge_filepath, 'w', encoding='utf-8') as f:
                f.write(final_content)
            logger.info(f"Merged {len(existing_full_files)} full transcripts into: {merge_filepath}")
        
        # Build merged content for SUMMARIES
        summary_merged_content = [f"# {channel_name} - Merged Summaries"]
        summary_merged_content.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_merged_content.append(f"**Total Videos:** {len(existing_summary_files)}")
        summary_merged_content.append(f"**Type:** AI Summaries Only")
        summary_merged_content.append("\n" + "="*80 + "\n")
        
        for i, (file_path, content) in enumerate(existing_summary_files, 1):
            logger.info(f"Adding summary {i}/{len(existing_summary_files)} to merge: {file_path.name}")
            
            # Add separator
            summary_merged_content.append(f"\n## Video {i}\n")
            
            # Add the content
            summary_merged_content.append(content)
            summary_merged_content.append("\n" + "-"*80 + "\n")
        
        # Write merged SUMMARIES file
        if existing_summary_files:
            summary_final_content = '\n'.join(summary_merged_content)
            with open(summary_merge_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_final_content)
            logger.info(f"Merged {len(existing_summary_files)} summaries into: {summary_merge_filepath}")
        
        return str(merge_filepath), str(summary_merge_filepath)
    
    def download_channel_transcripts(self, channel_url: str, languages: List[str] = ['en'], 
                                    limit: Optional[int] = None, force_redownload: bool = False,
                                    title_filter: Optional[str] = None, min_duration: Optional[int] = None,
                                    merge_output: Optional[str] = None):
        """
        Download all transcripts from a YouTube channel
        
        Args:
            channel_url: URL of the YouTube channel
            languages: List of language codes in order of preference
            limit: Maximum number of videos to process (for testing)
            force_redownload: If True, redownload even if file exists
            title_filter: Optional regex pattern to filter video titles
            min_duration: Optional minimum duration in minutes
            merge_output: If provided, merge all filtered videos into a single file
        """
        # Extract channel name
        # Handle URLs like https://www.youtube.com/@PeterAttiaMD or https://www.youtube.com/@PeterAttiaMD/videos
        url_parts = channel_url.rstrip('/').split('/')
        channel_name = None
        for part in url_parts:
            if part.startswith('@'):
                channel_name = part.replace('@', '')
                break
        
        # Fallback to old method if @ not found
        if not channel_name:
            channel_name = url_parts[-1] if url_parts[-1] != 'videos' else url_parts[-2]
            channel_name = channel_name.replace('@', '')
            
        logger.info(f"Processing channel: {channel_name}")
        
        # Get all videos from channel
        videos = self.get_channel_videos(channel_url)
        if not videos:
            logger.error("No videos found or error accessing channel")
            return
        
        # Apply title filter if specified
        if title_filter:
            try:
                import re
                pattern = re.compile(title_filter)
                original_count = len(videos)
                videos = [video for video in videos if pattern.search(video['title'])]
                logger.info(f"Title filter '{title_filter}' matched {len(videos)} out of {original_count} videos")
            except re.error as e:
                logger.error(f"Invalid regex pattern '{title_filter}': {e}")
                return
        
        # Apply duration filter if specified
        if min_duration:
            logger.info(f"Filtering videos with minimum duration of {min_duration} minutes...")
            original_count = len(videos)
            min_duration_seconds = min_duration * 60  # Convert minutes to seconds
            videos = [video for video in videos if video.get('duration', 0) >= min_duration_seconds]
            logger.info(f"Duration filter matched {len(videos)} out of {original_count} videos")
        
        # Get existing video IDs if not forcing redownload (after filtering)
        existing_ids = set() if force_redownload else self.get_existing_video_ids(channel_name)
        if existing_ids:
            logger.info(f"Found {len(existing_ids)} existing transcripts")
        
        # If merge mode, skip downloading and go straight to merging
        if merge_output:
            logger.info("Merge mode: Skipping downloads, using existing files only")
        else:
            # Apply limit if specified (only for download mode)
            if limit:
                videos = videos[:limit]
                logger.info(f"Limiting to first {limit} videos")
            
            # Process each video
            success_count = 0
            skip_count = 0
            fail_count = 0
            
            for i, video in enumerate(videos, 1):
                video_id = video['id']
                
                # Check if already downloaded
                if video_id in existing_ids:
                    logger.info(f"[{i}/{len(videos)}] Skipping {video['title']} - already downloaded")
                    skip_count += 1
                    continue
                
                logger.info(f"[{i}/{len(videos)}] Processing: {video['title']}")
                
                # Get full metadata
                metadata = self.get_video_metadata(video_id)
                if not metadata:
                    logger.warning(f"Could not get metadata for {video_id}")
                    fail_count += 1
                    continue
                
                # Download transcript
                transcript_result = self.download_transcript(video_id, languages)
                if transcript_result:
                    transcript_text, transcript_data = transcript_result
                    
                    # Generate summary if Claude is enabled
                    summary = None
                    if self.use_claude:
                        # Use formatted transcript for better readability
                        formatted_transcript = self.format_transcript_with_timestamps(transcript_data)
                        summary = self.generate_summary(
                            formatted_transcript, 
                            channel_name, 
                            metadata['title']
                        )
                    
                    # Save transcript with summary
                    self.save_transcript(metadata, transcript_text, transcript_data, channel_name, summary)
                    success_count += 1
                else:
                    logger.warning(f"No transcript available for: {video['title']}")
                    fail_count += 1
                
                # Small delay to be respectful to the API
                time.sleep(1)
            
            # Summary
            logger.info(f"\n{'='*50}")
            logger.info(f"Download Complete!")
            logger.info(f"Successfully downloaded: {success_count}")
            logger.info(f"Skipped (already exist): {skip_count}")
            logger.info(f"Failed/No transcript: {fail_count}")
            logger.info(f"Total processed: {len(videos)}")
        
        # Merge videos if requested
        if merge_output:
            logger.info(f"\n{'='*50}")
            logger.info(f"Merging filtered videos...")
            # Get the original filtered videos list (before limit was applied)
            all_filtered_videos = self.get_channel_videos(channel_url)
            
            # Apply same filters as before
            if title_filter:
                import re
                pattern = re.compile(title_filter)
                all_filtered_videos = [video for video in all_filtered_videos if pattern.search(video['title'])]
            
            if min_duration:
                min_duration_seconds = min_duration * 60
                all_filtered_videos = [video for video in all_filtered_videos if video.get('duration', 0) >= min_duration_seconds]
            
            full_merge_path, summary_merge_path = self.merge_filtered_videos(channel_name, all_filtered_videos, merge_output)
            logger.info(f"Merge complete!")
            logger.info(f"  Full transcripts: {full_merge_path}")
            logger.info(f"  Summaries only: {summary_merge_path}")


def main():
    parser = argparse.ArgumentParser(description='Download YouTube channel transcripts with AI summarization')
    parser.add_argument('channel_url', help='YouTube channel URL')
    parser.add_argument('--output-dir', '-o', default='transcripts', 
                       help='Output directory for transcripts (default: transcripts)')
    parser.add_argument('--languages', '-l', nargs='+', default=['en'],
                       help='Language codes in order of preference (default: en)')
    parser.add_argument('--limit', '-n', type=int, 
                       help='Limit number of videos to download (for testing)')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force redownload even if transcript exists')
    parser.add_argument('--no-summary', action='store_true',
                       help='Disable AI summarization with Claude')
    parser.add_argument('--title-filter', '-t', type=str,
                       help='Regex pattern to filter video titles (e.g., "^\\d+" for titles starting with numbers)')
    parser.add_argument('--min-duration', '-d', type=int,
                       help='Minimum video duration in minutes (e.g., 60 for videos longer than 1 hour)')
    parser.add_argument('--merge', type=str, nargs='?', const='auto',
                       help='Merge all filtered videos into a single file. Optionally specify filename (default: YYYY-MM-DD_merge.md)')
    
    args = parser.parse_args()
    
    # Create downloader and run
    downloader = YouTubeTranscriptDownloader(
        output_dir=args.output_dir,
        use_claude=not args.no_summary
    )
    downloader.download_channel_transcripts(
        channel_url=args.channel_url,
        languages=args.languages,
        limit=args.limit,
        force_redownload=args.force,
        title_filter=args.title_filter,
        min_duration=args.min_duration,
        merge_output=args.merge
    )


if __name__ == '__main__':
    main()