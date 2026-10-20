import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import Mock
import GoldenEmulator as ge

class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.exe=self.root/'Emulator with spaces.exe';self.exe.touch()
        self.game=self.root/'Game & special name.xex';self.game.write_text('example')
        self.entry={'id':'g1','title':'Test','system':'Xbox 360','path':'Games/Test.xex','nativePath':str(self.game),'size':7,'cover':'','favorite':True,'notes':'Keep notes'}
        self.process=Mock(pid=123);self.process.poll.return_value=None
        self.spawn=Mock(return_value=self.process)
        self.app=ge.Launcher(self.root/'data',popen=self.spawn)
        self.app.config={'Xbox 360':str(self.exe)}
        self.app.save({'version':2,'games':[self.entry]})
    def tearDown(self):self.temp.cleanup()
    def test_launch_passes_separate_arguments_without_shell(self):
        result=self.app.launch('g1')
        self.assertTrue(result['started'])
        self.spawn.assert_called_once_with([str(self.exe),str(self.game)],cwd=str(self.root),shell=False)
        self.assertTrue(self.app.status()['running'])
        self.assertGreater(self.app.state['games'][0]['lastPlayed'],0)
    def test_duplicate_launch_and_exit_status(self):
        self.app.launch('g1')
        with self.assertRaisesRegex(ValueError,'already running'):self.app.launch('g1')
        self.process.poll.return_value=3
        status=self.app.status();self.assertFalse(status['running']);self.assertEqual(status['lastExit']['exitCode'],3)
    def test_missing_game_never_starts(self):
        self.game.unlink()
        with self.assertRaisesRegex(ValueError,'not found'):self.app.launch('g1')
        self.spawn.assert_not_called()
    def test_missing_emulator_never_starts(self):
        self.exe.unlink()
        with self.assertRaisesRegex(ValueError,'Set up Xenia'):self.app.launch('g1')
        self.spawn.assert_not_called()
    def test_relative_legacy_path_requires_locate(self):
        self.app.state['games'][0]['nativePath']=''
        with self.assertRaisesRegex(ValueError,'Locate game file'):self.app.launch('g1')
    def test_presets(self):
        self.assertEqual(ge.launch_arguments('GameCube','emu.exe','g.iso'),['emu.exe','-b','-e','g.iso'])
        self.assertEqual(ge.launch_arguments('PlayStation 2','emu.exe','g.iso'),['emu.exe','-batch','--','g.iso'])
        with self.assertRaisesRegex(ValueError,'PS5'):ge.launch_arguments('PlayStation 5','emu.exe','g.pkg')
    def test_saved_library_reopens_without_data_loss(self):
        other=ge.Launcher(self.root/'data')
        self.assertEqual(other.state['games'][0]['notes'],'Keep notes')
        self.assertTrue(other.state['games'][0]['favorite'])
    def test_failed_save_keeps_previous_state(self):
        with self.assertRaises(ValueError):self.app.save({'version':2,'games':[dict(self.entry,size=-2)]})
        self.assertEqual(self.app.state['games'][0]['size'],7)
        self.assertEqual(ge.Launcher(self.root/'data').state['games'][0]['size'],7)
    def test_backup_rejects_executable_art_and_duplicate_ids(self):
        with self.assertRaises(ValueError):ge.validate_state({'version':2,'games':[dict(self.entry,cover='javascript:alert(1)')]})
        with self.assertRaises(ValueError):ge.validate_state({'version':2,'games':[self.entry,self.entry]})
    def test_corrupt_library_is_not_overwritten(self):
        self.app.state_file.write_text('{broken')
        with self.assertRaises(ValueError):ge.Launcher(self.root/'data')
        self.assertEqual(self.app.state_file.read_text(),'{broken')
    def test_picker_config_and_locate(self):
        self.app.picker=lambda kind,system:str(self.exe) if kind=='emulator' else str(self.game)
        self.app.choose_emulator('Xbox 360')
        self.assertTrue(ge.Launcher(self.root/'data').config['Xbox 360'])
        self.assertEqual(self.app.locate('g1')['games'][0]['nativePath'],str(self.game))
    def test_scan_full_paths(self):
        result=ge.scan_folder(self.root,'Xbox 360')
        match=next(f for f in result['files'] if f['name']==self.game.name)
        self.assertEqual(match['nativePath'],str(self.game))
        self.assertEqual(match['size'],7)
    def test_http_requires_token_and_same_origin(self):
        server=ge.LocalServer(('127.0.0.1',0),ge.handler_for(self.app,'test-token','<!-- NATIVE_CONFIG -->','http://127.0.0.1:0',lambda:None))
        origin=f'http://127.0.0.1:{server.server_port}'
        server.RequestHandlerClass=ge.handler_for(self.app,'test-token','<!-- NATIVE_CONFIG -->',origin,lambda:None)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(origin+'/api/state')
            self.assertEqual(err.exception.code,403)
            req=urllib.request.Request(origin+'/api/state',headers={'X-GoldenEmulator-Token':'test-token'})
            self.assertEqual(json.load(urllib.request.urlopen(req))['games'][0]['title'],'Test')
            req=urllib.request.Request(origin+'/api/state',data=b'{}',headers={'Content-Type':'application/json','X-GoldenEmulator-Token':'test-token','Origin':'https://unrelated.example'})
            with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(req)
            self.assertEqual(err.exception.code,403)
        finally:server.shutdown();server.server_close()
    def test_existing_instance_can_be_found_and_stopped_with_saved_token(self):
        from unittest.mock import patch
        stopped=threading.Event()
        server=ge.LocalServer(('127.0.0.1',0),ge.handler_for(self.app,'token','', 'http://127.0.0.1:0',stopped.set))
        origin=f'http://127.0.0.1:{server.server_port}'
        server.RequestHandlerClass=ge.handler_for(self.app,'token','',origin,stopped.set)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            ge.atomic_json(self.app.data_dir/'runtime.json',{'token':'token'})
            with patch.object(ge,'PORT',server.server_port):
                self.assertTrue(ge.contact_instance(self.app.data_dir))
                self.assertTrue(ge.contact_instance(self.app.data_dir,stop=True))
                self.assertTrue(stopped.wait(2))
        finally:server.shutdown();server.server_close()
    def test_missing_or_malformed_instance_record_is_not_running(self):
        self.assertFalse(ge.contact_instance(self.app.data_dir))
        (self.app.data_dir/'runtime.json').write_text('{broken')
        self.assertFalse(ge.contact_instance(self.app.data_dir))
    def test_stale_instance_token_cannot_stop_server(self):
        from unittest.mock import patch
        stopped=threading.Event()
        server=ge.LocalServer(('127.0.0.1',0),ge.handler_for(self.app,'actual','', 'http://127.0.0.1:0',stopped.set))
        server.RequestHandlerClass=ge.handler_for(self.app,'actual','',f'http://127.0.0.1:{server.server_port}',stopped.set)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            ge.atomic_json(self.app.data_dir/'runtime.json',{'token':'stale'})
            with patch.object(ge,'PORT',server.server_port):
                self.assertFalse(ge.contact_instance(self.app.data_dir,stop=True))
                self.assertFalse(stopped.is_set())
        finally:server.shutdown();server.server_close()
    def test_update_check_uses_numeric_installer_versions_and_includes_review_releases(self):
        def release(version,tag):
            name='GoldenEmulator-Setup-'+version+'.exe'
            return {'html_url':ge.RELEASE_PREFIX+tag,'prerelease':True,'assets':[{'name':name,'browser_download_url':'https://github.com/IGN1TE/GoldenEmulator/releases/download/'+tag+'/'+name}]}
        result=ge.select_update([release('0.9.0','old'),release('0.10.0','new')])
        self.assertTrue(result['available']);self.assertEqual(result['latest'],'0.10.0');self.assertTrue(result['prerelease'])
        self.assertFalse(ge.select_update([release('0.5.0','current')])['available'])
    def test_update_check_ignores_drafts_and_external_downloads(self):
        name='GoldenEmulator-Setup-9.0.0.exe'
        release={'draft':True,'html_url':ge.RELEASE_PREFIX+'future','assets':[{'name':name,'browser_download_url':'https://github.com/IGN1TE/GoldenEmulator/releases/download/future/'+name}]}
        self.assertFalse(ge.select_update([release])['available'])
        release['draft']=False;release['assets'][0]['browser_download_url']='https://untrusted.example/file.exe'
        self.assertFalse(ge.select_update([release])['available'])
    def test_update_failure_reports_error_without_claiming_up_to_date(self):
        from unittest.mock import patch
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError,'Could not check'):ge.check_updates()
    @unittest.skipUnless(sys.platform=='win32','Windows process smoke test')
    def test_real_windows_process_with_space_path(self):
        self.game.write_text('import sys\nsys.exit(0)\n')
        app=ge.Launcher(self.root/'data')
        app.config={'Xbox 360':sys.executable}
        app.launch('g1')
        app.process.wait(timeout=10)
        self.assertEqual(app.status()['lastExit']['exitCode'],0)

if __name__=='__main__':unittest.main()
