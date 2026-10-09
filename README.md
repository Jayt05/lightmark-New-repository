# Lightmark

Upload photos, scans or PDFs of set and lighting drawings marked up with coloured highlighter, then switch the lights on and off by layer (wattage, voltage, bulb type, cap). Anyone with the link and the password can view, upload and edit.

## How it fits together

- `index.html` is the whole site. GitHub Pages serves it.
- Drawings are stored in a Supabase database. The database checks the password on every request (`supabase-setup.sql`), so it is not stored in the page.

## Setup

1. In Supabase, open SQL Editor, paste in `supabase-setup.sql` and run it. To change the password, replace `'change-me'` in that file with your own password (upper and lower case count) and run it again.
2. If you set the database up before folders existed, also run `supabase-folders.sql` once.
3. Put the Supabase Project URL and anon public key into `CONFIG` near the bottom of `index.html`.
4. In GitHub, go to Settings → Pages, set Source to "Deploy from a branch", pick `main` and `/ (root)`, and save.

## Running at home instead (Raspberry Pi)

To keep drawings off the internet, Lightmark can run on a Raspberry Pi or any always-on Linux computer on your home network. The page is the same; `pi/server.py` stores everything in a SQLite file on that machine instead of Supabase.

1. On the Pi, get this folder (for example `git clone` this repository, or copy the folder across on a USB stick).
2. Run `sudo bash pi/install.sh` from inside it and choose a password.
3. Open the address it prints, such as `http://raspberrypi.local:8080`, on any device on the same Wi-Fi.

The Pi version blocks a device for 15 minutes after 5 wrong passwords, and its password is case-sensitive.

Run the same command again after updating the folder to install a new version; drawings and the password are kept. Use **Export all** on one Lightmark and **Import** on another to move drawings between them.
