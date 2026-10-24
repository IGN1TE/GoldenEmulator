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
    def test_new_console_launch_contracts(self):
        cases = {
            'SNES': ('g.sfc', ['g.sfc']),
            'NES': ('g.nes', ['g.nes']),
            'Wii': ('g.wbfs', ['-b', '-e', 'g.wbfs']),
            'PlayStation 1': ('g.chd', ['-batch', '--', 'g.chd']),
            'PlayStation 3': ('EBOOT.BIN', ['--no-gui', 'EBOOT.BIN']),

        }
        for system, (game, args) in cases.items():
            with self.subTest(system=system):
                self.assertEqual(ge.launch_arguments(system, 'emulator.exe', game), ['emulator.exe'] + args)
                self.assertTrue(ge.valid_game(system, Path(game)))
                entry = dict(self.entry, system=system)
                self.assertEqual(ge.validate_state({'version':2,'games':[entry]})['games'][0]['system'], system)
        for system in ('PlayStation 3', 'PlayStation 4', 'PlayStation 5'):
            self.assertFalse(ge.valid_game(system, Path('textures.bin')))
        self.assertFalse(ge.valid_game('PlayStation 4', Path('game.pkg')))
    def test_ps4_replaces_kyty_with_shadps4_and_persists(self):
        from unittest.mock import patch
        self.app.config['PlayStation 4']=str(self.root/'kyty_emulator.exe')
        for name, args in [('shadPS4.exe',['-g']),('ShadPS4QtLauncher.exe',['-d','-g']),('shadps4-qtlauncher.exe',['-d','-g'])]:
            exe=self.root/name;exe.touch()
            game=self.root/'eboot.bin';game.touch()
            self.app.picker=lambda *unused:str(exe)
            with patch.object(ge.subprocess,'run') as probe:
                self.app.choose_emulator('PlayStation 4')
                probe.assert_not_called()
            app=ge.Launcher(self.app.data_dir,popen=self.spawn)
            self.assertEqual(app.config['PlayStation 4'],str(exe))
            self.assertEqual(app.configurations()['PlayStation 4']['name'],'shadPS4')
            app.state['games'][0].update(system='PlayStation 4',nativePath=str(game))
            app.launch('g1')
            self.spawn.assert_called_with([str(exe)]+args+[str(game)],cwd=str(self.root),shell=False)

    def test_ps4_other_exe_connects_and_opens_without_assumed_flags(self):
        self.app.picker=lambda *unused:str(self.exe)
        self.app.choose_emulator('PlayStation 4')
        self.app.state['games'][0].update(system='PlayStation 4',nativePath='')
        self.app.launch('g1')
        self.spawn.assert_called_once_with([str(self.exe)],cwd=str(self.root),shell=False)

    def test_legacy_library_and_config_survive_all_console_additions(self):
        self.app.config['PlayStation 2'] = str(self.exe)
        ge.atomic_json(self.app.config_file, self.app.config)
        before = self.app.state_file.read_bytes()
        reopened = ge.Launcher(self.app.data_dir)
        self.assertEqual(before, self.app.state_file.read_bytes())
        self.assertEqual(reopened.config, self.app.config)
        self.assertEqual(len(reopened.configurations()), 10)
        self.assertTrue(reopened.configurations()['PlayStation 5']['supported'])
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
    def test_ps5_choose_reopen_and_open_any_exe_without_game_arguments(self):
        self.app.picker=lambda kind,system:str(self.exe)
        self.app.choose_emulator('PlayStation 5')
        reopened=ge.Launcher(self.app.data_dir,popen=self.spawn)
        self.assertEqual(reopened.config['PlayStation 5'],str(self.exe))
        self.assertTrue(reopened.configurations()['PlayStation 5']['exists'])
        before=reopened.state_file.read_bytes()
        reopened.open_emulator('PlayStation 5')
        self.spawn.assert_called_once_with([str(self.exe)],cwd=str(self.root),shell=False)
        self.assertEqual(before,reopened.state_file.read_bytes())
        with self.assertRaisesRegex(ValueError,'already running'):reopened.open_emulator('PlayStation 5')

    def test_ps5_picker_cancel_and_non_exe_preserve_configuration(self):
        self.app.picker=lambda *args:''
        self.assertTrue(self.app.choose_emulator('PlayStation 5')['cancelled'])
        self.app.picker=lambda *args:str(self.game)
        with self.assertRaisesRegex(ValueError,'EXE'):self.app.choose_emulator('PlayStation 5')
        self.assertNotIn('PlayStation 5',self.app.config)

    def test_update_download_verification_and_installer_arguments(self):
        import hashlib, io
        from unittest.mock import patch
        payload=b'MZ fake installer used only with mocked Popen'
        update={'available':True,'latest':'9.0.0','download':'https://github.com/IGN1TE/GoldenEmulator/releases/download/v9.0.0/GoldenEmulator-Setup-9.0.0.exe','name':'GoldenEmulator-Setup-9.0.0.exe','size':len(payload),'digest':'sha256:'+hashlib.sha256(payload).hexdigest()}
        with patch.object(ge,'check_updates',return_value=update), patch('urllib.request.urlopen',return_value=io.BytesIO(payload)), patch.object(ge.subprocess,'Popen') as spawn:
            self.assertTrue(ge.install_update(self.app.data_dir)['installing'])
            args=spawn.call_args.args[0]
            self.assertEqual(Path(args[0]).read_bytes(),payload)
            self.assertEqual(args[1:],['/SILENT','/SP-','/NORESTART','/RESTARTAPP=1'])
            self.assertFalse(spawn.call_args.kwargs['shell'])
        for corrupt in (b'bad', payload+b'extra', b'X'*len(payload)):
            with patch.object(ge,'check_updates',return_value=update), patch('urllib.request.urlopen',return_value=io.BytesIO(corrupt)), patch.object(ge.subprocess,'Popen') as spawn:
                with self.assertRaises(ValueError):ge.install_update(self.app.data_dir)
                spawn.assert_not_called()
        with patch.object(ge,'check_updates',return_value=dict(update,digest=None)), patch.object(ge.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'verification'):ge.install_update(self.app.data_dir)
            spawn.assert_not_called()

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
        self.assertFalse(ge.select_update([release('0.6.1','current')])['available'])
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
