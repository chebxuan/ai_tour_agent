"""Create a source release from a whitelist, excluding all local credentials and leads."""
from datetime import datetime, timezone
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ['backend', 'data/products', 'data/custom', 'frontend', 'deploy',
         '.dockerignore', 'docs/deployment-guide.md', 'readme.md',
         'scripts/normalize_product_library.py', 'scripts/maintain_database.py']
EXCLUDED = {'.git', '__pycache__', 'node_modules', '.next', '.DS_Store', 'coverage', 'out'}


def permitted(path):
    parts = path.relative_to(ROOT).parts
    return (not any(p in EXCLUDED or p.startswith('.env') and p != '.env.example' for p in parts)
            and path.suffix not in ('.pyc', '.log', '.dump'))


def main():
    destination = ROOT / '.local/deploy'
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / ('travel-release-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.tar.gz')
    files = []
    for item in ROOTS:
        source = ROOT / item
        candidates = source.rglob('*') if source.is_dir() else [source]
        files.extend(path for path in candidates if path.is_file() and not path.is_symlink() and permitted(path))
    with tarfile.open(output, 'w:gz') as archive:
        for path in sorted(set(files)):
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    output.chmod(0o600)
    with tarfile.open(output) as archive:
        names = archive.getnames()
        assert not any(name.startswith(('references/', '.local/', 'logs/')) or 'payments.json' in name for name in names)
        assert not any(any(p.startswith('.env') and p != '.env.example' for p in Path(name).parts) for name in names)
    print('Release:', output)
    print('Files:', len(names), 'Bytes:', output.stat().st_size)
    print('Contains source and catalogue seeds only; no local database, enquiries, payments or credentials.')


if __name__ == '__main__':
    main()
