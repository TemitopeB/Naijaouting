const {chromium}=require('playwright');const fs=require('fs');const D=__dirname;
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1000,height:1000},deviceScaleFactor:1.2});
const files=fs.readdirSync(D+'/svg').filter(f=>f.endsWith('.svg'));fs.mkdirSync(D+'/p12',{recursive:true});
for(const f of files){await p.setContent('<html><body style="margin:0">'+fs.readFileSync(D+'/svg/'+f,'utf8')+'</body></html>');await p.waitForTimeout(80);await p.screenshot({path:D+'/p12/'+f.replace('.svg','.png'),clip:{x:0,y:0,width:1000,height:1000}})}
console.log(files.length);await b.close()})();
