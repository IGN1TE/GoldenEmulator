"""GoldenEmulator Stage 4. Standard-library Windows launcher; no shell commands."""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser

SYSTEMS = {
    'GameCube': ('Dolphin', {'.iso', '.gcm', '.rvz', '.ciso'}),
    'Xbox 360': ('Xenia', {'.iso', '.xex'}),
    'PlayStation 2': ('PCSX2', {'.iso', '.bin', '.chd', '.cso', '.cue'}),
    'PlayStation 5': ('Not connected', {'.pkg', '.bin'}),
}
PORT = 48761
MAX_BYTES = 50 * 1024 * 1024


def validate_state(value):
    if not isinstance(value, dict) or value.get('version') != 2 or not isinstance(value.get('games'), list) or len(value['games']) > 5000:
        raise ValueError('Invalid library backup.')
    ids, keys, games = set(), set(), []
    for g in value['games']:
        if not isinstance(g, dict):
            raise ValueError('Invalid game entry.')
        for field, limit in [('id', 200), ('title', 200), ('path', 4096), ('system', 100)]:
            if not isinstance(g.get(field), str) or not g[field].strip() or len(g[field]) > limit:
                raise ValueError('Invalid game ' + field + '.')
        if g['id'] in ids or g['system'] not in SYSTEMS:
            raise ValueError('Duplicate ID or unknown console.')
        key = (g['system'], str(g.get('nativePath') or g['path']).casefold())
        if key in keys:
            raise ValueError('Duplicate game file.')
        ids.add(g['id']); keys.add(key)
        clean = {k: g[k] for k in ['id', 'title', 'path', 'system']}
        for k in ['size', 'modified', 'added', 'lastPlayed', 'launchCount']:
            n = g.get(k, 0)
            if isinstance(n, bool) or not isinstance(n, (float, int)) or not 0 <= n <= 10**18:
                raise ValueError('Invalid game number.')
            clean[k] = n
        for k, limit in [('notes', 2000), ('nativePath', 4096), ('format', 16), ('cover', 2500000)]:
            text = g.get(k, '')
            if not isinstance(text, str) or len(text) > limit or '\x00' in text:
                raise ValueError('Invalid game ' + k + '.')
            clean[k] = text
        if clean['cover']:
            import re
            if not re.fullmatch(r'data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+', clean['cover']):
                raise ValueError('Invalid cover image.')
        clean['favorite'] = g.get('favorite') is True
        games.append(clean)
    result = {'version': 2, 'games': games}
    if len(json.dumps(result).encode()) > 45 * 1024 * 1024:
        raise ValueError('Library exceeds the 45 MB review-build limit.')
    return result


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def launch_arguments(system, exe, game):
    if system == 'GameCube': return [str(exe), '-b', '-e', str(game)]
    if system == 'Xbox 360': return [str(exe), str(game)]
    if system == 'PlayStation 2': return [str(exe), '-batch', '--', str(game)]
    raise ValueError('PS5 launching is not connected. No compatibility is implied.')


def scan_folder(folder, system):
    if system not in SYSTEMS: raise ValueError('Unknown console.')
    root = Path(folder).resolve(strict=True)
    if not root.is_dir(): raise ValueError('Choose a game folder.')
    files, warnings, seen = [], [], 0
    def onerror(error): warnings.append('A subfolder could not be read.')
    for base, dirs, names in os.walk(root, followlinks=False, onerror=onerror):
        # Do not follow junctions/symlinks outside the selected folder.
        dirs[:] = [d for d in dirs if not Path(base, d).is_symlink() and not (getattr(Path(base, d), 'is_junction', lambda: False)())]
        for name in names:
            seen += 1
            if seen > 20000: raise ValueError('Choose a smaller folder (under 20,000 files).')
            p = Path(base, name)
            if p.is_symlink(): continue
            try:
                info = p.stat()
                files.append({'name':name, 'webkitRelativePath':root.name+'/'+p.relative_to(root).as_posix(), 'size':info.st_size, 'lastModified':int(info.st_mtime*1000), 'nativePath':str(p.resolve())})
            except OSError:
                warnings.append('A file could not be read.')
    return {'files':files, 'warnings':len(warnings), 'folder':str(root)}


class Launcher:
    def __init__(self, data_dir, picker=None, popen=subprocess.Popen):
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir/'library.json'
        self.config_file = self.data_dir/'emulators.json'
        self.lock = threading.RLock()
        self.picker = picker
        self.popen = popen
        self.process = None
        self.process_game = None
        self.last_exit = None
        self.state = {'version':2, 'games':[]}
        self.config = {}
        # Fail visibly instead of silently overwriting a damaged library.
        if self.state_file.exists(): self.state = validate_state(json.loads(self.state_file.read_text(encoding='utf-8')))
        if self.config_file.exists():
            raw = json.loads(self.config_file.read_text(encoding='utf-8'))
            if not isinstance(raw, dict): raise ValueError('Emulator settings are damaged.')
            self.config = {s:p for s,p in raw.items() if s in SYSTEMS and isinstance(p,str)}

    def save(self, data):
        new = validate_state(data)
        with self.lock:
            # Playback metadata is maintained by the launcher, not stale UI copies.
            old = {g['id']:g for g in self.state['games']}
            for g in new['games']:
                for k in ['lastPlayed', 'launchCount']:
                    g[k] = max(g.get(k,0), old.get(g['id'],{}).get(k,0))
            atomic_json(self.state_file,new); self.state=new
        return new

    def configurations(self):
        return {s:{'name':name,'path':self.config.get(s,''),'exists':Path(self.config[s]).is_file() if self.config.get(s) else False,'supported':s!='PlayStation 5'} for s,(name,_) in SYSTEMS.items()}

    def choose_emulator(self, system):
        if system not in SYSTEMS or system=='PlayStation 5': raise ValueError('This console has no launch integration.')
        path = self.picker('emulator', system)
        if not path: return {'cancelled':True}
        exe = Path(path).resolve(strict=True)
        if not exe.is_file() or exe.suffix.lower()!='.exe': raise ValueError('Choose the installed emulator EXE.')
        with self.lock:
            new = dict(self.config); new[system]=str(exe)
            atomic_json(self.config_file,new); self.config=new
        return self.configurations()

    def locate(self, gid):
        with self.lock:
            g = next((g for g in self.state['games'] if g['id']==gid),None)
            if not g: raise ValueError('Game is no longer in the library.')
            system=g['system']
        path=self.picker('game',system)
        if not path:return {'cancelled':True}
        p=Path(path).resolve(strict=True)
        if not p.is_file() or p.suffix.lower() not in SYSTEMS[system][1]: raise ValueError('Choose a recognised game file for this console.')
        if system=='PlayStation 5' and p.suffix.lower()=='.bin' and p.name.lower()!='eboot.bin':raise ValueError('Choose eboot.bin or a PKG file.')
        with self.lock:
            data=json.loads(json.dumps(self.state))
            g=next((g for g in data['games'] if g['id']==gid),None)
            if not g: raise ValueError('Game was removed while the picker was open.')
            g.update(nativePath=str(p),size=p.stat().st_size,format=p.suffix[1:].upper())
            self.save(data)
        return self.state

    def status(self):
        with self.lock:
            if self.process:
                code=self.process.poll()
                if code is None:return {'running':True,'game':self.process_game,'pid':self.process.pid}
                self.last_exit={'game':self.process_game,'exitCode':code,'ended':int(time.time()*1000)}
                self.process=None
            return {'running':False,'lastExit':self.last_exit}

    def launch(self,gid):
        with self.lock:
            if self.status()['running']:raise ValueError('An emulator launched here is already running. Close it before launching another game.')
            g=next((g for g in self.state['games'] if g['id']==gid),None)
            if not g:raise ValueError('Game is no longer in the library.')
            s=g['system']
            if s=='PlayStation 5':raise ValueError('PS5 launching is not connected.')
            exe=Path(self.config.get(s,''))
            if not exe.is_file() or exe.suffix.lower()!='.exe':raise ValueError('Set up '+SYSTEMS[s][0]+' in Emulator setup first.')
            game=Path(g.get('nativePath',''))
            if not game.is_absolute() or not game.is_file():raise ValueError('Game file not found. Use Locate game file to link its Windows path.')
            if game.suffix.lower() not in SYSTEMS[s][1]:raise ValueError('Unsupported game file for this console.')
            args=launch_arguments(s,exe.resolve(),game.resolve())
            try:self.process=self.popen(args,cwd=str(exe.resolve().parent),shell=False)
            except OSError as e:raise ValueError('Windows could not start the emulator: '+str(e)) from e
            self.process_game={'id':gid,'title':g['title'],'system':s}
            g['lastPlayed']=int(time.time()*1000);g['launchCount']=g.get('launchCount',0)+1
            warning=None
            try:atomic_json(self.state_file,self.state)
            except OSError:warning='Emulator started, but play history could not be saved.'
            return {'started':True,'game':self.process_game,'pid':self.process.pid,'warning':warning}


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=False


def handler_for(app,token,html,origin,stop):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,kind='application/json'):
            raw = json.dumps(body).encode('utf-8') if kind=='application/json' else body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(raw)
        def allowed(self):
            if self.headers.get('Host')!=origin.removeprefix('http://'):return False
            o=self.headers.get('Origin')
            if o and o!=origin:return False
            return secrets.compare_digest(self.headers.get('X-GoldenEmulator-Token',''),token)
        def do_GET(self):
            if self.headers.get('Host')!=origin.removeprefix('http://'):
                self.send(403,{'error':'Invalid host.'});return
            if self.path=='/':
                self.send(200,html.replace('<!-- NATIVE_CONFIG -->','<script>window.GE_NATIVE='+json.dumps({'token':token,'version':4})+';</script>'),'text/html');return
            if not self.allowed():self.send(403,{'error':'Reopen GoldenEmulator from its launcher.'});return
            if self.path=='/api/state':self.send(200,app.state)
            elif self.path=='/api/config':self.send(200,app.configurations())
            elif self.path=='/api/status':self.send(200,app.status())
            else:self.send(404,{'error':'Not found.'})
        def do_POST(self):
            if not self.allowed():self.send(403,{'error':'Reopen GoldenEmulator from its launcher.'});return
            if self.headers.get_content_type()!='application/json':self.send(415,{'error':'Expected JSON.'});return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=MAX_BYTES:raise ValueError('Invalid request size.')
                self.connection.settimeout(15)
                data=json.loads(self.rfile.read(n))
                if not isinstance(data,dict):raise ValueError('Expected an object.')
                if self.path=='/api/state': result=app.save(data)
                elif self.path=='/api/config':result=app.choose_emulator(data.get('system'))
                elif self.path=='/api/scan':
                    s=data.get('system')
                    if s not in SYSTEMS:raise ValueError('Unknown console.')
                    folder=app.picker('folder',s)
                    result=scan_folder(folder,s) if folder else {'cancelled':True}
                elif self.path=='/api/locate':result=app.locate(data.get('id'))
                elif self.path=='/api/launch':result=app.launch(data.get('id'))
                elif self.path=='/api/stop':
                    self.send(200,{'stopped':True});threading.Thread(target=stop,daemon=True).start();return
                else:self.send(404,{'error':'Not found.'});return
                self.send(200,result)
            except (ValueError,OSError,KeyError,TypeError) as e:self.send(400,{'error':str(e)})
            except Exception:self.send(500,{'error':'An unexpected launcher error occurred. Restart GoldenEmulator.'})
    return Handler


def main():
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw()
    if sys.platform!='win32':
        messagebox.showerror('GoldenEmulator','This launcher is for Windows.');root.destroy();return
    requests=queue.Queue()
    def picker(kind,system):
        task={'kind':kind,'system':system,'event':threading.Event(),'result':''}
        requests.put(task)
        if not task['event'].wait(600):raise ValueError('File selection timed out. Try again.')
        return task['result']
    def poll():
        try:
            task=requests.get_nowait()
            root.attributes('-topmost',True)
            if task['kind']=='folder':task['result']=filedialog.askdirectory(parent=root,title='Choose '+task['system']+' games folder')
            elif task['kind']=='emulator':task['result']=filedialog.askopenfilename(parent=root,title='Choose '+SYSTEMS[task['system']][0]+' executable',filetypes=[('Windows executable','*.exe')])
            else:task['result']=filedialog.askopenfilename(parent=root,title='Locate game file',filetypes=[('Game files',' '.join('*'+x for x in SYSTEMS[task['system']][1]))])
            task['event'].set()
        except queue.Empty:pass
        finally:root.after(100,poll)
    try:
        app=Launcher(Path(os.environ['LOCALAPPDATA'])/'GoldenEmulator',picker)
        html=(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'GoldenEmulator.html').read_text(encoding='utf-8')
        origin=f'http://127.0.0.1:{PORT}'
        token=secrets.token_urlsafe(32)
        def stop():
            server.shutdown();root.after(0,root.quit)
        server=LocalServer(('127.0.0.1',PORT),handler_for(app,token,html,origin,stop))
    except Exception as e:
        messagebox.showerror('GoldenEmulator','Could not start GoldenEmulator. If it is already running, use its open browser tab. Otherwise check your saved data in %LOCALAPPDATA%\\GoldenEmulator.\n\n'+str(e));root.destroy();return
    threading.Thread(target=server.serve_forever,daemon=True).start()
    root.after(100,poll)
    webbrowser.open(origin)
    root.mainloop();server.server_close();root.destroy()

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        import tkinter
        html=(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'GoldenEmulator.html').read_text(encoding='utf-8')
        assert '<!-- NATIVE_CONFIG -->' in html and 'function bindLaunch' in html
        Path(sys.argv[2]).write_text(json.dumps({'ok':True,'platform':sys.platform,'bundleHtml':True,'tkinter':True}))
    else:main()

