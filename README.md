# Message Information Bot

A lightweight **Discord utility bot** that provides deep inspection of any message by its ID.

## Features

### Main Commands
- `=message <message_id>`  
  Searches **every channel and thread** in the server and returns a rich, detailed view including:
  - Content preview + length/word count
  - Author details (avatar, banner, roles, join dates)
  - Activity, Application, and Interaction info
  - Full attachment metadata
  - Reactions, mentions, flags, timestamps, etc.
  - "Jump to Message" button

- `=checkreactions <message_id>`  
  For each reaction on the message:
  - Shows count and burst count
  - Lists members who **have not reacted** (with mentions)
  - Automatically chunks long lists

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Requirements

- Python 3.10+
- Discord Bot Token with:
  - `Server Members Intent`
  - `Message Content Intent`
  - `Read Message History` permission in channels

## Permissions

The bot needs:
- `Read Message History`
- `View Channels` (in all channels you want to search)

## Commands

| Command                  | Description                              | Example                  |
|--------------------------|------------------------------------------|--------------------------|
| `=message <id>`          | Full message details                     | `=message 1234567890`    |
| `=checkreactions <id>`   | Reaction participation analysis          | `=checkreactions 1234567890` |

---
