import { pathToFileURL } from 'node:url';
import fs from 'node:fs/promises';
import path from 'node:path';
const artifact = await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const { PresentationFile, FileBlob } = artifact;
async function saveBlob(blob, out) {
  await fs.mkdir(path.dirname(out), {recursive:true});
  await fs.writeFile(out, Buffer.from(await blob.arrayBuffer()));
}
const base='C:/GestaoVersus/app32/Propostas/Revisadas';
const files=[
 'Proposta_Comercial_Versus_Performance_Hub_Revisada.pptx',
 'Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx',
 'Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx',
];
for(const f of files){
 const pres=await PresentationFile.importPptx(await FileBlob.load(path.join(base,f)));
 const dir=`C:/GestaoVersus/app32/outputs/manual-propostas/presentations/pptx-edit/preview/${f.replace(/\.pptx$/,'')}`;
 const manifest=[];
 for(let i=0;i<pres.slides.items.length;i++){
   const slide=pres.slides.items[i];
   const out=path.join(dir,`slide-${String(i+1).padStart(2,'0')}.png`);
   try{
     const png=await pres.export({slide, format:'png', scale:0.5});
     await saveBlob(png,out);
     manifest.push(out);
   }catch(e){
     console.warn('render failed', f, i+1, e.message);
   }
 }
 console.log(JSON.stringify({file:f, slides:pres.slides.items.length, rendered:manifest.length, dir}, null, 2));
}
