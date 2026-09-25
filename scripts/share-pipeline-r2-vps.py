"""
Purpose: Provision only Pipeline R2 variables in Main's private VPS environment.
Run on the authorized VPS. Preserve a mode-0600 backup and never print secrets.
"""
from pathlib import Path
import os
import shutil
import tempfile
from datetime import datetime, timezone

source = Path('/home/hreidar/apps/ccm-workshop/shared/.env.production')
target = Path('/home/hreidar/apps/ccm-main/shared/.env')
keys = {'R2_PIPELINE_ENDPOINT', 'R2_PIPELINE_ACCESS_KEY_ID', 'R2_PIPELINE_SECRET_ACCESS_KEY', 'R2_PIPELINE_BUCKET_NAME'}
values = {line.split('=', 1)[0]: line for line in source.read_text().splitlines()
          if '=' in line and line.split('=', 1)[0] in keys}
if values.keys() != keys or any(not line.split('=', 1)[1].strip() for line in values.values()):
    raise RuntimeError('Pipeline R2 configuration is incomplete')
original = target.read_text()
lines = [line for line in original.splitlines() if line.split('=', 1)[0] not in keys and line != '# Crystal Workshop private R2 library']
insertion = 0
for index, line in enumerate(lines):
    if line.startswith(('R2_', 'CLOUDFLARE_')) and '=' in line:
        insertion = index + 1
lines[insertion:insertion] = ['', '# Crystal Workshop private R2 library'] + [values[key] for key in sorted(keys)] + ['']
updated = '\n'.join(lines).rstrip() + '\n'
if original != updated:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = target.with_name('.env.before-pipeline-r2-' + stamp)
    shutil.copy2(target, backup)
    os.chmod(backup, 0o600)
    descriptor, temporary = tempfile.mkstemp(prefix='.env-pipeline-r2-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
print('MAIN_VPS_PIPELINE_R2_CONFIGURED keys=4 mode=0600')
