from pathlib import Path
import base64
import hashlib

parts = sorted(Path('.').glob('part-*-of-*.b64'))
if len(parts) != 8:
    raise SystemExit(f'expected 8 parts, found {len(parts)}')

payload = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
data = base64.b64decode(payload, validate=True)
out = Path('task025-r7-review-package.tar.gz')
out.write_bytes(data)
sha = hashlib.sha256(data).hexdigest()
print(f'created={out}')
print(f'byte_size={len(data)}')
print(f'sha256={sha}')
expected = '43eb0490e5cfdc9296496a9aa8f539a39d4ae017d9c2bc2ead4507f03eaaa49c'
if sha != expected or len(data) != 94641:
    raise SystemExit('identity mismatch')
print('identity_match=YES')
