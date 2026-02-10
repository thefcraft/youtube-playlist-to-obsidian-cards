# youtube-playlist-to-obsidian-cards

A small CLI that turns a YouTube playlist into Obsidian “cardlink” blocks so you can track videos as todos inside Obsidian (works nicely with **Auto Card Link** `Community plugin`).

It scrapes YouTube’s internal API (the same data your browser sees), follows playlist continuations, and outputs a Markdown file where each video becomes a checklist item + cardlink.

I built this because I wanted:

- a checklist for long playlists,
- proper card previews in Obsidian,
- and something I could regenerate later without manual cleanup.

---

## What you get

For each video, you’ll get something like this:

```md
1. [ ] **"Some Video Title"**
'''cardlink
url: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&index=1
title: "Some Video Title"
host: www.youtube.com
favicon: https://m.youtube.com/static/favicon.ico
image: https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg
'''

```

- The checkbox works as a todo.
- Auto Card Link renders a nice preview.
- The index stays in sync with the playlist.

---

## Install

```bash
git clone https://github.com/thefcraft/youtube-playlist-to-obsidian-cards.git
cd youtube-playlist-to-obsidian-cards
uv sync
```

(If you’re using poetry/pipenv/pip, adapt accordingly.)

---

## Usage

Basic:

```bash
uv run main.py "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

This will:

- fetch the playlist,
- generate all cards,
- and write them to `<playlist_title>.md` in the `output` folder.

### Custom output file

```bash
python main.py "https://www.youtube.com/..." -o todos.md
```

### Change directory first (useful if you keep notes in a folder)

```bash
python main.py "https://youtu.be/..." -C notes/youtube
```

### Print to stdout (for piping)

```bash
python main.py "https://youtu.be/..." --stdout > playlist.md
```

### Overwrite an existing file

```bash
python main.py "https://youtu.be/..." -o playlist.md --force
```

---

## Recommended Obsidian setup

Install these plugins:

- **Auto Card Link**  
  - Enable it.
  - Make sure it renders fenced `cardlink` blocks.

Optional but nice:

- Checklist plugin (if you prefer better task UI).

---

## Limitations

- This is not the official YouTube API — it relies on their internal endpoints.  
  If YouTube changes something, this might break.
- Descriptions are not fetched (deliberately).

---

## Why this exists

I kept losing track of:

- which videos I watched,
- which ones were useful,
- and which ones I should revisit.

This turns a playlist into something you can actually manage inside Obsidian.

---

## License

MIT. Do whatever you want with it.
