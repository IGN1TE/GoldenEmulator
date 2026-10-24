"""Library Hub services. All filesystem writes stay within explicitly selected roots."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

MAX_BACKUP = 1024 * 1024 * 1024

def text(value, limit=2000):
    if not isinstance(value, str) or len(value) > limit or '\0' in value:
        raise ValueError('Invalid text field.')
    return value

def safe_files(root):
    root = Path(root).resolve(strict=True)
    result = []
    total = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [n for n in dirs if not Path(base,n).is_symlink() and not getattr(Path(base,n),'is_junction',lambda:False)()]
        for n in names:
            p = Path(base,n)
            if p.is_symlink(): continue
            p.resolve().relative_to(root)
            total += p.stat().st_size
            if total > MAX_BACKUP or len(result) >= 20000:
                raise ValueError('Save folder is too large (1 GB / 20,000 files maximum).')
            result.append(p)
    return result

class Features:
    def __init__(self, app, atomic, scan, valid):
        self.app, self.atomic, self.scan, self.valid = app, atomic, scan, valid
        self.path = app.data_dir/'features.json'
        self.data = {'version':1,'games':{},'roots':[], 'collections':[], 'logs':[], 'prefs':{}}
        if self.path.exists():
            raw=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw,dict) or raw.get('version')!=1 or not isinstance(raw.get('games'),dict):
                raise ValueError('Library Hub settings are damaged; restore features.json from a backup.')
            self.data.update(raw)
        self.started=None
        self.update_progress={'stage':'idle','received':0,'total':0}
        self.pending_repairs={}
        self.matches={}

    def persist(self):
        if len(json.dumps(self.data).encode()) > 40*1024*1024: raise ValueError('Hub data exceeds 40 MB; remove screenshots first.')
        self.atomic(self.path,self.data)

    def game(self,gid):
        g=next((g for g in self.app.state['games'] if g['id']==gid),None)
        if not g: raise ValueError('Game is no longer in the library.')
        return g

    def log(self,kind,message,gid=None):
        with self.app.lock:
            self.data['logs'].append({'at':int(time.time()*1000),'kind':kind,'message':str(message)[:4000],'id':gid})
            self.data['logs']=self.data['logs'][-200:]
            self.persist()

    def begin(self,gid,tracked=True):
        self.started=(gid,time.monotonic()) if tracked else None
        self.log('launch','Started emulator'+(' (process session tracking)' if tracked else ' (playtime unavailable for this launcher)'),gid)

    def finish(self,code):
        with self.app.lock:
            if self.started:
                gid,start=self.started; self.started=None
                seconds=max(0,int(time.monotonic()-start))
                entry=self.data['games'].setdefault(gid,{})
                entry['playSeconds']=entry.get('playSeconds',0)+seconds
                entry.setdefault('sessions',[]).append({'ended':int(time.time()*1000),'seconds':seconds,'exitCode':code})
                entry['sessions']=entry['sessions'][-100:]
            self.log('exit','Emulator exited with code '+str(code))

    def launch_config(self,gid,default_exe,default_args):
        e=self.data['games'].get(gid,{})
        exe=Path(e.get('emulator') or default_exe)
        if not exe.is_file() or exe.suffix.lower()!='.exe': raise ValueError('The per-game emulator EXE is missing.')
        args=e.get('arguments',[])
        if args:
            game=self.game(gid)
            args=[s.replace('{game}',game['nativePath']).replace('{config}',e.get('configPath','')) for s in args]
            if any('{config}' in s for s in e['arguments']) and not Path(e.get('configPath','')).is_file():
                raise ValueError('The per-game configuration file is missing.')
            return [str(exe.resolve()),*args]
        return [str(exe.resolve()),*default_args[1:]]

    def root_paths(self):
        return {r['id']:Path(r['path']) for r in self.data['roots']}

    def bind_portable(self):
        for g in self.app.state['games']:
            for root in self.data['roots']:
                if g['system']!=root['system'] or not g.get('nativePath'): continue
                try: rel=Path(g['nativePath']).resolve().relative_to(Path(root['path']).resolve())
                except ValueError: continue
                self.data['games'].setdefault(g['id'],{}).update(rootId=root['id'],relativePath=rel.as_posix())
        self.persist()

    def repair_preview(self):
        proposals=[]; missing=[]; roots=self.root_paths(); self.pending_repairs={}
        for g in self.app.state['games']:
            if g.get('nativePath') and Path(g['nativePath']).is_file(): continue
            missing.append({'id':g['id'],'title':g['title'],'path':g.get('nativePath') or g['path']})
            e=self.data['games'].get(g['id'],{}); root=roots.get(e.get('rootId'))
            if not root or not root.is_dir(): continue
            p=(root/e.get('relativePath','')).resolve()
            try: p.relative_to(root.resolve())
            except ValueError: continue
            if p.is_file() and self.valid(g['system'],p):
                self.pending_repairs[g['id']]=str(p)
                proposals.append({'id':g['id'],'title':g['title'],'path':str(p)})
        return {'missing':missing,'proposals':proposals}

    def backup_dir(self,gid):
        return self.app.data_dir/'save-backups'/hashlib.sha256(gid.encode()).hexdigest()[:24]

    def backup(self,gid):
        self.game(gid)
        root=Path(self.data['games'].get(gid,{}).get('savePath',''))
        if not str(self.data['games'].get(gid,{}).get('savePath','')) or not root.is_dir():
            raise ValueError('Choose this game’s save folder first.')
        root=root.resolve()
        dest=self.backup_dir(gid); dest.mkdir(parents=True,exist_ok=True)
        if dest.resolve().is_relative_to(root): raise ValueError('Choose the emulator save folder, not the GoldenEmulator data folder.')
        files=safe_files(root)
        name=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]+'.zip'
        path=dest/name; tmp=path.with_suffix('.tmp')
        try:
            with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
                for p in files: z.write(p,p.relative_to(root).as_posix())
            os.replace(tmp,path)
        finally: tmp.unlink(missing_ok=True)
        self.log('backup','Saved '+str(len(files))+' save files',gid)
        return {'name':name,'files':len(files)}

    def restore(self,gid,name):
        self.game(gid)
        if self.app.status()['running']: raise ValueError('Close the emulator before restoring saves.')
        if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{6}\.zip',str(name)): raise ValueError('Invalid backup name.')
        archive=self.backup_dir(gid)/name
        root=Path(self.data['games'].get(gid,{}).get('savePath',''))
        if not root.is_dir() or not self.data['games'].get(gid,{}).get('savePath'): raise ValueError('Choose a save folder first.')
        root=root.resolve()
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if len(infos)>20000 or sum(i.file_size for i in infos)>MAX_BACKUP: raise ValueError('Backup is too large.')
            for i in infos:
                raw_name=i.orig_filename
                rel=PurePosixPath(raw_name)
                if rel.is_absolute() or '..' in rel.parts or '\\' in raw_name or ':' in raw_name or (i.external_attr>>16)&0o170000==0o120000:
                    raise ValueError('Unsafe backup path.')
                target=root/i.filename
                if target.is_symlink(): raise ValueError('Save destination contains a symlink.')
                target.resolve().relative_to(root)
            if z.testzip(): raise ValueError('Backup is damaged.')
            safety=self.backup(gid)
            for i in infos:
                if i.is_dir(): continue
                target=root/i.filename; target.parent.mkdir(parents=True,exist_ok=True)
                tmp=target.with_name(target.name+'.ge-restore-'+uuid.uuid4().hex[:8])
                try:
                    with z.open(i) as src, tmp.open('wb') as dst: shutil.copyfileobj(src,dst)
                    os.replace(tmp,target)
                finally: tmp.unlink(missing_ok=True)
        self.log('restore','Restored '+name+'; pre-restore backup '+safety['name'],gid)
        return {'restored':True,'safetyBackup':safety['name']}

    def dispatch(self,d):
        action=d.get('action','get'); gid=d.get('id')
        with self.app.lock:
            if action=='get': return copy.deepcopy(self.data)
            if action=='restore-hub':
                raw=d.get('backup')
                if not isinstance(raw,dict) or raw.get('version')!=1 or not isinstance(raw.get('games'),dict):raise ValueError('Invalid Hub backup.')
                old=copy.deepcopy(self.data)
                try:
                    # Import descriptive data only; local launch/save paths remain selected by this machine.
                    allowed={'description','genre','year','completion','rating','collections','screenshots'}
                    for game in self.app.state['games']:
                        e=raw['games'].get(game['id'])
                        if e is None:continue
                        if not isinstance(e,dict):raise ValueError('Invalid game metadata.')
                        self.dispatch({'action':'save-game','id':game['id'],'patch':{k:v for k,v in e.items() if k in allowed}})
                    self.persist()
                except Exception:
                    self.data=old;self.persist();raise
                return {'ok':True}
            if action=='save-game':
                self.game(gid); old=copy.deepcopy(self.data); e=self.data['games'].setdefault(gid,{})
                try:
                    patch=d.get('patch',{})
                    if not isinstance(patch,dict):raise ValueError('Invalid game metadata.')
                    for k in ('description','genre','year','completion','configPath'):
                        if k in patch: e[k]=text(patch[k],5000 if k=='description' else 4096 if k=='configPath' else 200)
                    if 'rating' in patch:
                        n=patch['rating']
                        if type(n)!=int or not 0<=n<=5: raise ValueError('Rating must be 0–5.')
                        e['rating']=n
                    if 'arguments' in patch:
                        args=patch['arguments']
                        if not isinstance(args,list) or len(args)>64: raise ValueError('Use up to 64 arguments.')
                        e['arguments']=[text(a,4096) for a in args]
                    if 'collections' in patch:
                        names=patch['collections']
                        if not isinstance(names,list) or len(names)>30: raise ValueError('Too many collections.')
                        e['collections']=list(dict.fromkeys(text(n,80).strip() for n in names if text(n,80).strip()))
                        self.data['collections']=sorted(set(self.data['collections']+e['collections']))
                    if 'screenshots' in patch:
                        shots=patch['screenshots']
                        if not isinstance(shots,list) or len(shots)>4: raise ValueError('Use up to four screenshots.')
                        if any(not re.fullmatch(r'data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+',text(s,1500000)) for s in shots): raise ValueError('Invalid screenshot.')
                        e['screenshots']=shots
                    self.persist()
                except Exception: self.data=old; raise
                return copy.deepcopy(e)
            if action=='prefs':
                self.data['prefs']={k:d.get(k) is True for k in ('couch','autoBackup','autoScan')};self.persist();return self.data['prefs']
            if action=='pick-game-path':
                self.game(gid); kind=d.get('kind')
                if kind not in ('emulator','save','config'): raise ValueError('Invalid path type.')
                p=self.app.picker('folder' if kind=='save' else 'config' if kind=='config' else 'emulator',self.game(gid)['system'])
                if not p: return {'cancelled':True}
                p=Path(p).resolve(strict=True)
                if kind=='emulator' and (not p.is_file() or p.suffix.lower()!='.exe'): raise ValueError('Choose an emulator EXE.')
                if kind=='save' and not p.is_dir(): raise ValueError('Choose a save folder.')
                if kind=='config' and not p.is_file(): raise ValueError('Choose a configuration file.')
                self.data['games'].setdefault(gid,{})[{'emulator':'emulator','save':'savePath','config':'configPath'}[kind]]=str(p)
                self.persist();return {'path':str(p)}
            if action=='clear-emulator':
                self.data['games'].setdefault(self.game(gid)['id'],{}).pop('emulator',None);self.persist();return {'ok':True}
            if action=='root-add':
                system=d.get('system')
                if system not in self.app.configurations(): raise ValueError('Unknown console.')
                p=self.app.picker('folder',system)
                if not p:return {'cancelled':True}
                p=Path(p).resolve(strict=True)
                if not p.is_dir(): raise ValueError('Choose a folder.')
                if len(self.data['roots'])>=20: raise ValueError('Maximum 20 watched folders.')
                self.data['roots'].append({'id':uuid.uuid4().hex,'system':system,'path':str(p)})
                self.bind_portable();return self.data['roots']
            if action=='root-remove':
                self.data['roots']=[r for r in self.data['roots'] if r['id']!=d.get('rootId')];self.persist();return {'ok':True}
            if action=='root-relink':
                root=next((r for r in self.data['roots'] if r['id']==d.get('rootId')),None)
                if root is None:raise ValueError('Watched folder no longer exists.')
                p=self.app.picker('folder',root['system'])
                if p: root['path']=str(Path(p).resolve(strict=True));self.persist()
                return self.repair_preview()
            if action=='scan':
                self.bind_portable(); batches=[]
                for root in self.data['roots']:
                    try: batches.append({**self.scan(root['path'],root['system']),'system':root['system'],'rootId':root['id']})
                    except (OSError,ValueError) as e:batches.append({'system':root['system'],'files':[],'error':str(e)})
                return {'batches':batches}
            if action=='repair': return self.repair_preview()
            if action=='repair-apply':
                data=copy.deepcopy(self.app.state)
                for g in data['games']:
                    if g['id'] in d.get('ids',[]) and g['id'] in self.pending_repairs:
                        p=Path(self.pending_repairs[g['id']]);p.stat()
                        if not p.is_file():raise ValueError('A repair file disappeared. Scan again.')
                        g.update(nativePath=str(p),size=p.stat().st_size)
                result=self.app.save(data);self.pending_repairs={};return result
            if action=='group':
                ids=list(dict.fromkeys(d.get('ids',[])))
                if not 1<=len(ids)<=12: raise ValueError('Select 1–12 discs.')
                gs=[self.game(i) for i in ids]
                if len({g['system'] for g in gs})!=1: raise ValueError('Discs must use the same console.')
                primary=ids[0]
                if any(self.data['games'].get(i,{}).get('discParent') not in (None,'',primary) for i in ids): raise ValueError('Ungroup these discs before regrouping.')
                for e in self.data['games'].values():
                    if e.get('discParent')==primary:e.pop('discParent',None)
                for i in ids:self.data['games'].setdefault(i,{})['discParent']=primary
                self.persist();return {'ok':True}
            if action=='ungroup':
                parent=self.data['games'].get(gid,{}).get('discParent',gid)
                for e in self.data['games'].values():
                    if e.get('discParent')==parent:e.pop('discParent',None)
                self.persist();return {'ok':True}
            if action=='backups':
                self.game(gid);return {'backups':[{'name':p.name,'size':p.stat().st_size} for p in sorted(self.backup_dir(gid).glob('*.zip'),reverse=True)]}
            if action=='backup':
                if self.app.status()['running']:raise ValueError('Close the emulator before backing up saves.')
                return self.backup(gid)
            if action=='restore': return self.restore(gid,d.get('name'))
            if action=='health':
                notes={'PlayStation 1':'Configure BIOS in DuckStation.','PlayStation 2':'Configure BIOS in PCSX2.','PlayStation 3':'Install firmware in RPCS3.','PlayStation 4':'Configure shadPS4/QtLauncher and extracted games.','PlayStation 5':'Opens the emulator only; compatibility is not verified.'}
                return {'systems':[{'system':s,**c,'note':notes.get(s,'Configure graphics, audio and controllers in the emulator.')} for s,c in self.app.configurations().items()], 'missing':self.repair_preview()['missing']}
            if action=='update-progress':return dict(self.update_progress)
            if action=='metadata-search':return self.metadata_search(text(d.get('query',''),200))
            if action=='metadata-apply':return self.metadata_apply(gid,d.get('pageId'))
            raise ValueError('Unknown Library Hub action.')

    def wiki(self,host,params):
        url='https://'+host+'/w/api.php?'+urllib.parse.urlencode({'format':'json','formatversion':2,**params})
        req=urllib.request.Request(url,headers={'User-Agent':'GoldenEmulator/0.9.0 (https://github.com/IGN1TE/GoldenEmulator)'})
        with urllib.request.urlopen(req,timeout=12) as r: raw=r.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('Metadata response is too large.')
        data=json.loads(raw)
        if 'error' in data:raise ValueError('Metadata provider rejected the query. Try a shorter title.')
        return data

    def metadata_search(self,query):
        if not query.strip():raise ValueError('Enter a game title.')
        data=self.wiki('en.wikipedia.org',{'action':'query','generator':'search','gsrsearch':query+' video game','gsrlimit':6,'prop':'extracts|pageimages|pageprops','exintro':1,'explaintext':1,'exchars':1500,'piprop':'thumbnail','pithumbsize':500})
        pages=data.get('query',{}).get('pages',[]);self.matches={str(p['pageid']):p for p in pages}
        return {'matches':[{'pageId':str(p['pageid']),'title':p['title'],'description':p.get('extract',''),'hasArtwork':bool(p.get('thumbnail'))} for p in pages]}

    def metadata_apply(self,gid,pageid):
        g=self.game(gid);p=self.matches.get(str(pageid))
        if not p:raise ValueError('Search again before selecting a match.')
        e=self.data['games'].setdefault(gid,{})
        e.update(description=p.get('extract','')[:5000],source='https://en.wikipedia.org/?curid='+str(p['pageid']),sourceTitle=p['title'])
        warning=[]; item=p.get('pageprops',{}).get('wikibase_item','')
        if re.fullmatch(r'Q\d+',item):
            try:
                entity=self.wiki('www.wikidata.org',{'action':'wbgetentities','ids':item,'props':'claims'})['entities'][item]
                claims=entity.get('claims',{})
                dates=[c.get('mainsnak',{}).get('datavalue',{}).get('value',{}).get('time','') for c in claims.get('P577',[])]
                years=[s[1:5] for s in dates if re.match(r'\+\d{4}-',s)]
                if years:e['year']=min(years)
                genres=[c.get('mainsnak',{}).get('datavalue',{}).get('value',{}).get('id','') for c in claims.get('P136',[])]
                genres=[i for i in genres if re.fullmatch(r'Q\d+',i)][:10]
                if genres:
                    labels=self.wiki('www.wikidata.org',{'action':'wbgetentities','ids':'|'.join(genres),'props':'labels','languages':'en'})['entities']
                    e['genre']=', '.join(x.get('labels',{}).get('en',{}).get('value','') for x in labels.values())[:200]
            except (OSError,ValueError,KeyError):warning.append('Release year/genre unavailable')
        image=p.get('thumbnail',{}).get('source','')
        if image:
            u=urllib.parse.urlparse(image)
            if u.scheme=='https' and u.hostname=='upload.wikimedia.org':
                try:
                    req=urllib.request.Request(image,headers={'User-Agent':'GoldenEmulator/0.9.0'})
                    with urllib.request.urlopen(req,timeout=15) as r:
                        if urllib.parse.urlparse(r.url).hostname!='upload.wikimedia.org': raise ValueError('Unexpected image redirect.')
                        mime=r.headers.get_content_type();raw=r.read(1800001)
                    if mime not in ('image/png','image/jpeg','image/webp') or len(raw)>1800000:raise ValueError('Image format or size unsupported.')
                    data=copy.deepcopy(self.app.state)
                    next(x for x in data['games'] if x['id']==gid)['cover']='data:'+mime+';base64,'+base64.b64encode(raw).decode()
                    self.app.save(data);e['artworkSource']=image
                except (OSError,ValueError):warning.append('Artwork unavailable; existing cover kept')
        self.persist();return {'state':self.app.state,'extra':e,'warning':'; '.join(warning)}
