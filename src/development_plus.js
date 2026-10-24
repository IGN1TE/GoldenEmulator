/* GoldenEmulator Development Plus — additive, library-schema-preserving features. */
(() => {
'use strict';
const prefKey='goldenemulator-devplus-prefs-v1';
const defaults={theme:'original',density:'comfortable',motion:true};
let prefs;
try { prefs={...defaults,...JSON.parse(localStorage.getItem(prefKey)||'{}')}; } catch { prefs={...defaults}; }
function save(){try{localStorage.setItem(prefKey,JSON.stringify(prefs))}catch{} apply()}
function apply(){document.body.dataset.geTheme=prefs.theme;document.body.dataset.geDensity=prefs.density;document.body.classList.toggle('ge-reduce-motion',!prefs.motion);document.body.classList.toggle('ge-hide-empty',prefs.hideEmpty)}
function download(name,data,type='application/json'){const blob=new Blob([data],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)}
function games(){return Array.isArray(window.state?.games)?window.state.games:typeof state!=='undefined'&&Array.isArray(state.games)?state.games:[]}
function stats(){const all=games();return {games:all.length,favorites:all.filter(g=>g.favorite).length,played:all.filter(g=>g.lastPlayed).length,launches:all.reduce((n,g)=>n+(Number(g.launchCount)||0),0),systems:[...new Set(all.map(g=>g.system))].length,bytes:all.reduce((n,g)=>n+(Number(g.size)||0),0)}}
function escHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&quot;'}[c]))}
function openTools(){
 const dlg=document.getElementById('modal');if(!dlg)return;
 if(dlg.open)dlg.close();
 const s=stats();
 dlg.innerHTML=`<div class="dialog-top"><span>GOLDENEMULATOR PLUS</span><button id="ge-close" class="close" aria-label="Close">×</button></div><h2>Appearance & Library Tools</h2><div class="ge-stat-grid"><div>Games<strong>${s.games}</strong></div><div>Favourites<strong>${s.favorites}</strong></div><div>Played<strong>${s.played}</strong></div><div>Launches<strong>${s.launches}</strong></div></div><label>Theme<select id="ge-theme"><option value="original">Original</option><option value="gold">Golden Edition</option><option value="midnight">Midnight Blue</option><option value="violet">Royal Violet</option></select></label><label>Game card size<select id="ge-density"><option value="comfortable">Comfortable</option><option value="compact">Compact</option><option value="large">Large</option></select></label><label class="ge-check"><input id="ge-motion" type="checkbox"> Enable animations</label><div class="actions"><button class="primary" id="ge-export">Export library report</button><button class="secondary" id="ge-help">Keyboard shortcuts</button><button class="secondary" id="ge-reset">Reset appearance</button></div><p class="note">Appearance settings are stored on this device. Game files and library entries are not modified.</p>`;
 dlg.showModal();
 dlg.querySelector('#ge-close').onclick=()=>dlg.close();
 for(const [id,key] of [['ge-theme','theme'],['ge-density','density']]){const el=dlg.querySelector('#'+id);el.value=prefs[key];el.onchange=()=>{prefs[key]=el.value;save()}}
 for(const [id,key] of [['ge-motion','motion']]){const el=dlg.querySelector('#'+id);el.checked=prefs[key];el.onchange=()=>{prefs[key]=el.checked;save()}}
 dlg.querySelector('#ge-reset').onclick=()=>{prefs={...defaults};save();openTools()};
 dlg.querySelector('#ge-export').onclick=()=>download('GoldenEmulator-Report.json',JSON.stringify({generated:new Date().toISOString(),summary:stats(),bySystem:Object.fromEntries([...new Set(games().map(g=>g.system))].map(system=>[system,games().filter(g=>g.system===system).length]))},null,2));
 dlg.querySelector('#ge-help').onclick=()=>{dlg.querySelector('.note').textContent='Shortcuts: / Search · Esc Systems · Ctrl+Shift+G Open Plus tools · F11 Fullscreen (browser). Controller navigation remains available.'};
}
function installButton(){if(document.getElementById('ge-plus-button'))return;const tools=document.querySelector('header .tools');if(!tools)return;const b=document.createElement('button');b.id='ge-plus-button';b.textContent='✦';b.title='GoldenEmulator Plus — themes and library tools';b.setAttribute('aria-label','GoldenEmulator Plus settings');b.onclick=openTools;tools.prepend(b)}
function init(){apply();installButton();new MutationObserver(()=>{if(!document.getElementById('ge-plus-button'))installButton()}).observe(document.querySelector('header')||document.body,{childList:true,subtree:true});document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.shiftKey&&e.key.toLowerCase()==='g'){e.preventDefault();openTools()}})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
