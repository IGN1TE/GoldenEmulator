"""GoldenEmulator Stage 5. Standard-library Windows launcher; no shell commands."""
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
from features import Features

SYSTEMS = {
    'SNES': ('Snes9x', {'.sfc', '.smc'}),
    'NES': ('Mesen', {'.nes', '.unf', '.unif'}),
    'Wii': ('Dolphin', {'.iso', '.wbfs', '.rvz', '.ciso'}),
    'PlayStation 1': ('DuckStation', {'.cue', '.chd', '.pbp', '.m3u'}),
    'PlayStation 3': ('RPCS3', {'.bin', '.elf', '.self'}),
    'PlayStation 4': ('shadPS4', {'.bin', '.elf', '.zar'}),
    'GameCube': ('Dolphin', {'.iso', '.gcm', '.rvz', '.ciso'}),
    'Xbox 360': ('Xenia', {'.iso', '.xex'}),
    'PlayStation 2': ('PCSX2', {'.iso', '.bin', '.chd', '.cso', '.cue'}),
    'PlayStation 5': ('Custom emulator (experimental)', {'.pkg', '.bin'}),
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
    if system in ('GameCube', 'Wii'): return [str(exe), '-b', '-e', str(game)]
    if system in ('SNES', 'NES'): return [str(exe), str(game)]
    if system == 'PlayStation 1': return [str(exe), '-batch', '--', str(game)]
    if system == 'PlayStation 3': return [str(exe), '--no-gui', str(game)]
    if system == 'PlayStation 4':
        if ps4_profile(exe)=='shadps4-launcher': return [str(exe), '-d', '-g', str(game)]
        if ps4_profile(exe)=='shadps4': return [str(exe), '-g', str(game)]
        return [str(exe)]
    if system == 'Xbox 360': return [str(exe), str(game)]
    if system == 'PlayStation 2': return [str(exe), '-batch', '--', str(game)]
    raise ValueError('PS5 launching is not connected. No compatibility is implied.')


def ps4_profile(exe):
    name=Path(exe).stem.lower().replace('-', '').replace('_', '')
    if name.startswith('shadps4'):
        return 'shadps4-launcher' if 'launcher' in name else 'shadps4'
    return 'custom'


def valid_game(system, path):
    return (path.suffix.lower() in SYSTEMS[system][1] and
            not (system in ('PlayStation 3', 'PlayStation 4', 'PlayStation 5')
                 and path.suffix.lower() == '.bin' and path.name.lower() != 'eboot.bin'))


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
        self.update_lock = threading.Lock()
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

        self.features = Features(self, atomic_json, scan_folder, valid_game)

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
        return {s:{'name':name,'path':self.config.get(s,''),'exists':Path(self.config[s]).is_file() if self.config.get(s) else False,'supported':True} for s,(name,_) in SYSTEMS.items()}

    def choose_emulator(self, system):
        if system not in SYSTEMS: raise ValueError('This console has no launch integration.')
        path = self.picker('emulator', system)
        if not path: return {'cancelled':True}
        exe = Path(path).resolve(strict=True)
        if not exe.is_file() or exe.suffix.lower()!='.exe': raise ValueError('Choose the installed emulator EXE.')
        with self.lock:
            new = dict(self.config); new[system]=str(exe)
            atomic_json(self.config_file,new); self.config=new
        return self.configurations()

    def open_emulator(self, system):
        if system not in SYSTEMS: raise ValueError('Unknown console.')
        with self.lock:
            if self.status()['running']: raise ValueError('An emulator is already running. Close it first.')
            exe = Path(self.config.get(system, ''))
            if not exe.is_file() or exe.suffix.lower() != '.exe':
                raise ValueError('Choose an EXE in Emulator setup first.')
            self.process = self.popen([str(exe.resolve())], cwd=str(exe.resolve().parent), shell=False)
            self.features.begin(None,False)
            self.process_game = {'id':None, 'title':system + ' emulator', 'system':system}
            return {'started':True, 'pid':self.process.pid, 'warning':'Emulator opened. Select your game inside the emulator.'}

    def locate(self, gid):
        with self.lock:
            g = next((g for g in self.state['games'] if g['id']==gid),None)
            if not g: raise ValueError('Game is no longer in the library.')
            system=g['system']
        path=self.picker('game',system)
        if not path:return {'cancelled':True}
        p=Path(path).resolve(strict=True)
        if not p.is_file() or not valid_game(system, p): raise ValueError('Choose a recognised game file for this console (BIN must be eboot.bin).')
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
                self.features.finish(code)
                if getattr(self,'window',None):
                    try:self.window.restore();self.window.show()
                    except Exception:pass
                self.last_exit={'game':self.process_game,'exitCode':code,'ended':int(time.time()*1000)}
                self.process=None
            return {'running':False,'lastExit':self.last_exit}

    def launch(self,gid):
        with self.lock:
            if self.status()['running']:raise ValueError('An emulator launched here is already running. Close it before launching another game.')
            g=next((g for g in self.state['games'] if g['id']==gid),None)
            if not g:raise ValueError('Game is no longer in the library.')
            s=g['system']
            extra=self.features.data['games'].get(gid,{})
            chosen=extra.get('emulator') or self.config.get(s,'')
            if s=='PlayStation 5' or (s=='PlayStation 4' and ps4_profile(chosen)=='custom'):
                if extra.get('emulator'):
                    exe=Path(chosen)
                    if not exe.is_file() or exe.suffix.lower()!='.exe':raise ValueError('Per-game emulator is missing.')
                    self.process=self.popen([str(exe.resolve())],cwd=str(exe.resolve().parent),shell=False)
                    self.process_game={'id':None,'title':s+' emulator','system':s}
                    self.features.begin(gid,False)
                    return {'started':True,'pid':self.process.pid,'warning':'Emulator opened. Select the game inside it. Playtime is not tracked.'}
                return self.open_emulator(s)
            exe=Path(chosen)
            if not exe.is_file() or exe.suffix.lower()!='.exe':raise ValueError('Set up '+SYSTEMS[s][0]+' in Emulator setup first.')
            game=Path(g.get('nativePath',''))
            if not game.is_absolute() or not game.is_file():raise ValueError('Game file not found. Use Locate game file to link its Windows path.')
            if not valid_game(s, game):raise ValueError('Unsupported game file for this console.')
            if s == 'PlayStation 4' and game.suffix.lower() == '.zar':
                raise ValueError('For shadPS4, locate the extracted eboot.bin or ELF file instead of a ZArchive.')
            args=launch_arguments(s,exe.resolve(),game.resolve())
            args=self.features.launch_config(gid,exe,args)
            if self.features.data['prefs'].get('autoBackup') and extra.get('savePath'):self.features.backup(gid)
            try:self.process=self.popen(args,cwd=str(exe.resolve().parent),shell=False)
            except OSError as e:raise ValueError('Windows could not start the emulator: '+str(e)) from e
            self.features.begin(gid,not (s=='PlayStation 4' and ps4_profile(exe)=='shadps4-launcher'))
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
                self.send(200,html.replace('<!-- NATIVE_CONFIG -->','<script>window.GE_NATIVE='+json.dumps({'token':token,'version':6})+';</script>'),'text/html');return
            if not self.allowed():self.send(403,{'error':'Reopen GoldenEmulator from its launcher.'});return
            if self.path=='/api/state':self.send(200,app.state)
            elif self.path=='/api/config':self.send(200,app.configurations())
            elif self.path=='/api/status':self.send(200,{**app.status(),'desktopReady':getattr(app,'desktop_ready',False)})
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
                elif self.path=='/api/features':result=app.features.dispatch(data)
                elif self.path=='/api/config':result=app.choose_emulator(data.get('system'))
                elif self.path=='/api/scan':
                    s=data.get('system')
                    if s not in SYSTEMS:raise ValueError('Unknown console.')
                    folder=app.picker('folder',s)
                    result=scan_folder(folder,s) if folder else {'cancelled':True}
                elif self.path=='/api/locate':result=app.locate(data.get('id'))
                elif self.path=='/api/launch':result=app.launch(data.get('id'))
                elif self.path=='/api/open-emulator':result=app.open_emulator(data.get('system'))
                elif self.path=='/api/desktop-ready':
                    app.desktop_ready=data.get('ok') is True;result={'ok':app.desktop_ready}
                elif self.path=='/api/focus':
                    app.window.restore();app.window.show();result={'focused':True}
                elif self.path=='/api/fullscreen':
                    app.window.toggle_fullscreen();result={'ok':True}
                elif self.path=='/api/updates':result=check_updates()
                elif self.path=='/api/install-update':
                    if not app.update_lock.acquire(blocking=False): raise ValueError('An update is already in progress.')
                    try:
                        if app.status()['running']: raise ValueError('Close the running emulator before updating.')
                        result=install_update(app.data_dir,progress=lambda stage,received,total:app.features.update_progress.update(stage=stage,received=received,total=total))
                    except Exception:
                        app.update_lock.release()
                        raise
                    self.send(200,result)
                    threading.Timer(1,stop).start()
                    return
                elif self.path=='/api/stop':
                    self.send(200,{'stopped':True});threading.Thread(target=stop,daemon=True).start();return
                else:self.send(404,{'error':'Not found.'});return
                self.send(200,result)
            except (ValueError,OSError,KeyError,TypeError) as e:
                if self.path in ('/api/launch','/api/open-emulator'):
                    try:app.features.log('error',str(e),data.get('id'))
                    except Exception:pass
                if self.path=='/api/install-update':app.features.update_progress.update(stage='error',error=str(e))
                self.send(400,{'error':str(e)})
            except Exception:self.send(500,{'error':'An unexpected launcher error occurred. Restart GoldenEmulator.'})
    return Handler


APP_VERSION = '0.9.0'
RELEASES_API = 'https://api.github.com/repos/IGN1TE/GoldenEmulator/releases?per_page=100'
RELEASE_PREFIX = 'https://github.com/IGN1TE/GoldenEmulator/releases/tag/'


def select_update(releases, current=APP_VERSION):
    import re
    if not isinstance(releases,list):raise ValueError('GitHub returned an invalid release list.')
    latest=tuple(map(int,current.split('.')));result={'current':current,'latest':current,'available':False,'url':''}
    for release in releases:
        if not isinstance(release,dict) or release.get('draft'):continue
        url=release.get('html_url','')
        if not isinstance(url,str) or not re.fullmatch(re.escape(RELEASE_PREFIX)+r'[A-Za-z0-9._-]+',url):continue
        assets=release.get('assets',[])
        if not isinstance(assets,list):continue
        for asset in assets:
            if not isinstance(asset,dict):continue
            match=re.fullmatch(r'GoldenEmulator-Setup-(\d+)\.(\d+)\.(\d+)\.exe',str(asset.get('name','')))
            if not match:continue
            version=tuple(map(int,match.groups()))
            download=asset.get('browser_download_url','')
            expected='https://github.com/IGN1TE/GoldenEmulator/releases/download/'+url.rsplit('/',1)[1]+'/'+asset['name']
            if download!=expected:continue
            if version>latest:
                latest=version;result={'current':current,'latest':'.'.join(map(str,version)),'available':True,'url':url,'prerelease':release.get('prerelease') is True,'download':download,'name':asset['name'],'size':asset.get('size'),'digest':asset.get('digest'),'notes':str(release.get('body') or '')[:12000]}
    return result


def check_updates():
    import urllib.request
    req=urllib.request.Request(RELEASES_API,headers={'Accept':'application/vnd.github+json','User-Agent':'GoldenEmulator/'+APP_VERSION})
    try:
        with urllib.request.urlopen(req,timeout=10) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('Release response is too large.')
        return select_update(json.loads(raw))
    except (OSError,ValueError) as e:
        raise ValueError('Could not check for updates. Check your internet connection and try again. GitHub may be temporarily unavailable or rate-limited.') from e


def install_update(data_dir, progress=None):
    """Fetch only an installer selected from our release API; verify before running."""
    import hashlib
    import re
    import tempfile
    import urllib.request
    if progress:progress('checking',0,0)
    update=check_updates()
    if not update['available']: raise ValueError('You are already up to date.')
    digest=update.get('digest')
    if not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):
        raise ValueError('This release has no SHA-256 verification data. Please try again later.')
    size=update.get('size')
    if not isinstance(size,int) or not 0<size<=500*1024*1024: raise ValueError('Invalid installer size.')
    folder=Path(data_dir)/'updates';folder.mkdir(parents=True,exist_ok=True)
    target=Path(tempfile.mkdtemp(prefix='install-',dir=folder))/update['name']
    try:
        request=urllib.request.Request(update['download'],headers={'User-Agent':'GoldenEmulator/'+APP_VERSION})
        hashed=hashlib.sha256();received=0
        with urllib.request.urlopen(request,timeout=30) as response, target.open('wb') as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                received+=len(chunk)
                if received>size:raise ValueError('Installer download exceeded its expected size.')
                output.write(chunk);hashed.update(chunk)
                if progress:progress('downloading',received,size)
        if progress:progress('verifying',received,size)
        if received!=size or hashed.hexdigest()!=digest[7:].lower():
            raise ValueError('Installer verification failed. Nothing was installed; try again.')
        if progress:progress('installing',received,size)
        subprocess.Popen([str(target),'/SILENT','/SP-','/NORESTART','/RESTARTAPP=1'],cwd=str(target.parent),shell=False)
    except Exception:
        target.unlink(missing_ok=True)
        target.parent.rmdir()
        raise
    return {'installing':True,'version':update['latest']}


def contact_instance(data_dir, stop=False, focus=False):
    """Use only our fixed loopback address; never trust a URL from a state file."""
    import urllib.request
    origin=f'http://127.0.0.1:{PORT}'
    try:
        runtime=json.loads((Path(data_dir)/'runtime.json').read_text(encoding='utf-8'))
        token=runtime['token']
        if not isinstance(token,str) or len(token)>200:return False
        req=urllib.request.Request(origin+('/api/stop' if stop else '/api/focus' if focus else '/api/status'),
            data=b'{}' if stop or focus else None,
            headers={'Content-Type':'application/json','X-GoldenEmulator-Token':token})
        with urllib.request.urlopen(req,timeout=3) as response:
            result=json.load(response)
        return result.get('stopped') is True if stop else result.get('focused') is True if focus else isinstance(result.get('running'),bool)
    except (OSError,ValueError,KeyError,TypeError):return False


def main():
    import ctypes
    def error(text):ctypes.windll.user32.MessageBoxW(None,text,'GoldenEmulator',0x10)
    if sys.platform!='win32':return
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('IGN1TE.GoldenEmulator')
    data_dir=Path(os.environ['LOCALAPPDATA'])/'GoldenEmulator'
    origin=f'http://127.0.0.1:{PORT}'
    if '--stop' in sys.argv:
        if not contact_instance(data_dir,stop=True):error('No current launcher was found. Exit older portable versions through their Settings menu.')
        return
    if contact_instance(data_dir):
        if contact_instance(data_dir,focus=True):return
        # Upgrade from the previous browser-hosted launcher without terminating games.
        if not contact_instance(data_dir,stop=True):error('Exit the previous launcher before opening this version.');return
        for _ in range(50):
            if not contact_instance(data_dir):break
            time.sleep(.1)
    server=None;serving=False
    try:
        import webview
        def picker(kind,system):
            if kind=='folder':result=window.create_file_dialog(webview.FileDialog.FOLDER)
            else:
                types=('Configuration files (*.*)',) if kind=='config' else ('Windows executable (*.exe)',) if kind=='emulator' else ('Game files ('+';'.join('*'+x for x in SYSTEMS[system][1])+')',)
                result=window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=False,file_types=types)
            return result[0] if result else ''
        app=Launcher(data_dir,picker)
        html=(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'GoldenEmulator.html').read_text(encoding='utf-8')
        token=secrets.token_urlsafe(32)
        def stop():window.destroy()
        try:server=LocalServer(('127.0.0.1',PORT),handler_for(app,token,html,origin,stop))
        except OSError:raise ValueError('An older GoldenEmulator is still running. Exit it through Settings > Exit GoldenEmulator, then open this version again.')
        webview.settings['ALLOW_DOWNLOADS']=True
        webview.settings['ALLOW_FILE_URLS']=False
        window=webview.create_window('GoldenEmulator',origin,width=1360,height=860,min_size=(900,600),background_color='#080d1b',text_select=True)
        app.window=window
        app.desktop_ready=False
        def loaded():
            window.run_js("""(function check(){if(typeof ready==='undefined'||!ready){setTimeout(check,100);return;}fetch('/api/desktop-ready',{method:'POST',headers:{'Content-Type':'application/json','X-GoldenEmulator-Token':window.GE_NATIVE.token},body:JSON.stringify({ok:document.querySelectorAll('.system').length===10&&typeof navigator.getGamepads==='function'&&!!document.getElementById('settings')})});})();""")
        window.events.loaded+=loaded
        atomic_json(data_dir/'runtime.json',{'token':token,'version':6})
        threading.Thread(target=server.serve_forever,daemon=True).start();serving=True
        webview.start(icon=str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'GoldenEmulator.ico'),gui='edgechromium',private_mode=False,storage_path=str(data_dir/'WebView2'))
    except Exception as e:
        error('Could not open GoldenEmulator. Microsoft Edge WebView2 Runtime is required. Your library has not been reset.\n\n'+str(e))
    finally:
        if server:
            if serving:server.shutdown()
            server.server_close()
        try:
            runtime=data_dir/'runtime.json'
            if 'token' in locals() and json.loads(runtime.read_text(encoding='utf-8')).get('token')==token:runtime.unlink()
        except (OSError,ValueError):pass

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        import webview
        html=(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'GoldenEmulator.html').read_text(encoding='utf-8')
        assert '<!-- NATIVE_CONFIG -->' in html and 'function bindLaunch' in html
        Path(sys.argv[2]).write_text(json.dumps({'ok':True,'platform':sys.platform,'bundleHtml':True,'desktop':True}))
    else:main()

