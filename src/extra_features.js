/* GoldenEmulator optional UI expansion. Does not change saved library schema. */
(() => {
 'use strict';
 const KEY='ge-ui-preferences-v1';
 const themes=['neon','gold','midnight'];
 const safeRead=()=>{try {const p=JSON.parse(localStorage.getItem(KEY)||'{}');return {theme:themes.includes(p.theme)?p.theme:'neon',compact:p.compact===true,largeText:p.largeText===true};}catch{return {theme:'neon',compact:false,largeText:false};}};
 let prefs=safeRead();
 function apply(){document.body.classList.toggle('ge-large-text',prefs.largeText);try{localStorage.setItem(KEY,JSON.stringify(prefs));}catch{}}
 function csvValue(v){const text=String(v??'');const safe=/^[\s]*[=+@\-]/.test(text)?"'"+text:text;return '"'+safe.replace(/"/g,'""')+'"';}
 function exportCsv(){
  const rows=(typeof state!=='undefined'&&Array.isArray(state.games))?state.games:[];
  const cols=['title','system','format','size','favorite','notes','path','launchCount','lastPlayed'];
  const lines=[cols.map(csvValue).join(',')].concat(rows.map(g=>cols.map(k=>csvValue(g[k])).join(',')));
  const blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='GoldenEmulator-library.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function dashboard(){
  const games=(typeof state!=='undefined'&&Array.isArray(state.games))?state.games:[];
  const bySystem=new Map();for(const g of games)bySystem.set(g.system,(bySystem.get(g.system)||0)+1);
  const totalBytes=games.reduce((n,g)=>n+(Number(g.size)||0),0);
  return `<div class="ge-metrics"><div><strong>${games.length}</strong><small>Games</small></div><div><strong>${games.filter(g=>g.favorite).length}</strong><small>Favourites</small></div><div><strong>${games.reduce((n,g)=>n+(Number(g.launchCount)||0),0)}</strong><small>Launches</small></div><div><strong>${(totalBytes/1073741824).toFixed(1)} GB</strong><small>Library file sizes</small></div></div><h3>By console</h3><div class="ge-systems">${[...bySystem].sort((a,b)=>b[1]-a[1]).map(([name,count])=>`<div><span>${esc(name)}</span><strong>${count}</strong></div>`).join('')||'<p>No games imported yet.</p>'}</div>`;
 }
 function openPanel(){
  const dialog=document.getElementById('modal');if(!dialog)return;
  if(dialog.open)dialog.close();
  dialog.innerHTML=`<div class="dialog-top"><span>GOLDENEMULATOR · EXTRA TOOLS</span><button class="close" id="ge-close" aria-label="Close">×</button></div><h2>Library dashboard</h2><label class="ge-toggle"><input type="checkbox" id="ge-large-text"> Larger text</label><h2>Library overview</h2>${dashboard()}<div class="actions"><button class="secondary" id="ge-export">Export library CSV</button><button class="secondary" id="ge-random">Random game</button><button class="secondary" id="ge-backup">Export JSON backup</button></div><p class="note">These settings stay on this computer. The original library format is unchanged. Shortcuts: Alt+G opens tools, / searches, Esc closes.</p>`;
  dialog.showModal();
  dialog.querySelector('#ge-close').onclick=()=>dialog.close();
  const large=dialog.querySelector('#ge-large-text');large.checked=prefs.largeText;large.onchange=()=>{prefs.largeText=large.checked;apply();};
  dialog.querySelector('#ge-export').onclick=exportCsv;
  dialog.querySelector('#ge-backup').onclick=()=>{if(typeof exportBackup==='function')exportBackup();};
  dialog.querySelector('#ge-random').onclick=()=>{const games=(typeof state!=='undefined'&&Array.isArray(state.games))?state.games:[];if(!games.length){if(typeof toast==='function')toast('Import games first.');return;}const game=games[Math.floor(Math.random()*games.length)];dialog.close();if(typeof details==='function')details(game.id);};
 }
 function init(){apply();const tools=document.querySelector('header .tools');if(!tools||document.getElementById('ge-extra-tools'))return;const button=document.createElement('button');button.id='ge-extra-tools';button.type='button';button.setAttribute('aria-label','Library dashboard');button.title='Library dashboard (Alt+G)';button.textContent='▥';button.onclick=openPanel;tools.prepend(button);document.addEventListener('keydown',e=>{if(e.altKey&&e.key.toLowerCase()==='g'){e.preventDefault();openPanel();}});}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
