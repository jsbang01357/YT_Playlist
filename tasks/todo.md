# Todo

- [x] Analyze `playlist.py` dependencies and runtime behavior.
- [x] Update `requirements.txt` to match the script.
- [x] Verify the Python file still compiles.
- [x] Create a uv virtual environment and install `requirements.txt`.
- [x] Add playlist URL extraction mode.
- [x] Verify playlist ID parsing and Python compilation.
- [x] Add Streamlit dependency and project ignore rules.
- [x] Split YouTube API logic into `youtube_client.py`.
- [x] Add playlist/video URL parsing utilities in `playlist_tools.py`.
- [x] Add local JSON storage in `storage.py`.
- [x] Build Streamlit app shell in `app.py`.
- [x] Add OAuth connection status UI.
- [x] Implement playlist list view.
- [x] Implement playlist detail and video URL extraction.
- [x] Add TXT/CSV download buttons.
- [x] Implement playlist creation.
- [x] Implement bulk video URL add.
- [x] Verify app locally with `.venv`.
- [x] Add OAuth client diagnostics and fixed local callback URI.
- [x] Add CSV upload parser for playlist creation.
- [x] Add Streamlit CSV playlist creation tab.
- [x] Verify CSV import samples and Python compilation.
- [x] Add local daily quota usage tracker.
- [x] Record quota units from YouTube API calls.
- [x] Show today's estimated quota in the sidebar.
- [x] Verify quota tracking calculations.
- [x] Organize root files into `src/`, `scripts/`, `inputs/`, and `secrets/`.
- [x] Update app, CLI, and VS Code launch paths after the move.
- [x] Verify Streamlit starts from `src/app.py`.

## Summary

- `playlist.py` is a YouTube Data API script that reads an Excel workbook, groups songs by category, creates private playlists, searches one video per song, and inserts each result into the matching playlist.
- `requirements.txt` now includes the Google API/OAuth clients and `openpyxl` for reading `.xlsx` files with pandas.
- Verified with `python3 -m py_compile playlist.py`.
- Created `.venv` with uv using Python 3.12.13, installed `requirements.txt`, and verified the installed imports with `.venv/bin/python`.
- Added `--extract-urls` mode to read a playlist URL or ID, fetch every video URL through the YouTube Data API, and optionally save results to `.txt` or `.csv`.
- Added a local Streamlit app for OAuth connection status, playlist listing, playlist detail export, playlist creation, bulk video URL add, URL extraction, and JSON caching.
- Diagnosed Web application OAuth clients and fixed the local callback URI to `http://localhost:8080/`.
- Added CSV upload playlist creation that accepts exported `title, video_id, url` files and URL-only CSV files.
- Added local daily quota tracking in `data/quota_usage.json`, sidebar quota display, and batch operation estimates.
- Moved Streamlit source files into `src/`, the legacy CLI into `scripts/`, the Excel input into `inputs/`, and OAuth files into `secrets/`; updated path constants and launch settings.
