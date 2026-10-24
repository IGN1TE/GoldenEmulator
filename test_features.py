import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile
import GoldenEmulator as ge

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.exe=self.root/'emulator.exe';self.exe.touch()
        self.game=self.root/'games'/'game.xex';self.game.parent.mkdir();self.game.write_text('game')
        self.process=Mock(pid=123);self.process.poll.return_value=None
        self.spawn=Mock(return_value=self.process)
        self.app=ge.Launcher(self.root/'data',popen=self.spawn);self.app.config={'Xbox 360':str(self.exe)}
        self.app.save({'version':2,'games':[{'id':'g1','title':'Game','system':'Xbox 360','path':'games/game.xex','nativePath':str(self.game),'size':4,'cover':'','favorite':False,'notes':''}]})
        self.h=self.app.features
        self.save=self.root/'saves';self.save.mkdir();(self.save/'slot.sav').write_text('original')
        self.h.data['games']['g1']={'savePath':str(self.save)}
    def tearDown(self):self.tmp.cleanup()
    def call(self,action,**kw):return self.h.dispatch({'action':action,**kw})
    def test_save_restore_creates_safety_and_preserves_unrelated_files(self):
        first=self.call('backup',id='g1')['name'];(self.save/'slot.sav').write_text('changed');(self.save/'other.sav').write_text('other')
        result=self.call('restore',id='g1',name=first)
        self.assertEqual((self.save/'slot.sav').read_text(),'original');self.assertTrue((self.save/'other.sav').exists())
        with zipfile.ZipFile(self.h.backup_dir('g1')/result['safetyBackup']) as z:self.assertEqual(z.read('slot.sav'),b'changed')
    def test_restore_rejects_traversal_before_writes(self):
        folder=self.h.backup_dir('g1');folder.mkdir(parents=True);name='20260101-120000-abcdef.zip'
        for bad in ('../escape','/absolute','C:/absolute','folder\\escape'):
            # Set the stored name explicitly: ZipInfo normalizes backslashes on Windows.
            entry=zipfile.ZipInfo();entry.filename=bad
            with zipfile.ZipFile(folder/name,'w') as z:z.writestr(entry,'bad')
            with self.assertRaises(ValueError):self.call('restore',id='g1',name=name)
            self.assertEqual((self.save/'slot.sav').read_text(),'original')
    def test_backup_and_restore_block_active_game(self):
        first=self.call('backup',id='g1')['name'];self.app.launch('g1')
        for action in ('backup','restore'):
            with self.assertRaisesRegex(ValueError,'Close the emulator'):self.call(action,id='g1',name=first)
    def test_portable_reconnect_repairs_only_missing_game(self):
        self.app.picker=lambda *a:str(self.game.parent)
        roots=self.call('root-add',system='Xbox 360');rid=roots[0]['id']
        moved=self.root/'moved';self.game.parent.rename(moved);self.app.picker=lambda *a:str(moved)
        preview=self.call('root-relink',rootId=rid);self.assertEqual(len(preview['proposals']),1)
        state=self.call('repair-apply',ids=['g1']);self.assertEqual(state['games'][0]['nativePath'],str(moved/'game.xex'))
        self.assertEqual(self.call('repair')['missing'],[])
    def test_portable_links_never_escape_root(self):
        self.h.data['roots']=[{'id':'r','system':'Xbox 360','path':str(self.game.parent)}]
        self.h.data['games']['g1'].update(rootId='r',relativePath='../emulator.exe')
        self.game.unlink();self.assertEqual(self.call('repair')['proposals'],[])
    def test_scan_preserves_review_before_import(self):
        self.app.picker=lambda *a:str(self.game.parent);self.call('root-add',system='Xbox 360')
        (self.game.parent/'new.xex').write_text('new');result=self.call('scan')
        self.assertEqual(len(result['batches'][0]['files']),2);self.assertEqual(len(self.app.state['games']),1)
    def test_per_game_arguments_are_literal_and_override_emulator(self):
        other=self.root/'other.exe';other.touch();config=self.root/'profile.ini';config.touch()
        self.h.data['games']['g1'].update(emulator=str(other),configPath=str(config))
        self.call('save-game',id='g1',patch={'arguments':['--config','{config}','{game}','& echo unsafe']})
        self.app.launch('g1');self.spawn.assert_called_once_with([str(other),'--config',str(config),str(self.game),'& echo unsafe'],cwd=str(self.root),shell=False)
    def test_missing_custom_config_prevents_launch(self):
        self.call('save-game',id='g1',patch={'arguments':['{config}']})
        with self.assertRaisesRegex(ValueError,'configuration file'):self.app.launch('g1')
        self.spawn.assert_not_called()
    def test_process_session_counted_once(self):
        with patch('features.time.monotonic',side_effect=[10,135]):
            self.app.launch('g1');self.process.poll.return_value=0;self.app.status();self.app.status()
        self.assertEqual(self.h.data['games']['g1']['playSeconds'],125)
        self.assertEqual(len(self.h.data['games']['g1']['sessions']),1)
    def test_auto_backup_happens_before_launch(self):
        self.call('prefs',autoBackup=True);self.app.launch('g1')
        self.assertEqual(len(self.call('backups',id='g1')['backups']),1)
    def test_metadata_validation_and_restore_preserves_local_paths(self):
        self.call('save-game',id='g1',patch={'rating':4,'collections':['Favourite','Favourite'],'description':'Hello'})
        old=copy.deepcopy(self.h.data)
        for patch_data in ({'rating':7},{'collections':[3]},{'screenshots':['javascript:alert(1)']},{'arguments':['a']*65}):
            with self.assertRaises(ValueError):self.call('save-game',id='g1',patch=patch_data)
            self.assertEqual(self.h.data,old)
        self.call('restore-hub',backup={'version':1,'games':{'g1':{'rating':5,'savePath':'malicious','emulator':'wrong.exe','description':'Restored'}}})
        self.assertEqual(self.h.data['games']['g1']['rating'],5);self.assertEqual(self.h.data['games']['g1']['savePath'],str(self.save));self.assertNotIn('emulator',self.h.data['games']['g1'])
    def test_disc_group_validation_and_ungroup(self):
        self.app.state['games'].append(dict(self.app.state['games'][0],id='g2',path='disc2.xex'))
        self.call('group',ids=['g1','g2']);self.assertEqual(self.h.data['games']['g2']['discParent'],'g1')
        self.call('ungroup',id='g2');self.assertNotIn('discParent',self.h.data['games']['g1'])
        self.app.state['games'][1]['system']='NES'
        with self.assertRaises(ValueError):self.call('group',ids=['g1','g2'])
    def test_metadata_requires_selected_match_and_keeps_cover_without_artwork(self):
        with self.assertRaises(ValueError):self.call('metadata-apply',id='g1',pageId='10')
        with patch.object(self.h,'wiki',return_value={'query':{'pages':[{'pageid':10,'title':'Game','extract':'Description'}]}}):
            result=self.call('metadata-search',query='Game');self.assertEqual(result['matches'][0]['pageId'],'10')
        self.call('metadata-apply',id='g1',pageId='10');self.assertEqual(self.h.data['games']['g1']['description'],'Description')
    def test_health_reports_missing_executable(self):
        self.exe.unlink();health=self.call('health');x=next(c for c in health['systems'] if c['system']=='Xbox 360');self.assertFalse(x['exists'])
    def test_update_progress_and_digest(self):
        import hashlib
        payload=b'installer';update={'available':True,'latest':'9.0.0','download':'https://github.com/IGN1TE/GoldenEmulator/releases/download/v9.0.0/GoldenEmulator-Setup-9.0.0.exe','name':'GoldenEmulator-Setup-9.0.0.exe','size':len(payload),'digest':'sha256:'+hashlib.sha256(payload).hexdigest()};events=[]
        with patch.object(ge,'check_updates',return_value=update),patch('urllib.request.urlopen',return_value=io.BytesIO(payload)),patch.object(ge.subprocess,'Popen'):
            ge.install_update(self.app.data_dir,progress=lambda *x:events.append(x))
        self.assertEqual([e[0] for e in events],['checking','downloading','verifying','installing'])

if __name__=='__main__':unittest.main()
