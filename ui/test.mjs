import puppeteer from 'puppeteer-core';
import fs from 'fs';
const out='shots'; fs.mkdirSync(out,{recursive:true});
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox','--window-size=1600,900']});
const p=await b.newPage(); await p.setViewport({width:1600,height:900});
const logs=[]; p.on('console',m=>logs.push(m.type()+': '+m.text())); p.on('pageerror',e=>logs.push('PAGEERROR: '+e.message));
const client=await p.createCDPSession(); await client.send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:process.cwd()+'/'+out});
await p.goto('file://'+process.cwd()+'/ui/vanta.html'); await new Promise(r=>setTimeout(r,2500));
const step=async(name,fn)=>{try{const r=await p.evaluate(fn);console.log('STEP',name,'OK',JSON.stringify(r)??'');}catch(e){console.log('STEP',name,'FAIL',e.message);} await new Promise(r=>setTimeout(r,1500)); await p.screenshot({path:`${out}/${name}.png`});};
const A='https://cdn.jsdelivr.net/gh/mrdoob/three.js@r147/examples/models/gltf/DamagedHelmet/glTF-Binary/DamagedHelmet.glb';
const B='https://cdn.jsdelivr.net/gh/KhronosGroup/glTF-Sample-Models@master/2.0/ToyCar/glTF-Binary/ToyCar.glb';
await step('0_boot',()=>({ready:!!window.__vantaReady,kb:!!(window.VANTA&&VANTA.kitbash)}));
await step('1_loadA',async()=>{await VANTA.loadFromURL(arguments[0]); return VANTA.state.fileName;}).catch(()=>{});
await p.evaluate(async(A)=>{await VANTA.loadFromURL(A);},A); await new Promise(r=>setTimeout(r,4000)); await p.screenshot({path:`${out}/1_A.png`});
await p.evaluate(async(B)=>{const r=await fetch(B);const bl=await r.blob();await VANTA.kitbash.loadIntoB([new File([bl],'ToyCar.glb')]);},B); await new Promise(r=>setTimeout(r,4000)); await p.screenshot({path:`${out}/2_AB.png`});
await step('3_selectB_attach',()=>{let m=null;VANTA.kitbash.bay.traverse(o=>{if(o.isMesh&&!m)m=o;});const pre=VANTA.state.model?(()=>{let n=0;VANTA.state.model.traverse(o=>{if(o.isMesh)n++});return n})():0;
  // simulate selection via internal path: dispatch is hard; use attach API after programmatic selection
  window.__sel=m; return {picked:m&&m.name,meshesA:pre};});
const box=await p.evaluate(()=>{const c=document.querySelector('canvas').getBoundingClientRect();return {x:c.left,y:c.top,w:c.width,h:c.height};});
// click on bay B region: project its centre to screen
const scr=await p.evaluate(()=>{const v=new THREE.Box3().setFromObject(VANTA.kitbash.bay).getCenter(new THREE.Vector3()).project(VANTA.camera);const c=document.querySelector('canvas').getBoundingClientRect();return {x:c.left+(v.x+1)/2*c.width,y:c.top+(1-v.y)/2*c.height};});
await p.mouse.move(scr.x,scr.y); await p.mouse.down(); await p.mouse.up(); await new Promise(r=>setTimeout(r,800));
console.log('SEL', await p.evaluate(()=>document.getElementById('kb-sel').textContent));
await p.screenshot({path:`${out}/3_sel.png`});
await p.keyboard.down('Control'); await p.keyboard.press('KeyD'); await p.keyboard.up('Control'); await new Promise(r=>setTimeout(r,1500));
console.log('AFTER ATTACH', await p.evaluate(()=>{let n=0;VANTA.state.model.traverse(o=>{if(o.isMesh)n++});return {meshesA:n,sel:document.getElementById('kb-sel').textContent};}));
await p.screenshot({path:`${out}/4_attached.png`});
// clip-on: toggle and click top of A
await p.click('#kb-clip');
const top=await p.evaluate(()=>{const bb=new THREE.Box3().setFromObject(VANTA.pivot);const v=new THREE.Vector3((bb.min.x+bb.max.x)/2,bb.max.y*0.8,(bb.min.z+bb.max.z)/2).project(VANTA.camera);const c=document.querySelector('canvas').getBoundingClientRect();return {x:c.left+(v.x+1)/2*c.width,y:c.top+(1-v.y)/2*c.height};});
await p.mouse.move(top.x,top.y); await p.mouse.down(); await p.mouse.up(); await new Promise(r=>setTimeout(r,1200));
await p.click('#kb-clip'); await p.screenshot({path:`${out}/5_clipped.png`});
// undo / redo
await p.click('#kb-undo'); await new Promise(r=>setTimeout(r,500)); await p.click('#kb-redo');
// extract: select helmet mesh, place box, extract
await p.evaluate(()=>{const kb=VANTA.kitbash;});
const hel=await p.evaluate(()=>{const bb=new THREE.Box3().setFromObject(VANTA.state.model);const v=bb.getCenter(new THREE.Vector3()).project(VANTA.camera);const c=document.querySelector('canvas').getBoundingClientRect();return {x:c.left+(v.x+1)/2*c.width,y:c.top+(1-v.y)/2*c.height};});
await p.mouse.move(hel.x,hel.y); await p.mouse.down(); await p.mouse.up(); await new Promise(r=>setTimeout(r,600));
console.log('SEL2', await p.evaluate(()=>document.getElementById('kb-sel').textContent));
await p.click('#kb-box'); await new Promise(r=>setTimeout(r,600)); await p.click('#kb-ext'); await new Promise(r=>setTimeout(r,3000));
console.log('AFTER EXTRACT', await p.evaluate(()=>document.getElementById('kb-sel').textContent));
await p.screenshot({path:`${out}/6_extract.png`});
await p.click('#kb-expA'); await p.click('#kb-expB'); await new Promise(r=>setTimeout(r,4000));
console.log('ASK', await p.evaluate(()=>{VANTA.updateAsk();return document.getElementById('ask-out').value.split('KITBASH')[1];}));
console.log('FILES', fs.readdirSync(out).join(' '));
console.log(logs.filter(l=>/error|PAGEERROR|warn/i.test(l)).slice(0,20).join('\n'));
await b.close();
