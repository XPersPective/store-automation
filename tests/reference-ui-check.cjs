// Synthetic DOM/network check of the real event handlers; browser proof is separate.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const fields = new Map();
function field(id) {
  if (!fields.has(id)) fields.set(id, {id, value:'', disabled:false, hidden:false, handlers:{},
    classList:{add(){},remove(){}}, addEventListener(n,f){this.handlers[n]=f;},
    setAttribute(){}, removeAttribute(){}, focus(){}, append(){}, replaceChildren(){}, reset(){},
    showModal(){this.open=true;}, close(){this.open=false;}});
  return fields.get(id);
}
let posts = 0, saved;
const context = {document:{getElementById:field,createElement:()=>field('card')},
  crypto:require('node:crypto').webcrypto, AbortController, setTimeout, clearTimeout, TypeError,
  fetch:async(url, options)=>{
    if (options?.method === 'POST') {posts++; saved=JSON.parse(options.body); throw new TypeError('response lost after commit');}
    return {ok:true,json:async()=>saved ? [{...saved,created:new Date().toISOString()}] : []};
  }};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../examples/reference/app.js'),'utf8'), context);
(async()=>{
  field('new-note').handlers.click();
  field('title').value='Preserved'; field('body').value='Original';
  await field('note-form').handlers.submit({preventDefault(){}});
  assert.equal(posts,1);
  assert.equal(field('title').disabled,true);
  assert.equal(field('cancel').disabled,true);
  assert.equal(field('save').textContent,'Kaydı kontrol et');
  await field('note-form').handlers.submit({preventDefault(){}});
  assert.equal(posts,1,'readback must avoid second POST');
  assert.equal(field('editor').open,false);
  assert.equal(field('title').disabled,false);
  console.log('PASS: lost response keeps content/identity; readback avoids duplicate');
})().catch(error=>{console.error(error);process.exitCode=1;});
