# Lightmark

Upload photos, scans or PDFs of set and lighting drawings marked up with coloured highlighter, then switch the lights on and off by layer (wattage, voltage, bulb type, cap). Anyone with the link and the password can view, upload and edit.

## How it fits together

- `index.html` is the whole site. GitHub Pages serves it.
- Drawings are stored in a Supabase database. The database checks the password on every request (`supabase-setup.sql`), so it is not stored in the page.

## Setup

1. In Supabase, open SQL Editor, paste in `supabase-setup.sql` and run it. To change the password, edit `'potter'` in that file and run it again.
2. If you set the database up before folders existed, also run `supabase-folders.sql` once.
3. Put the Supabase Project URL and anon public key into `CONFIG` near the bottom of `index.html`.
4. In GitHub, go to Settings → Pages, set Source to "Deploy from a branch", pick `main` and `/ (root)`, and save.
