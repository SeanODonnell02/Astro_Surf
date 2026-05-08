# Sims 4 Auto Save 💾

Never lose hours of gameplay to a crash again.

## What it does

Runs quietly in the background while you play. Every few minutes it copies your
Sims 4 Saves folder to a rolling set of timestamped backups. If the game crashes
you just restore the most recent backup — no progress lost.

## Setup (one time)

1. Make sure Python 3.9+ is installed — download from https://python.org
2. Open a terminal / command prompt in this folder and run:

```
pip install psutil
```

## Running it

Double-click **autosave.py**, or from a terminal:

```
python autosave.py
```

## Using it

| Setting | What it does |
|---|---|
| **Saves folder** | Where The Sims 4 stores your saves. Auto-detected but you can change it. |
| **Backup folder** | Where backups are written. Default: `Documents/Sims4_AutoBackups` |
| **Every N minutes** | How often a backup runs while the game is open. 10 min is a good default. |
| **Keep N backups** | How many rolling backups to keep. Old ones are deleted automatically. |

Hit **▶ Start Auto Save** before you start playing — the app will watch for the
game process and back up on schedule whenever it's running.

Use **Save Now** to take an instant backup at any point.

## Restoring a backup

1. Close The Sims 4
2. Open `Documents/Sims4_AutoBackups`
3. Copy the files from the most recent `backup_YYYY-MM-DD_HH-MM-SS` folder
   into your `Documents/Electronic Arts/The Sims 4/Saves` folder
4. Launch the game and load normally

## Default save locations

| OS | Path |
|---|---|
| Windows | `C:\Users\YOU\Documents\Electronic Arts\The Sims 4\Saves` |
| macOS | `~/Documents/Electronic Arts/The Sims 4/Saves` |
