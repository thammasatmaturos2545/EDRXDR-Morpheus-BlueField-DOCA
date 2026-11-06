"""Interactive private registry staging only, never provision the live review root."""
from pathlib import Path
import getpass, hashlib, json, os, re, secrets, sys, tempfile
import decision_review as review

def entry(login, role, password, salt):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', login):
        raise ValueError('Login must be 1-48 ASCII letters/digits/_/-')
    if role not in ('viewer', 'reviewer') or not 16 <= len(password) <= 128:
        raise ValueError('Role/password length invalid')
    if len(password.encode()) > 256:
        raise ValueError('Password byte limit')
    return {'login': login, 'actor_ref': 'reviewer:' + login, 'role': role,
            'salt': salt.hex(), 'scrypt_sha256': hashlib.scrypt(
                password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64).hex()}

def main():
    if sys.argv[1:] != ['--stage-private-reviewers'] or not sys.stdin.isatty():
        raise ValueError('Explicit interactive staging required')
    os.umask(0o077)
    count = int(input('Number of named people (1-32): '))
    if not 1 <= count <= 32:
        raise ValueError('Invalid count')
    users, seen = [], set()
    for number in range(count):
        login = input(f'Private login label for person {number+1}: ').strip()
        role = input('Role (viewer/reviewer): ').strip()
        if login in seen:
            raise ValueError('Duplicate person/login')
        password = getpass.getpass('Password (16-128 characters, hidden): ')
        confirm = getpass.getpass('Repeat password: ')
        if password != confirm:
            raise ValueError('Password mismatch')
        users.append(entry(login, role, password, secrets.token_bytes(16)))
        seen.add(login)
        password = confirm = None
    if not any(user['role'] == 'reviewer' for user in users):
        raise ValueError('At least one named reviewer required for the write workflow')
    root = Path(tempfile.mkdtemp(
        prefix='human-review-users-staged-', dir='/mnt/nexus-copilot-mQTssj'))
    path = root / 'reviewers.json'
    with path.open('x') as stream:
        json.dump({'schema_version': 'nexus-reviewers-v1', 'users': users}, stream)
    print('PRIVATE_REVIEWER_STAGING', root)
    print('USER_COUNT', len(users))
    print('NOT_PROVISIONED; no live catalog/DB/environment/runtime changed')
    print('Keep registry/passwords private; do not paste or commit registry contents')

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('STOP reviewer staging failed; no live provisioning; details withheld')
        raise SystemExit(1)
