/* Stand-in for the database, used only when building landing data in a headless browser. */
(()=>{const store={};const subs=[];
const colOf=p=>p.split("/").slice(0,-1).join("/");
function snapCol(c){const docs=Object.keys(store).filter(k=>colOf(k)===c).map(k=>({id:k.split("/").pop(),data:()=>JSON.parse(JSON.stringify(store[k])),exists:true}));return {docs}}
function fire(){subs.forEach(s=>s.fn(snapCol(s.c)))}
let n=0;
const docRef=p=>({get:async()=>({exists:p in store,data:()=>store[p]&&JSON.parse(JSON.stringify(store[p]))}),set:async d=>{store[p]=JSON.parse(JSON.stringify(d));setTimeout(fire)},update:async d=>{store[p]=Object.assign({},store[p],JSON.parse(JSON.stringify(d)));setTimeout(fire)},delete:async()=>{delete store[p];setTimeout(fire)}});
const db={collection:c=>({onSnapshot:(fn,err)=>{subs.push({c,fn});setTimeout(()=>fn(snapCol(c)));return()=>{}},add:async d=>{const id="d"+(++n);store[c+"/"+id]=JSON.parse(JSON.stringify(d));setTimeout(fire);return docRef(c+"/"+id)},doc:id=>docRef(c+"/"+id)}),doc:docRef};
window.__store=store;let up=0;
const caps={db,user:{canEdit:async()=>true,id:async()=>"u1",isOwner:async()=>true},assets:{upload:async b=>{up++;window.__up=(window.__up||0)+1;return {id:"a"+up+"x".repeat(10),url:"/_blob/a"+up,sizeBytes:b.size,contentType:"image/jpeg"}}},downloads:{save:async r=>{window.__dl=r;return {saved:true}}}};
window.claude={use:async k=>caps[k]||null};})();
