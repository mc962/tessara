import * as esbuild from 'esbuild';
import { writeFileSync, rmSync, mkdirSync } from 'fs';

const isWatch = process.argv.includes('--watch');
const outdir = 'static/js/dist';

rmSync(outdir, { recursive: true, force: true });
mkdirSync(outdir, { recursive: true });

const buildOptions = {
  entryPoints: [
    'static/js/src/app.js',
    'static/js/src/app.css',
  ],
  bundle: true,
  minify: !isWatch,
  outdir,
  // No hash in watch mode — predictable filenames so manifest stays valid across rebuilds
  entryNames: isWatch ? '[name]' : '[name]-[hash]',
  metafile: true,
  sourcemap: isWatch,
};

function writeManifest(metafile) {
  const manifest = {};
  for (const outFile of Object.keys(metafile.outputs)) {
    const filename = outFile.split('/').pop();
    if (filename.match(/^app(-[A-Z0-9]+)?\.js$/)) {
      manifest['app.js'] = '/static/js/dist/' + filename;
    } else if (filename.match(/^app(-[A-Z0-9]+)?\.css$/)) {
      manifest['app.css'] = '/static/js/dist/' + filename;
    }
  }
  writeFileSync(`${outdir}/manifest.json`, JSON.stringify(manifest, null, 2));
  return manifest;
}

if (isWatch) {
  const manifestPlugin = {
    name: 'manifest',
    setup(build) {
      build.onEnd(result => {
        if (result.metafile) {
          const manifest = writeManifest(result.metafile);
          console.log('Rebuilt:', manifest);
        }
      });
    },
  };
  const ctx = await esbuild.context({ ...buildOptions, plugins: [manifestPlugin] });
  await ctx.watch();
  console.log('Watching for changes…');
} else {
  const result = await esbuild.build(buildOptions);
  const manifest = writeManifest(result.metafile);
  console.log('Built:', manifest);
}