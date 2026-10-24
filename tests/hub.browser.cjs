const test=require('node:test'),assert=require('node:assert/strict'),http=require('node:http'),fs=require('node:fs');
const {chromium}=require('playwright');
test('Hub game details, collections, couch mode, disc groups and controller search',async()=>{
 const html=fs.readFileSync('GoldenEmulator.html','utf8').replace('<!-- NATIVE_CONFIG -->','<script>window.GE_NATIVE={token:"test"}</script>');
 const server=http.createServer((req,res)=>res.end(html));await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,channel:process.env.GE_BROWSER_CHANNEL||undefined});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  let state={version:2,games:['Alpha','Beta'].map((title,i)=>({id:'g'+i,title,system:'Xbox 360',path:title+'.xex',size:4,cover:'',favorite:false,notes:''}))};
  const data={version:1,games:{},roots:[],collections:[],logs:[],prefs:{}};
  await page.route('**/api/**',async route=>{const url=new URL(route.request().url()).pathname,body=route.request().postDataJSON()||{};let result={};
   if(url==='/api/state'){if(route.request().method()==='POST')state=body;result=state}
   if(url==='/api/status')result={running:false};
   if(url==='/api/features'){
    if(body.action==='save-game'){data.games[body.id]={...data.games[body.id],...body.patch};data.collections=[...new Set(Object.values(data.games).flatMap(e=>e.collections||[]))]}
    if(body.action==='prefs')data.prefs=body;
    if(body.action==='group')body.ids.forEach(id=>{data.games[id]={...data.games[id],discParent:body.ids[0]}});
    result=data;
   }
   await route.fulfill({json:result});
  });
  await page.goto(`http://127.0.0.1:${server.address().port}`);await page.waitForFunction(()=>typeof ready!=='undefined'&&ready);
  await page.locator('#hub-open').click();await page.locator('#hub-couch').check();await page.locator('#hub-save-prefs').click();await page.waitForFunction(()=>document.body.classList.contains('ge-couch'));
  await page.evaluate(()=>{modal.close();details('g0')});await page.locator('#hub-game-page').click();await page.locator('#hub-edit').click();
  await page.locator('#hub-description').fill('A test game description');await page.locator('#hub-rating').selectOption('4');await page.locator('#hub-collections').fill('Playing Now');await page.locator('#hub-notes').fill('Personal note');await page.locator('#hub-save-details').click();
  await page.getByText('A test game description',{exact:true}).waitFor();assert.equal(state.games[0].notes,'Personal note');assert.equal(data.games.g0.rating,4);
  await page.evaluate(()=>{modal.close();navigate('Library')});await page.locator('#hub-collection').selectOption('Playing Now');assert.equal(await page.locator('[data-game]').count(),1);
  await page.locator('#hub-collection').selectOption('');await page.evaluate(()=>LibraryHub.gamePage('g0'));await page.locator('#hub-discs').click();await page.locator('[data-disc-id="g1"]').check();await page.locator('#hub-group').click();await page.locator('[data-disc="g1"]').waitFor();
  await page.evaluate(()=>{modal.close();navigate('Library')});assert.equal(await page.locator('[data-game]').count(),1);
  await page.evaluate(()=>LibraryHub.controllerSearch());for(const c of 'ALPHA')await page.locator('#hub-key-'+c).click();await page.locator('#hub-key-search').click();assert.equal(await page.locator('[data-game]').count(),1);assert.equal(await page.evaluate(()=>query),'ALPHA');
  assert.deepEqual(errors,[]);
 }finally{await browser.close();await new Promise(r=>server.close(r))}
});
