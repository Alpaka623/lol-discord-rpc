# League of Legends Discord Rich Presence

A Python script that displays your current League of Legends or TFT game status in Discord, including champion GIFs, KDA, and game phase.

## Features
- Displays current Champion (with GIF from Giphy)
- Supports TFT (with Level and Placement)
- Displays KDA and game duration
- Optional profile buttons (u.gg / MetaTFT)
- Automatic League Client detection

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your details:
   - `GIPHY_API_KEY`: Get one for free at [Giphy Developers](https://developers.giphy.com/).
   - `PROFILE_LINK_LOL` / `PROFILE_LINK_TFT`: Your profile links (optional).
   - `LEAGUE_LOCKFILE_PATH`: Usually detected automatically, but can be set manually.

## Usage
Run the script while League of Legends is open:
```bash
python rpc.py
```

## Requirements
- Windows (League Client required)
- Discord Desktop App
- Python 3.8+

## Important Note
- **RPC Priority:** To prevent the default League of Legends Rich Presence from overriding this script, you should start **both Discord and your Terminal (e.g., PowerShell or CMD) as Administrator**. This ensures the script's presence stays on top of the default game status.
