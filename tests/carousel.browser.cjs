const test=require('node:test');
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');

test('carousel navigation preserves scroll and focus during selection and rapid input',async()=>{
  const html=fs.readFileSync(process.env.GE_TEST_HTML||path.join(__dirname,'../GoldenEmulator.html'));
  const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({headless:true,...(process.env.GE_BROWSER_CHANNEL?{channel:process.env.GE_BROWSER_CHANNEL}:{})});
    const page=await browser.newPage({viewport:{width:1360,height:860}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.waitForFunction(()=>typeof ready!=='undefined'&&ready);
    const next=page.getByRole('button',{name:'Next system',exact:true});
    for(let i=0;i<5;i++)await next.click();
    await page.waitForTimeout(1500);
    const before=await page.locator('.carousel').evaluate(el=>el.scrollLeft);
    assert.ok(before>1000,'Test must start well beyond the first consoles');
    await next.focus();
    await page.keyboard.press('Enter');
    assert.equal(await next.evaluate(el=>el===document.activeElement),true,'Next button lost keyboard focus');
    const after=await page.locator('.carousel').evaluate(el=>el.scrollLeft);
    assert.ok(after>before-50,`Selection jumped back from ${before} to ${after}`);
    assert.equal(await page.locator('.system.selected').getAttribute('data-system'),'7');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('.system.selected').getAttribute('data-system'),'8');
    await page.waitForTimeout(1500);
    const visible=await page.locator('.system.selected').evaluate(el=>{
      const card=el.getBoundingClientRect(),rail=el.parentElement.getBoundingClientRect();
      const m=el.querySelector('svg').getScreenCTM();
      return {inside:card.left>=rail.left-1&&card.right<=rail.right+1,uniform:Math.abs(m.a-m.d)<.001};
    });
    assert.ok(visible.inside,'Final selected card must be visible');assert.ok(visible.uniform);
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('.system.selected').getAttribute('data-system'),'0','Wraparound selects first console');
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('.system.selected').getAttribute('data-system'),'9');
    assert.deepEqual(errors,[]);
  }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
});

