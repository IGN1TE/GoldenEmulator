const test=require('node:test');const assert=require('node:assert/strict');const http=require('node:http');const fs=require('node:fs');const {chromium}=require('playwright');
test('PS5 setup connects custom executable and update installs without external navigation',async()=>{
 const html=fs.readFileSync('GoldenEmulator.html','utf8').replace('<!-- NATIVE_CONFIG -->','<script>window.GE_NATIVE={token:"test"}</script>');
 const server=http.createServer((req,res)=>res.end(html));await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,channel:process.env.GE_BROWSER_CHANNEL||undefined});
 try {const page=await browser.newPage();const calls=[];let connected=false;
 await page.route('**/api/**',async route=>{const url=new URL(route.request().url()).pathname;calls.push(url);let data={};
 if(url==='/api/state')data={version:2,games:[]};
 if(url==='/api/status')data={running:false};
 if(url==='/api/config'){if(route.request().method()==='POST')connected=true;data=Object.fromEntries(['SNES','NES','Wii','PlayStation 1','PlayStation 2','PlayStation 3','PlayStation 4','PlayStation 5','GameCube','Xbox 360'].map(s=>[s,{name:'Custom',path:connected?'C:\\Kyty.exe':'',exists:connected,supported:true}]));}
 if(url==='/api/open-emulator')data={started:true,warning:'Emulator opened'};
 if(url==='/api/updates')data={available:true,latest:'9.0.0'};
 if(url==='/api/install-update')data={installing:true};
 await route.fulfill({json:data});});
 await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForFunction(()=>typeof ready!=='undefined'&&ready);
 await page.evaluate(()=>emulatorSetup());await page.locator('[data-emulator="PlayStation 5"]').click();await page.locator('[data-open-emulator="PlayStation 5"]').click();assert.ok(calls.includes('/api/open-emulator'));
 await page.locator('[data-emulator="PlayStation 4"]').click();await page.locator('[data-open-emulator="PlayStation 4"]').click();assert.equal(await page.getByText('PS4: select kyty_emulator.exe',{exact:false}).count(),0);
 await page.evaluate(()=>{modal.close();document.getElementById('settings').click()});await page.locator('#check-updates').click();await page.waitForFunction(()=>!updateBusy);assert.ok(calls.includes('/api/install-update'));assert.equal(browser.contexts()[0].pages().length,1);
 }finally{await browser.close();await new Promise(r=>server.close(r));}
});
