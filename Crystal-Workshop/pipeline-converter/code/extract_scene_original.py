"""
Purpose: Extract the exact named Cockpit texture without re-encoding its bytes.
Can prepare originals beside numbered local scenes before the Windows R2 backup.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


def extract_original(scene, directory, stem=None):
    with ZipFile(scene) as archive:
        info = archive.getinfo('CockpitScene.xml')
        if info.file_size > 4 * 1024 * 1024:
            raise ValueError('Scene XML too large.')
        root = ET.fromstring(archive.read(info))
        entities = [e for e in root.iter() if e.tag.split('}')[-1] == 'SolidEntity' and e.get('Texture')]
        if len(entities) != 1:
            raise ValueError('Exactly one textured SolidEntity is required.')
        member = entities[0].get('Texture')
        extension = Path(member).suffix.lower()
        if extension not in {'.jpg', '.jpeg', '.png'}:
            raise ValueError('Unsupported original photo format.')
        info = archive.getinfo(member)
        if info.file_size > 64 * 1024 * 1024:
            raise ValueError('Original photo too large.')
        data = archive.read(info)
    digest = hashlib.sha256(data).hexdigest()
    if stem is not None:
        import re
        if not re.fullmatch(r'\d+-[a-zA-Z0-9_-]+-v\d+', stem):
            raise ValueError('Invalid versioned photo stem.')
    name = (stem or 'original-' + digest[:16]) + extension
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    try:
        with target.open('xb') as output:
            output.write(data)
    except FileExistsError:
        if target.is_symlink() or target.read_bytes() != data:
            raise ValueError('Existing original differs from the scene texture.')
    return {'name': name, 'sha256': digest, 'textureMember': member, 'bytes': len(data)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    args = parser.parse_args()
    for folder in sorted(args.collection.iterdir()):
        if not folder.is_dir() or folder.is_symlink() or not folder.name.split('-')[0].isdigit():
            continue
        for scene in sorted(folder.glob('*.cockpit')):
            if scene.is_symlink():
                raise ValueError('Linked scene files are not supported.')
            print(json.dumps({'folder': folder.name, 'scene': scene.name, **extract_original(scene, folder)}))
