import { pathToFileURL } from 'node:url';
const artifact=await import(pathToFileURL('C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const {PresentationFile,FileBlob}=artifact;
const p='C:/GestaoVersus/app32/Propostas/Revisadas/Proposta_Britos_Mag_Servicos_Pontuais_Revisada.pptx';
const pres=await PresentationFile.importPptx(await FileBlob.load(p));
const s=pres.slides.items[2];
for (const id of ['3']) { const e=s.elements.items.find(e=>String(e.toSnapshot?.().id)===id); if(e) e.text=''; }
function addText({text,left,top,width,height,fontSize=26,color='#ffffff',bold=false}){const shape=s.shapes.add({geometry:'rect',position:{left,top,width,height},fill:'#00000000',line:{style:'solid',fill:'#00000000',width:0}}); shape.text=text; shape.text.fontSize=fontSize; shape.text.color=color; shape.text.bold=bold; return shape;}
addText({left:860,top:115,width:930,height:95,fontSize:25,bold:true,color:'#43e3ba',text:'Atenderemos às necessidades apresentadas em reunião com Wilson Caldas e Priscila.'});
addText({left:860,top:260,width:930,height:60,fontSize:25,bold:true,text:'Escopo proposto:'});
addText({left:860,top:380,width:940,height:430,fontSize:23,text:'→ definição e estruturação legal do negócio;\n\n→ análise das atividades: intermediação, monitoramento, instalação, recebimento de valores de terceiros, patrimônio e indústria de energia;\n\n→ enquadramento e planejamento tributário conforme alternativas disponíveis na legislação atual.'});
const pptx=await PresentationFile.exportPptx(pres); await pptx.save(p); console.log('overlay fixed',p);
