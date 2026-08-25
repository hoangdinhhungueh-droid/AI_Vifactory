import os, sys, glob, base64, hashlib
from PIL import Image

work_dir = sys.argv[1]
target_name = sys.argv[2]
expected_md5 = sys.argv[3]

txt_files = sorted(glob.glob(f'{work_dir}/part_*.txt'), key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
b64_full = ''
for f in txt_files:
    with open(f, 'r') as fh:
        b64_full += fh.read()
    os.remove(f)

raw = base64.b64decode(b64_full)
dest = f'/var/vf/episodes/en-byzantine-empire-ep001/assets/raw/{target_name}'
with open(dest, 'wb') as fh:
    fh.write(raw)

v_md5 = hashlib.md5(raw).hexdigest()
im = Image.open(dest)
is_match = (v_md5 == expected_md5)
print(f'ASSEMBLED {target_name}: {len(raw)} bytes | MD5: {v_md5} | PIL: {im.size} {im.format} | ' + ('MATCH ✅' if is_match else 'MISMATCH ❌'))
