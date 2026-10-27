// Focused edit of the published presentation. Leaves unrelated slides and notes intact.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {partialExplanation as copy} from './explicacao-parcial.mjs';
const [repoArg,inputArg,outputArg]=process.argv.slice(2);
if(!repoArg||!inputArg||!outputArg)throw new Error('Usage: revisar_parcial.mjs <repo> <original-pptx> <new-output-pptx>');
const repo=path.resolve(repoArg),input=path.resolve(inputArg),output=path.resolve(outputArg);
const modules=process.env.RUNTIME_NODE_MODULES,skill=process.env.PRESENTATIONS_SKILL_DIR,python=process.env.RUNTIME_PYTHON;
if(!modules||!skill||!python)throw new Error('Set bundled runtime paths as documented for build.mjs.');
if(input===output)throw new Error('Validate a separate output before replacing the published file.');
const sourceHash=crypto.createHash('sha256').update(await fs.readFile(input)).digest('hex');
if(sourceHash!=='43e8b0ea342d3f550c16465d0020f4a68380e5c296e68abb5e95fc0a1d64e247')throw new Error('Expected the published presentation from commit 526b19e.');
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=await PresentationFile.importPptx(await FileBlob.load(input));
const before=await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.id','elements.kind','elements.text','elements.position','notes.text']});
if(before.records.length!==10)throw new Error('Expected ten source slides.');
const record=i=>before.records.find(r=>r.index===i);
const owned=(i,test)=>{const hits=record(i).elements.filter(test);if(hits.length!==1)throw new Error('Ambiguous edit target on slide '+(i+1));return p.resolve(hits[0].id);};
owned(5,e=>e.kind==='textbox'&&e.text.startsWith('Um 503 síncrono')).text=copy.postgresFooter;
owned(7,e=>e.kind==='textbox'&&e.text==='A1: uma coleta parcial preservada').text=copy.title;
const table=owned(7,e=>e.kind==='table');
copy.rows.forEach((row,r)=>row.forEach((value,c)=>table.cells.set(r,c,value)));
owned(7,e=>e.kind==='textbox'&&e.text.startsWith('A1: revisão após')).text=copy.footer;
const sourceNote='Fonte: campanha R2/A1 de 27/10/2026, implementacao-java/experimento/campanhas/2026-10-27-reduzida65-r2/RESULTADOS.md e resultados-a1/. Documento consolidado no commit 771d7a621c31aaccda7359b8207979c4bc84f19d. ';
for(const [i,value] of [[0,copy.openingNotes+sourceNote],[5,copy.postgresNotes+sourceNote+'group-summary.json: postgres-stop, rate=12.'],[7,copy.notes+sourceNote+'emenda-a1/README.md e strict-sensitivity.json.']])p.resolve(record(i).id).speakerNotes.textFrame.setText(value);
const buildKey=crypto.createHash('sha256').update(output).digest('hex').slice(0,12);
const tmp=path.join(repo,'implementacao-java/.runtime/apresentacao-parcial-clara','build-'+buildKey);
await fs.mkdir(tmp,{recursive:true});await fs.mkdir(path.dirname(output),{recursive:true});
const candidate=path.join(tmp,'candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const owners=[4,5,6,7,8,9];
const result=await finalizePresentation({workspaceDir:repo,candidatePath:candidate,finalPath:output,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:owners,
 fontPolicy:{basis:'reference',families:['Arial'],referencePath:input,referenceSha256:sourceHash},verifyArtifactToolImport:true,
 receiptPath:path.join(tmp,'validation.json')});
const after=await PresentationFile.importPptx(await FileBlob.load(output));
const content=await after.inspect({select:'$.slides[*]',include:['id','index','title','elements.id','elements.kind','elements.text','elements.position','elements.style','notes.text']});
await fs.writeFile(path.join(tmp,'inspection.ndjson'),content.ndjson);
for(let i=0;i<after.slides.items.length;i++){
 const png=await after.export({slide:after.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const timing=[40,50,65,60,55,70,55,70,70,65];
const guide='# Roteiro de fala da apresentação final\n\nDez slides, duração estimada de 10 minutos. Os tempos são sugestões de ensaio, não duração medida.\n\n'+content.records.map(r=>'## Slide '+(r.index+1)+' ('+timing[r.index]+' s)\n\n'+r.notes.text.trim()+'\n').join('\n');
await fs.writeFile(path.join(tmp,'ROTEIRO-APRESENTACAO.md'),guide,'utf8');
console.log(JSON.stringify({sha256:result.finalSha256,slides:after.slides.items.length,integrity:result.packageIntegrity.status,layout:result.presentationLayout.exitCode,import:result.firstPartyImport.passed}));
