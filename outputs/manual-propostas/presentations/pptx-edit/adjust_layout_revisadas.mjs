import { pathToFileURL } from 'node:url';
import path from 'node:path';
const artifact = await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const { PresentationFile, FileBlob } = artifact;
const base='C:/GestaoVersus/app32/Propostas/Revisadas';
function getShape(slide,id){return slide.elements.items.find(e=>String(e.toSnapshot?.().id)===String(id));}
function adjust(slide,id,{text,frame,fontSize}){
 const e=getShape(slide,id); if(!e){console.warn('missing',slide.index,id); return;}
 if(text!==undefined) e.text=String(text).trim();
 if(frame) e.position=frame;
 if(fontSize && e.text) e.text.fontSize=fontSize;
}
async function process(file, ops){
 const p=path.join(base,file);
 const pres=await PresentationFile.importPptx(await FileBlob.load(p));
 for(const op of ops){ adjust(pres.slides.items[op.slide-1], op.id, op); }
 const pptx=await PresentationFile.exportPptx(pres);
 await pptx.save(p);
 console.log('adjusted',p);
}
await process('Proposta_Comercial_Versus_Performance_Hub_Revisada.pptx', [
 {slide:7,id:6,fontSize:22,frame:{left:340,top:135,width:1320,height:720},text:'Nossa proposta permite que empresas menores acessem uma estrutura de gestão antes restrita a grandes organizações.\n\nInvestimento:\n• Parcela fixa mensal: R$ [valor]\n• Parcela variável por metas/resultados: R$ [critério]\n\nSem fidelidade obrigatória e sem multa rescisória, quando aplicável.'},
 {slide:8,id:8,fontSize:26,frame:{left:320,top:185,width:1300,height:500},text:'Condição de entrada com risco reduzido\n\nProposta válida até [data].\n\nA continuidade será revisada com base em utilidade percebida, aderência da cadência e evolução real da gestão.'}
]);
await process('Proposta_Brazilian_Nickel_Servicos_Pontuais_Revisada.pptx', [
 {slide:4,id:3,fontSize:22,frame:{left:585,top:105,width:1220,height:820}},
 {slide:5,id:3,fontSize:24,frame:{left:585,top:120,width:1220,height:760}},
 {slide:6,id:3,fontSize:23,frame:{left:585,top:115,width:1220,height:780}},
 {slide:7,id:3,fontSize:24,frame:{left:585,top:150,width:1220,height:680}},
 {slide:9,id:3,fontSize:24,frame:{left:585,top:150,width:1180,height:720}},
 {slide:12,id:6,fontSize:21,frame:{left:335,top:80,width:1500,height:850}},
 {slide:13,id:6,fontSize:24,frame:{left:335,top:185,width:1450,height:650}}
]);
await process('Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx', [
 {slide:3,id:3,fontSize:21,frame:{left:585,top:105,width:1220,height:820}},
 {slide:5,id:3,fontSize:23,frame:{left:585,top:145,width:1180,height:720}},
 {slide:7,id:6,fontSize:27,frame:{left:340,top:145,width:1350,height:750},text:'O investimento para esta etapa será de:\n\nR$ 6.500,00\n(seis mil e quinhentos reais)\n\nForma de pagamento:\n• 50% no início dos trabalhos;\n• 50% na entrega do relatório final.\n\nO valor considera volume de trabalho, conhecimento necessário e impacto esperado na qualidade da decisão.'}
]);
