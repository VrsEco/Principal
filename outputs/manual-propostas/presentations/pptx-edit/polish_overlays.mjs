import { pathToFileURL } from 'node:url';
import path from 'node:path';
const artifact=await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {PresentationFile, FileBlob}=artifact;
const base='C:/GestaoVersus/app32/Propostas/Revisadas';
function get(slide,id){return slide.elements.items.find(e=>String(e.toSnapshot?.().id)===String(id));}
function clear(slide,id){const e=get(slide,id); if(e) e.text='';}
function addText(slide,{text,left,top,width,height,fontSize=28,color='#ffffff',bold=false,align='left'}){
 const shape=slide.shapes.add({geometry:'rect', position:{left,top,width,height}, fill:'#00000000', line:{style:'solid', fill:'#00000000', width:0}});
 shape.text=String(text).trim();
 shape.text.fontSize=fontSize;
 shape.text.color=color;
 shape.text.bold=bold;
 shape.text.alignment=align;
 return shape;
}
async function save(file, fn){
 const p=path.join(base,file);
 const pres=await PresentationFile.importPptx(await FileBlob.load(p));
 await fn(pres);
 const pptx=await PresentationFile.exportPptx(pres);
 await pptx.save(p);
 console.log('polished',p);
}
await save('Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx', async pres=>{
 const s=pres.slides.items[8];
 clear(s,3);
 addText(s,{left:650,top:170,width:1120,height:70,fontSize:26,bold:true,color:'#43e3ba',text:'Cada frente de trabalho será estruturada como projeto:'});
 addText(s,{left:650,top:285,width:1120,height:430,fontSize:24,color:'#ffffff',text:'a) alinhamento de expectativas;\nb) início do projeto;\nc) levantamento e entrevistas;\nd) acompanhamento da execução;\ne) validações intermediárias;\nf) entrega conforme alinhamento inicial;\ng) recomendação executiva de próximos passos.'});
});
await save('Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx', async pres=>{
 const s5=pres.slides.items[4];
 clear(s5,3);
 addText(s5,{left:650,top:170,width:1120,height:70,fontSize:26,bold:true,color:'#43e3ba',text:'Cada frente será estruturada como projeto:'});
 addText(s5,{left:650,top:285,width:1120,height:430,fontSize:24,color:'#ffffff',text:'a) alinhamento de expectativas;\nb) levantamento de informações;\nc) análise técnica e consultiva;\nd) validações intermediárias;\ne) entrega do relatório final;\nf) orientação executiva sobre próximos passos.\n\nA efetividade depende da disponibilidade das informações e da participação dos responsáveis.'});
 const s7=pres.slides.items[6];
 clear(s7,6);
 addText(s7,{left:350,top:125,width:1200,height:50,fontSize:24,color:'#ffffff',text:'O investimento para esta etapa será de:'});
 addText(s7,{left:350,top:205,width:1000,height:80,fontSize:44,bold:true,color:'#43e3ba',text:'R$ 6.500,00'});
 addText(s7,{left:350,top:300,width:1100,height:45,fontSize:24,color:'#ffffff',text:'seis mil e quinhentos reais'});
 addText(s7,{left:350,top:405,width:1200,height:170,fontSize:26,bold:true,color:'#ffffff',text:'Forma de pagamento:\n• 50% no início dos trabalhos;\n• 50% na entrega do relatório final.'});
 addText(s7,{left:350,top:645,width:1250,height:120,fontSize:22,color:'#ffffff',text:'O valor considera o volume de trabalho, o conhecimento necessário, as técnicas aplicadas e o impacto esperado na qualidade da decisão.'});
});
