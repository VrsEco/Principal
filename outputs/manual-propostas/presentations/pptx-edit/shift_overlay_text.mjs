import { pathToFileURL } from 'node:url';
import path from 'node:path';
const artifact=await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {PresentationFile,FileBlob}=artifact;
const base='C:/GestaoVersus/app32/Propostas/Revisadas';
function get(slide,id){return slide.elements.items.find(e=>String(e.toSnapshot?.().id)===String(id));}
function set(slide,id,frame,fontSize){const e=get(slide,id); if(e){e.position=frame; if(fontSize) e.text.fontSize=fontSize;}}
async function save(file, ops){const p=path.join(base,file); const pres=await PresentationFile.importPptx(await FileBlob.load(p)); for(const o of ops){set(pres.slides.items[o.slide-1],o.id,o.frame,o.fontSize);} const pptx=await PresentationFile.exportPptx(pres); await pptx.save(p); console.log('shifted',p);}
await save('Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx',[
 {slide:5,id:7,fontSize:24,frame:{left:860,top:170,width:900,height:70}},
 {slide:5,id:8,fontSize:22,frame:{left:860,top:285,width:900,height:500}},
 {slide:3,id:3,fontSize:17,frame:{left:880,top:85,width:900,height:850}}
]);
await save('Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx',[
 {slide:9,id:8,fontSize:24,frame:{left:860,top:170,width:900,height:70}},
 {slide:9,id:9,fontSize:22,frame:{left:860,top:285,width:900,height:500}}
]);
