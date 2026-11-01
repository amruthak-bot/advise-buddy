const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('frontend/index.html', 'utf8');
const code = html.slice(html.indexOf('function showDrawer('), html.indexOf('async function runAnalysis('));
const elements = {};
let clicks = 0;
const box = elements.drawer = {innerHTML:'', classList:{remove(){}}, scrollIntoView(){assert.ok(this.innerHTML.includes('Question'));}, focus(){}};
elements.exportStatus = {innerHTML:'', appendChild(a){this.link=a;}, scrollIntoView(){}};
const document = {getElementById:id=>elements[id], body:{appendChild(a){a.attached=true;}}, createElement:()=>({click(){assert.ok(this.attached);clicks++;},remove(){this.attached=false;}})};
const res = {question:'Test', findings:[], blueprint:{items:[{id:'q',label:'Question'}]}, sources:[{id:'s',title:'Source',text:'Text',type:'official',url:'https://example.org'}], sourceFreshness:{}, comparisons:[]};
const context = {document,Blob,URL,Date,lastResult:res,manualClosed:{},lastAutoClosed:[],esc:s=>String(s||''),CELL:{stated:['green','Stated']},openChecks:()=>[]};
vm.createContext(context); vm.runInContext(code,context);
for (const status of ['silent','error','stated']) {
 res.findings=[{itemId:'q',sourceId:'s',status,quote:status==='stated'?'Exact quote':null,quoteVerified:true}];
 box.innerHTML='';context.showDrawer('q','s');
 assert.match(box.innerHTML,status==='silent'?/no usable answer/:status==='error'?/Not fetched/:/Exact quote/);
}
context.exportReport();assert.equal(clicks,1);assert.match(elements.exportStatus.innerHTML,/Checklist prepared/);assert.equal(elements.exportStatus.link.download,'advise-buddy-checklist.md');
context.exportReport();assert.equal(clicks,2);URL.revokeObjectURL(context.exportReport.previousUrl);
console.log('Frontend feedback checks passed: silent/error/quoted cells and repeat export.');
