import { pathToFileURL } from 'node:url';
import path from 'node:path';
const artifact=await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {PresentationFile, FileBlob}=artifact;
const base='C:/GestaoVersus/app32/Propostas/Revisadas';
function get(slide,id){return slide.elements.items.find(e=>String(e.toSnapshot?.().id)===String(id));}
function setFrame(slide,id,frame,fontSize){const e=get(slide,id); if(e){e.position=frame; if(fontSize) e.text.fontSize=fontSize;}}
async function process(file, ops){const p=path.join(base,file); const pres=await PresentationFile.importPptx(await FileBlob.load(p)); for(const o of ops){setFrame(pres.slides.items[o.slide-1],o.id,o.frame,o.fontSize);} const pptx=await PresentationFile.exportPptx(pres); await pptx.save(p); console.log('realigned',p);}
await process('Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx',[
 {slide:4,id:3,fontSize:20,frame:{left:880,top:105,width:900,height:820}},
 {slide:5,id:3,fontSize:21,frame:{left:880,top:120,width:900,height:760}},
 {slide:6,id:3,fontSize:20,frame:{left:880,top:115,width:900,height:780}},
 {slide:7,id:3,fontSize:21,frame:{left:880,top:150,width:900,height:680}}
]);
await process('Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx',[
 {slide:3,id:3,fontSize:19,frame:{left:880,top:105,width:900,height:820}}
]);
