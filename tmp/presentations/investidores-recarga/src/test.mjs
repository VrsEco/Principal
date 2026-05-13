/** @jsxRuntime automatic */
/** @jsxImportSource @oai/artifact-tool/presentation-jsx */
import { Presentation, PresentationFile, column, text, fill, hug, drawSlideToCtx } from '@oai/artifact-tool';
import { Canvas } from 'file:///C:/Users/mff20/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/node_modules/skia-canvas/lib/index.mjs';

const presentation = Presentation.create({ slideSize: { width: 1920, height: 1080 } });
const slide = presentation.slides.add();
slide.compose(column({ width: fill, height: fill, padding: 80, gap: 20 }, [
  text('Teste', { width: fill, height: hug, style: { fontSize: 64, bold: true, color: '#111827' } }),
  text('Subtitulo', { width: fill, height: hug, style: { fontSize: 28, color: '#4B5563' } }),
]), { frame: { left: 0, top: 0, width: 1920, height: 1080 }, baseUnit: 8 });
const blob = await PresentationFile.exportPptx(presentation);
await blob.save('C:/GestaoVersus/app32/tmp/presentations/investidores-recarga/output/teste.pptx');
const canvas = new Canvas(1920, 1080);
const ctx = canvas.getContext('2d');
await drawSlideToCtx(slide, presentation, ctx);
await canvas.saveAs('C:/GestaoVersus/app32/tmp/presentations/investidores-recarga/scratch/teste.png');
console.log('ok');
