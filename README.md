# YouTube Channel Transcript Downloader with AI Summarization

A Python tool to download all transcripts from any YouTube channel, generate AI summaries using Claude, and save them as organized markdown files.

## Features

- Downloads all video transcripts from a YouTube channel
- **AI-powered summarization using Claude 3.5 Sonnet**
- **Channel-specific summarization prompts** (customized for Peter Attia, Huberman Lab, TED, etc.)
- Saves transcripts as markdown files with timestamps
- Creates separate summary-only files for quick reference
- Organizes files by channel and date
- Skips already downloaded videos on subsequent runs
- Supports multiple languages
- Handles both manual and auto-generated subtitles

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Set up Claude API for AI summarization:
   - Get an API key from [Anthropic Console](https://console.anthropic.com/)
   - Create a `.env` file:
   ```bash
   cp .env.example .env
   ```
   - Add your API key to the `.env` file:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

## Usage

### Basic usage - Download all transcripts from Peter Attia's channel:

```bash
python youtube_transcript_downloader.py https://www.youtube.com/@PeterAttiaMD/videos
```

### Download from any channel:

```bash
python youtube_transcript_downloader.py <CHANNEL_URL>
```

### Options:

- `--output-dir, -o`: Specify output directory (default: `transcripts`)
- `--languages, -l`: Language codes in order of preference (default: `en`)
- `--limit, -n`: Limit number of videos to download (useful for testing)
- `--force, -f`: Force redownload even if transcript already exists
- `--no-summary`: Disable AI summarization (useful if no API key)

### Examples:

Download only the first 5 videos for testing:
```bash
python youtube_transcript_downloader.py https://www.youtube.com/@PeterAttiaMD/videos --limit 5
```

Download with Spanish preference, fallback to English:
```bash
python youtube_transcript_downloader.py <CHANNEL_URL> --languages es en
```

Save to custom directory:
```bash
python youtube_transcript_downloader.py <CHANNEL_URL> --output-dir my_transcripts
```

## Output Structure

Transcripts are saved in the following structure:
```
transcripts/
└── ChannelName/
    ├── 2024-01-15_Video_Title_One.md              # Full transcript with AI summary
    ├── summary_2024-01-15_Video_Title_One.md      # Summary only (no transcript)
    ├── 2024-01-20_Another_Video_Title.md
    ├── summary_2024-01-20_Another_Video_Title.md
    └── ...
```

Each markdown file contains:
- Video title
- Channel name
- Upload date
- Video URL
- Duration
- Description
- **AI-generated summary** (if Claude API is configured)
- Full transcript with timestamps

## AI Summarization

### Channel-Specific Prompts

The tool includes customized prompts for popular channels:

- **Peter Attia (The Drive)**: Extracts health tips, supplements, exercise protocols, biomarkers, and scientific references
- **Huberman Lab**: Focuses on neuroscience protocols, behavioral tools, and implementation priorities
- **TED Talks**: Highlights big ideas, innovations, and actionable takeaways
- **Default**: Provides comprehensive summaries with key points and references

### Customizing Prompts

Edit `channel_prompts.json` to add or modify channel-specific prompts. Each channel can have:
- Custom system prompt for context
- Detailed user prompt template with specific sections

## Features

- **Incremental Downloads**: The tool tracks which videos have already been downloaded and skips them on subsequent runs
- **Error Handling**: Continues processing even if individual videos fail
- **Rate Limiting**: Includes delays between requests to be respectful to YouTube's API
- **Flexible Language Support**: Can prioritize multiple languages and fall back to available options

## Notes

- Some videos may not have transcripts available
- Age-restricted videos may not be accessible
- The tool uses unofficial YouTube APIs which may change