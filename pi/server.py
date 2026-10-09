#!/usr/bin/env python3
"""Lightmark home server: serves the Lightmark page and keeps every drawing in a
SQLite file on this machine, so nothing leaves your network.

Run:  python3 server.py --set-password      (once, to choose the password)
      python3 server.py                     (starts on port 8080)

It answers the same small set of requests the page makes to Supabase, so the
page works unchanged. Only the Python standard library is used.
"""
import argparse, getpass, hashlib, hmac, json, os, re, secrets, sqlite3, sys, threading, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('LIGHTMARK_DATA', os.path.join(HERE, 'data'))
DB_PATH = os.path.join(DATA, 'lightmark.db')
PASS_PATH = os.path.join(DATA, 'password.json')
PAGE_PATH = os.path.join(HERE, 'index.html')
MAX_BODY = 40 * 1024 * 1024  # a large phone photo, base64-encoded, fits comfortably

TABLES = {
    'folders': ['id', 'name', 'created'],
    'drawings': ['id', 'name', 'w', 'h', 'created', 'ai', 'thumb', 'layers', 'marks', 'folder'],
    'drawing_images': ['id', 'data'],
}
JSON_COLS = {'layers', 'marks'}
lock = threading.Lock()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('pragma foreign_keys = on')
    return con


def init_db():
    os.makedirs(DATA, exist_ok=True)
    with db() as con:
        con.executescript('''
          create table if not exists folders (id text primary key, name text not null, created text not null);
          create table if not exists drawings (
            id text primary key, name text not null, w integer not null, h integer not null, created text not null,
            ai integer not null default 0, thumb text, layers text not null default '[]', marks text not null default '[]',
            folder text references folders(id) on delete set null);
          create table if not exists drawing_images (id text primary key references drawings(id) on delete cascade, data text not null);
        ''')


def hash_password(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    return {'salt': salt, 'hash': hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(salt), 200_000).hex()}


def password_ok(pw):
    try:
        stored = json.load(open(PASS_PATH))
    except FileNotFoundError:
        return False
    return hmac.compare_digest(hash_password(pw, stored['salt'])['hash'], stored['hash'])


def row_out(table, row):
    out = dict(row)
    for c in JSON_COLS & out.keys():
        out[c] = json.loads(out[c] or '[]')
    if 'ai' in out:
        out['ai'] = bool(out['ai'])
    return out


def clean(table, body, creating):
    cols = TABLES[table]
    vals = {k: v for k, v in body.items() if k in cols and k not in ('created',)}
    if creating:
        vals.setdefault('id', str(uuid.uuid4()))
        if table != 'drawing_images':
            vals['created'] = datetime.now(timezone.utc).isoformat()
    for c in JSON_COLS & vals.keys():
        vals[c] = json.dumps(vals[c])
    if 'ai' in vals:
        vals['ai'] = 1 if vals['ai'] else 0
    return vals


class Handler(BaseHTTPRequestHandler):
    server_version = 'Lightmark'

    def log_message(self, fmt, *args):  # keep the journal quiet apart from errors
        pass

    def send(self, code, body=None, ctype='application/json'):
        data = b'' if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > MAX_BODY:
            raise ValueError('too large')
        raw = self.rfile.read(n) if n else b''
        return json.loads(raw) if raw else {}

    def route(self, method):
        url = urlparse(self.path)
        if method == 'GET' and url.path in ('/', '/index.html'):
            page = open(PAGE_PATH, encoding='utf-8').read()
            page = re.sub(r"const CONFIG = \{.*?\};", "const CONFIG = { url: location.origin, key: 'home-server', local: true };", page, count=1, flags=re.S)
            return self.send(200, page.encode(), 'text/html; charset=utf-8')
        if not url.path.startswith('/rest/v1/'):
            return self.send(404, {'message': 'not found'})
        name = url.path[len('/rest/v1/'):]
        pw_ok = password_ok((self.headers.get('x-lightmark-pass') or '').strip())
        if name == 'rpc/lm_pass_ok':
            return self.send(200, pw_ok)
        if name not in TABLES:
            return self.send(404, {'message': 'not found'})
        if not pw_ok:
            return self.send(200, []) if method == 'GET' else self.send(401, {'message': 'wrong password'})
        q = parse_qs(url.query)
        idv = (q.get('id', [''])[0])
        rid = idv[3:] if idv.startswith('eq.') else None
        with lock, db() as con:
            if method == 'GET':
                cols = [c for c in (q.get('select', ['*'])[0]).split(',') if c in TABLES[name]] or TABLES[name]
                sql = f'select {",".join(cols)} from {name}'
                args = []
                if rid is not None:
                    sql += ' where id = ?'; args.append(rid)
                order = q.get('order', [''])[0]
                m = re.fullmatch(r'(\w+)\.(asc|desc)', order)
                if m and m.group(1) in TABLES[name]:
                    sql += f' order by {m.group(1)} {m.group(2)}'
                return self.send(200, [row_out(name, r) for r in con.execute(sql, args)])
            if method == 'POST':
                vals = clean(name, self.body(), True)
                con.execute(f'insert into {name} ({",".join(vals)}) values ({",".join("?" * len(vals))})', list(vals.values()))
                row = con.execute(f'select * from {name} where id = ?', [vals['id']]).fetchone()
                if 'return=representation' in (self.headers.get('Prefer') or ''):
                    return self.send(201, [row_out(name, row)])
                return self.send(201)
            if rid is None:
                return self.send(400, {'message': 'id required'})
            if method == 'PATCH':
                vals = clean(name, self.body(), False); vals.pop('id', None)
                if vals:
                    con.execute(f'update {name} set {",".join(k + " = ?" for k in vals)} where id = ?', [*vals.values(), rid])
                return self.send(204)
            if method == 'DELETE':
                con.execute(f'delete from {name} where id = ?', [rid])
                return self.send(204)
        return self.send(405, {'message': 'method not allowed'})

    def handle_method(self, method):
        try:
            self.route(method)
        except ValueError:
            self.send(413, {'message': 'file too large'})
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.send(400, {'message': str(e)})

    def do_GET(self): self.handle_method('GET')
    def do_POST(self): self.handle_method('POST')
    def do_PATCH(self): self.handle_method('PATCH')
    def do_DELETE(self): self.handle_method('DELETE')


def main():
    ap = argparse.ArgumentParser(description='Lightmark home server')
    ap.add_argument('--port', type=int, default=int(os.environ.get('LIGHTMARK_PORT', 8080)))
    ap.add_argument('--set-password', action='store_true', help='choose the password, then exit')
    a = ap.parse_args()
    init_db()
    if a.set_password:
        pw = getpass.getpass('New Lightmark password: ').strip()
        if len(pw) < 8 or pw != getpass.getpass('Type it again: ').strip():
            sys.exit('Passwords must match and be at least 8 characters.')
        with open(PASS_PATH, 'w') as f:
            json.dump(hash_password(pw), f)
        os.chmod(PASS_PATH, 0o600)
        print('Password saved.')
        return
    if not os.path.exists(PASS_PATH):
        sys.exit('Set a password first: python3 server.py --set-password')
    print(f'Lightmark is running on port {a.port}')
    ThreadingHTTPServer(('0.0.0.0', a.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
