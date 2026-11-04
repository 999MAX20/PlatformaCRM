"""Verify and restore missing audit evidence only; never overwrite existing files."""
import argparse, hashlib, json, zipfile
from pathlib import Path, PurePosixPath
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--restore-missing',action='store_true');args=parser.parse_args()
manifest=json.loads((OUT/'package-manifest.json').read_text(encoding='utf-8'))
archive=OUT/manifest['archive']['filename']
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(archive.read_bytes())==manifest['archive']['sha256'],'Archive hash mismatch'
rows={r['path']:r for r in manifest['included'] if r['storage']=='archive'}
restored=0
with zipfile.ZipFile(archive) as z:
 assert set(z.namelist())==set(rows),'Unexpected archive entries'
 for name,r in rows.items():
  rel=PurePosixPath(name)
  assert not rel.is_absolute() and '..' not in rel.parts
  target=(ROOT/name).resolve();assert target.is_relative_to(OUT.resolve())
  content=z.read(name);assert len(content)==r['size'] and sha(content)==r['sha256']
  if target.exists():
   assert target.is_file() and sha(target.read_bytes())==r['sha256'],f'Existing file differs: {name}'
  elif args.restore_missing:
   target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:f.write(content)
   restored+=1
print(json.dumps({'archive_entries_verified':len(rows),'restored_missing':restored,'overwrite_existing':False,'boundary':'Only packaged audit artifacts restored; omitted local-only evidence remains unavailable in a fresh checkout.'}))
