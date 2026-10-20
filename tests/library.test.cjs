const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../src/app.js'),'utf8');
const context=vm.createContext({ART:'data:image/jpeg;base64,',window:{},document:{getElementById:()=>({})},console});
vm.runInContext(source.slice(0,source.lastIndexOf("\ndocument.querySelectorAll('[data-page]')"))+'\nglobalThis.api={planImport,validateBackup,titleFrom,esc};',context);
const {planImport,validateBackup,titleFrom,esc}=context.api;
const file=(p,n=100)=>({name:p.split('/').pop(),webkitRelativePath:p,size:n,lastModified:123});
const game={id:'one',title:'Test',system:'GameCube',path:'Games/Test.iso',size:100,cover:'',favorite:true,notes:'hello',added:10};
test('folder scan accepts target formats, skips unrelated files and duplicates',()=>{const r=planImport([file('Games/Test.iso'),file('Games/Second.rvz'),file('Games/readme.txt'),file('Games/archive.zip')],'GameCube',[game]);assert.equal(r.games.length,1);assert.equal(r.games[0].title,'Second');assert.equal(r.duplicates,1);assert.equal(r.ignored,2)});
test('same filename in different subfolders stays distinct; case duplicates skipped',()=>{const r=planImport([file('Xbox/Halo/default.xex'),file('Xbox/Gears/default.xex'),file('xbox/halo/DEFAULT.XEX')],'Xbox 360',[]);assert.equal(r.games.length,2);assert.equal(r.games[0].title,'Halo');assert.equal(r.games[1].title,'Gears');assert.equal(r.duplicates,1)});
test('PS2 cue/bin pairing imports only the cue entry',()=>{const r=planImport([file('PS2/Game.cue'),file('PS2/Game.bin'),file('PS2/Other.bin')],'PlayStation 2',[]);assert.equal(r.games.length,2);assert.equal(r.games[0].format,'CUE');assert.equal(r.ignored,1)});
test('PS5 ignores arbitrary BIN assets and recognizes eboot/pkg without compatibility claims',()=>{const r=planImport([file('PS5/Game/eboot.bin'),file('PS5/Game/data.bin'),file('PS5/Other.pkg')],'PlayStation 5',[]);assert.equal(r.games.length,2);assert.equal(r.games[0].title,'Game')});
test('backup round trip preserves favourite, notes and art',()=>{const data={version:2,games:[{...game,cover:'data:image/jpeg;base64,YQ=='}]};const r=validateBackup(JSON.parse(JSON.stringify(data)));assert.equal(r.games[0].favorite,true);assert.equal(r.games[0].notes,'hello');assert.equal(r.games[0].cover,data.games[0].cover)});
test('backup rejects duplicate IDs, duplicate paths and invalid systems',()=>{assert.throws(()=>validateBackup({version:2,games:[game,game]}));assert.throws(()=>validateBackup({version:2,games:[game,{...game,id:'two'}]}));assert.throws(()=>validateBackup({version:2,games:[{...game,system:'invalid'}]}))});
test('backup rejects external or executable artwork and invalid size',()=>{for(const cover of ['https://example.com/track.png','data:image/svg+xml;base64,YQ==','javascript:alert(1)'])assert.throws(()=>validateBackup({version:2,games:[{...game,cover}]}));assert.throws(()=>validateBackup({version:2,games:[{...game,size:-1}]}));assert.throws(()=>validateBackup({version:1,games:[]}))});
test('file-derived text is escaped for rendering',()=>{assert.equal(esc('<img onerror="x">&'), '&lt;img onerror=&quot;x&quot;&gt;&amp;');assert.equal(titleFrom('GC/My_Game.iso'),'My Game')});
test('new console formats import and round trip',()=>{
  for(const [system,path] of [['SNES','Mario.sfc'],['NES','Mario.nes'],['Wii','Sports.wbfs'],['PlayStation 1','Game.chd'],['PlayStation 3','Game/USRDIR/EBOOT.BIN'],['PlayStation 4','Game/eboot.bin']]){
    const result=planImport([file(path)],system,[]);
    assert.equal(result.games.length,1,system);
    assert.equal(validateBackup({version:2,games:[{...result.games[0],id:'new'}]}).games[0].system,system);
  }
});
test('PS3 and PS4 ignore arbitrary BIN data and package installers',()=>{
  for(const system of ['PlayStation 3','PlayStation 4']){
    const result=planImport([file('Game/eboot.bin'),file('Game/assets.bin'),file('Game.pkg')],system,[]);
    assert.equal(result.games.length,1);assert.equal(result.ignored,2);
  }
});
test('artwork preserves aspect ratio and selected card never scales one axis',()=>{
  const result=vm.runInContext('art([54,92,363,327])',context);
  assert.match(result,/viewBox="54 92 363 327"/);
  assert.match(result,/preserveAspectRatio="xMidYMid meet"/);
  assert.doesNotMatch(result,/style=/);
  assert.doesNotMatch(fs.readFileSync(require('node:path').join(__dirname,'../src/shell.html'),'utf8'),/scale[XY]\(/);
});
