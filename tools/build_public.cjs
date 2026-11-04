// Publish only files in the verified release manifest, never the source tree.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const root = path.resolve(__dirname,'..');
const manifest = JSON.parse(fs.readFileSync(path.join(root,'build-manifest.json'),'utf8'));
if (manifest.preview !== false) throw new Error('A review preview cannot be published');
const output = path.join(root,'dist');
fs.mkdirSync(output,{recursive:true});
for (const [file,hash] of Object.entries(manifest.files)) {
  if (file === 'vercel.json') continue;
  if (file.includes('..') || /(^\.|Defense|private|draft|approval|tools\/|\.bak|pre-redesign)/i.test(file)) throw new Error('Excluded file: '+file);
  const input = path.join(root,file);
  const data = fs.readFileSync(input);
  if (crypto.createHash('sha256').update(data).digest('hex') !== hash) throw new Error('Release file changed after verification: '+file);
  const target = path.join(output,file);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,data);
}
fs.copyFileSync(path.join(root,'build-manifest.json'),path.join(output,'build-manifest.json'));
console.log('Verified public output: '+Object.keys(manifest.files).length+' manifest files; private drafts excluded.');
