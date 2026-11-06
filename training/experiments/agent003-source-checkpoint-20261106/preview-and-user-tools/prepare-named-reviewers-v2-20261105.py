"""Private interactive reviewer staging. No runtime, DB, catalog or source changes."""
from pathlib import Path
import argparse, getpass, hashlib, json, os, re, secrets, sys, tempfile

def password_issue(password, confirm):
    if password != confirm:
        return 'PASSWORD_MISMATCH'
    if len(password) < 16:
        return 'PASSWORD_TOO_SHORT_MINIMUM_16_CHARACTERS'
    if len(password) > 128 or len(password.encode('utf-8')) > 256:
        return 'PASSWORD_TOO_LONG'
    return None

def make_user(login, role, password):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', login):
        raise ValueError('LOGIN_FORMAT_INVALID')
    if role not in ('viewer', 'reviewer'):
        raise ValueError('ROLE_INVALID')
    if password_issue(password, password):
        raise ValueError(password_issue(password, password))
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=64)
    return {'login': login, 'actor_ref': 'reviewer:' + login, 'role': role,
            'salt': salt.hex(), 'scrypt_sha256': digest.hex()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage-private-reviewers', action='store_true')
    args = parser.parse_args()
    if not args.stage_private_reviewers or not sys.stdin.isatty():
        raise ValueError('INTERACTIVE_STAGING_REQUIRED')
    if os.geteuid() == 0:
        raise ValueError('RUN_AS_SAIUSER_WITHOUT_SUDO')
    os.umask(0o077)
    phase = 'inputs'
    root = None
    try:
        while True:
            count = input('Number of named people (1-32): ').strip()
            if count.isdigit() and 1 <= int(count) <= 32:
                count = int(count)
                break
            print('COUNT_INVALID; enter a number from1 to32')
        users, seen = [], set()
        for number in range(count):
            while True:
                login = input(f'Private login label for person {number+1}: ').strip()
                if re.fullmatch(r'[A-Za-z0-9_-]{1,48}', login) and login not in seen:
                    break
                print('LOGIN_INVALID_OR_DUPLICATE; letters/digits/_/- only')
            while True:
                role = input('Role (viewer/reviewer): ').strip()
                if role in ('viewer', 'reviewer'):
                    break
                print('ROLE_INVALID; type viewer or reviewer')
            for attempt in range(3):
                password = getpass.getpass('New password (16-128 characters, hidden): ')
                confirm = getpass.getpass('Repeat password (hidden): ')
                issue = password_issue(password, confirm)
                if issue is None:
                    break
                password = confirm = None
                print(issue + '; re-enter both passwords')
            else:
                raise ValueError('PASSWORD_VALIDATION_FAILED_AFTER_3_TRIES')
            phase = 'password_digest'
            users.append(make_user(login, role, password))
            password = confirm = None
            seen.add(login)
            phase = 'inputs'
        if not any(user['role'] == 'reviewer' for user in users):
            raise ValueError('AT_LEAST_ONE_REVIEWER_REQUIRED')
        phase = 'private_directory'
        root = Path(tempfile.mkdtemp(
            prefix='human-review-users-staged-', dir='/mnt/nexus-copilot-mQTssj'))
        root.chmod(0o700)
        phase = 'private_registry_write'
        temporary = root / 'reviewers.json.pending'
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump({'schema_version': 'nexus-reviewers-v1', 'users': users}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        temporary.rename(root / 'reviewers.json')
        info = (root / 'reviewers.json').stat()
        if info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o777 != 0o600:
            raise ValueError('PRIVATE_REGISTRY_PERMISSION_CHECK_FAILED')
        print('PRIVATE_REVIEWER_STAGING', root)
        print('USER_COUNT', len(users))
        print('NOT_PROVISIONED; no live users/catalog/DB/runtime changes')
        print('Do not paste or commit registry contents or passwords')
    except (EOFError, KeyboardInterrupt):
        print('STAGING_CANCELLED; no live provisioning')
        raise SystemExit(1)
    except Exception as error:
        safe = {
            'LOGIN_FORMAT_INVALID', 'ROLE_INVALID',
            'PASSWORD_VALIDATION_FAILED_AFTER_3_TRIES',
            'AT_LEAST_ONE_REVIEWER_REQUIRED',
            'PRIVATE_REGISTRY_PERMISSION_CHECK_FAILED'}
        code = str(error) if isinstance(error, ValueError) and str(error) in safe else type(error).__name__
        print('STAGING_STOP_PHASE', phase, 'SAFE_REASON', code)
        if root is not None:
            print('PRIVATE_INCOMPLETE_DIRECTORY', root)
        print('No live provisioning; preserve private files; do not paste credentials')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
