"""Set the authorized Workshop canonical origin, preserving private environment backups."""
from pathlib import Path
from datetime import datetime, timezone
import os
import shutil
import sys
import tempfile

for argument in sys.argv[1:]:
    target = Path(argument).resolve(strict=True)
    original = target.read_text()
    lines = original.splitlines()
    found = False
    for index, line in enumerate(lines):
        if line.startswith(('AUTH_URL=', 'NEXTAUTH_URL=')):
            lines[index] = line.split('=', 1)[0] + '=https://workshop.acm.is'
            found = True
    if not found:
        lines.append('AUTH_URL=https://workshop.acm.is')
    updated = '\n'.join(lines) + '\n'
    if updated != original:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = target.with_name(target.name + '.before-workshop-' + stamp)
        shutil.copy2(target, backup)
        os.chmod(backup, 0o600)
        descriptor, temporary = tempfile.mkstemp(prefix='.workshop-env-', dir=target.parent)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    print('Workshop canonical origin configured; secret values omitted.')
