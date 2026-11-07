"""Download a resumable Finland PBF and verify Geofabrik's MD5 checksum."""
import hashlib
import json
from pathlib import Path

import osmium
import requests

root = Path('data/raw')
root.mkdir(parents=True, exist_ok=True)
target = root / 'finland.osm.pbf'
part = target.with_suffix(target.suffix + '.part')
url = 'https://download.geofabrik.de/europe/finland-latest.osm.pbf'
expected_response = requests.get(url + '.md5', timeout=60)
expected_response.raise_for_status()
expected = expected_response.text.split()[0]
if not target.exists():
    offset = part.stat().st_size if part.exists() else 0
    response = requests.get(url, stream=True, headers={'Range': f'bytes={offset}-'} if offset else {}, timeout=(30,120))
    response.raise_for_status()
    append = offset > 0 and response.status_code == 206
    downloaded = offset if append else 0
    reported = downloaded // (50 * 1024 * 1024)
    with part.open('ab' if append else 'wb') as output:
        for chunk in response.iter_content(1024 * 1024):
            output.write(chunk)
            downloaded += len(chunk)
            if downloaded // (50 * 1024 * 1024) > reported:
                reported = downloaded // (50 * 1024 * 1024)
                print(f'{downloaded / 1024**2:.0f} MiB ladattu', flush=True)
    with part.open('rb') as source:
        actual = hashlib.file_digest(source, 'md5').hexdigest()
    if actual != expected:
        raise ValueError('Geofabrik MD5 mismatch; source may have changed during download. Keep .part for diagnosis.')
    part.replace(target)
else:
    with target.open('rb') as source:
        actual = hashlib.file_digest(source, 'md5').hexdigest()
    if actual != expected:
        raise ValueError('Existing PBF differs from latest; preserve it and use its own metadata, or move it before downloading a new snapshot.')
with osmium.io.Reader(str(target)) as reader:
    header = reader.header()
    timestamp = header.get('osmosis_replication_timestamp')
    generator = header.get('generator')
metadata = dict(url=url, md5=actual, osm_date=timestamp, generator=generator, bytes=target.stat().st_size)
(root/'finland-source.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps(metadata, indent=2), flush=True)
