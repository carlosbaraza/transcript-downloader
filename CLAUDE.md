# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Channel Transcript Downloader with AI Summarization - A Python tool to download YouTube video transcripts, generate AI summaries using Claude, and archive them as organized markdown files.

## Commands

### Install dependencies:
```bash
pip install -r requirements.txt
```

### Download transcripts from a channel:
```bash
python youtube_transcript_downloader.py <CHANNEL_URL> [options]
```

Options:
- `--limit N`: Download only N videos (useful for testing)
- `--languages en es`: Specify language preferences
- `--output-dir DIR`: Custom output directory
- `--force`: Redownload even if transcript exists

### Example usage:
```bash
# Download all from Peter Attia's channel
python youtube_transcript_downloader.py https://www.youtube.com/@PeterAttiaMD/videos

# Test with first 5 videos
python youtube_transcript_downloader.py https://www.youtube.com/@PeterAttiaMD/videos --limit 5
```

## Project Structure

```
youtube-transcripts/
├── youtube_transcript_downloader.py  # Main script
├── requirements.txt                  # Python dependencies
├── README.md                         # User documentation
└── transcripts/                      # Output directory (gitignored)
    └── ChannelName/                  # Channel-specific folders
        ├── YYYY-MM-DD_Title.md       # Full transcript with AI summary
        └── summary_YYYY-MM-DD_Title.md # Summary only (no transcript)
```

## Key Features

- Downloads transcripts from any YouTube channel
- AI summarization using Claude 3.5 Sonnet API
- Channel-specific summarization prompts (Peter Attia, Huberman Lab, TED, etc.)
- Saves as markdown with timestamps and metadata
- Creates separate summary files for quick reference
- Skips already downloaded videos on subsequent runs
- Handles both manual and auto-generated subtitles
- Supports multiple languages with fallback
- Organized file structure by channel and date

## Environment Variables

- `ANTHROPIC_API_KEY`: Required for AI summarization features

## Configuration Files

- `channel_prompts.json`: Contains channel-specific AI prompts for customized summaries
- `.env`: Stores API keys (not committed to git)