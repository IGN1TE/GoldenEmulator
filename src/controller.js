/* Standard Gamepad mapping. Input decoding is independent of the DOM. */
const ControllerInput = (() => {
  function read(pad) {
    if (!pad || pad.mapping !== 'standard') return '';
    const down = i => !!pad.buttons[i]?.pressed;
    if (down(1)) return 'back';
    if (down(0)) return 'accept';
    if (down(3)) return 'search';
    if (down(2)) return 'hub';
    if (down(9)) return 'collections';
    if (down(4)) return 'previous';
    if (down(5)) return 'next';
    const x=pad.axes[0]||0,y=pad.axes[1]||0;
    if (down(12)) return 'up'; if (down(13)) return 'down';
    if (down(14)) return 'left'; if (down(15)) return 'right';
    if(Math.max(Math.abs(x),Math.abs(y))<0.55) return '';
    return Math.abs(x)>Math.abs(y)?(x>0?'right':'left'):(y>0?'down':'up');
  }
  function create() {
    let last='',due=0,armed=false;
    return (action,time,enabled=true) => {
      if(!enabled){armed=false;last='';return '';}
      if(!action){armed=true;last='';return '';}
      if(!armed)return '';
      if(action!==last){last=action;due=time+420;return action;}
      if(['up','down','left','right'].includes(action)&&time>=due){due=time+150;return action;}
      return '';
    };
  }
  function neighbor(rects,current,direction) {
    const a=rects[current];if(!a)return rects.length?0:-1;
    const horizontal=direction==='left'||direction==='right',sign=direction==='left'||direction==='up'?-1:1;
    let best=-1,score=Infinity;
    rects.forEach((b,i)=>{if(i===current)return;const dx=b.x-a.x,dy=b.y-a.y,forward=(horizontal?dx:dy)*sign,cross=Math.abs(horizontal?dy:dx);if(forward<=2)return;const s=forward+cross*3;if(s<score){score=s;best=i;}});
    return best;
  }
  return {read,create,neighbor};
})();
if(typeof module!=='undefined')module.exports=ControllerInput;
else (()=>{
  const gate=ControllerInput.create();let active=false,lastPad='',saved=null,selectMode=false,dialogOrigin=null;
  const badge=document.createElement('span');badge.id='controller-status';badge.textContent='Controller: press a button to connect';document.querySelector('footer').prepend(badge);
  const scope=()=>modal.open?modal:document;
  const items=()=>[...scope().querySelectorAll('button,input:not([type="hidden"]),select,textarea')].filter(e=>!e.disabled&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&e.type!=='file');
  function remember(e){saved=e?{id:e.id,game:e.dataset.game,system:e.dataset.system,page:e.dataset.page}:null;}
  function focus(e){if(!e)return;document.querySelectorAll('.pad-focus').forEach(x=>x.classList.remove('pad-focus'));e.classList.add('pad-focus');e.focus({preventScroll:true});e.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});remember(e);}
  function restore(){const list=items();const match=saved&&list.find(e=>(saved.id&&e.id===saved.id)||(saved.game&&e.dataset.game===saved.game)||(saved.system!==undefined&&e.dataset.system===saved.system)||(saved.page&&e.dataset.page===saved.page));const target=match||list.find(e=>e.id==='launch-game')||list.find(e=>e.classList.contains('system')&&e.classList.contains('selected'))||list[0];if(target!==document.activeElement)focus(target);}
  function act(action){
    active=true;document.body.classList.add('controller-mode');
    let list=items(),e=document.activeElement;
    if(!list.includes(e)){restore();e=document.activeElement;list=items();}
    if(selectMode&&e.tagName!=='SELECT')selectMode=false;
    if(typeof LibraryHub!=='undefined'){if(action==='search'){LibraryHub.controllerSearch();queueMicrotask(restore);return;}if(action==='hub'){LibraryHub.home().catch(e=>toast(e.message));return;}if(action==='collections'){LibraryHub.nextCollection();restore();return;}}
    if(action==='back'){if(selectMode){selectMode=false;toast('Selection saved.');return;}if(modal.open){modal.close();return;}navigate('Systems');restore();return;}
    if(action==='previous'||action==='next'){if(modal.open)return;const pages=['Systems','Library','Favorites'];let i=pages.indexOf(page);navigate(pages[(Math.max(0,i)+(action==='next'?1:2))%3]);restore();return;}
    if(action==='accept'){
      if(e?.tagName==='SELECT'){selectMode=!selectMode;toast(selectMode?'Up/down changes the option. A/Cross or B/Circle finishes.':'Selection saved.');return;}
      if(['INPUT','TEXTAREA'].includes(e?.tagName)&&!['checkbox','radio'].includes(e.type)){toast('Use your keyboard to enter text.');return;}
      const origin=saved,wasOpen=modal.open;e?.click();if(!wasOpen&&modal.open)dialogOrigin=origin;queueMicrotask(restore);return;
    }
    if(selectMode){if(action==='up'||action==='down'){const options=[...e.options];let i=e.selectedIndex+(action==='down'?1:-1);while(options[i]?.disabled)i+=action==='down'?1:-1;if(options[i]){e.selectedIndex=i;e.dispatchEvent(new Event('change',{bubbles:true}));queueMicrotask(restore);}}return;}
    const rects=list.map(x=>{const r=x.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};});const n=ControllerInput.neighbor(rects,list.indexOf(e),action);if(n>=0)focus(list[n]);
  }
  modal.addEventListener('close',()=>{selectMode=false;if(active){if(!modal.open&&dialogOrigin){saved=dialogOrigin;dialogOrigin=null;}queueMicrotask(restore);}});
  document.addEventListener('pointerdown',()=>{active=false;selectMode=false;document.body.classList.remove('controller-mode');document.querySelectorAll('.pad-focus').forEach(e=>e.classList.remove('pad-focus'));});
  window.addEventListener('focus',()=>{if(active)restore();});
  function tick(time){
    try{
      const pads=Array.from(navigator.getGamepads?.()||[]).filter(Boolean),pad=pads.find(p=>p.mapping==='standard');
      const key=pad?pad.index+':'+pad.id:'';
      if(key!==lastPad){gate('',time,false);lastPad=key;badge.textContent=pad?'Controller connected · A/× Select · B/○ Back · LB/RB Pages':pads.length?'Controller mapping unsupported · use keyboard/mouse':'Controller disconnected · press a button to connect';}
      const enabled=!!pad&&!document.hidden&&document.hasFocus()&&!launchStatus.running;
      const action=gate(ControllerInput.read(pad),time,enabled);if(action)act(action);
    }catch{badge.textContent='Controller unavailable · use keyboard/mouse';gate('',time,false);}
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
