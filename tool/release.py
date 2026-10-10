"""Read-only local checks for the existing AppPublishing/Fastlane layout."""
import hashlib
import ipaddress
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit


def _path(root, relative):
    """Reject links before opening anything, including missing descendants."""
    root = Path(root).absolute()
    candidate = root / relative
    if '..' in Path(relative).parts or Path(relative).is_absolute():
        raise ValueError('Publishing path escapes its root')
    for part in (candidate, *candidate.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('Linked publishing/source paths are refused')
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('Publishing path escapes its root')
    return candidate


def _text(root, relative):
    path = _path(root, relative)
    if not path.is_file():
        return None
    if path.stat().st_size > 100_000:
        raise ValueError('Public metadata exceeds the read limit')
    return path.read_text(encoding='utf-8-sig')


def _public_url(value):
    try:
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
            return False
        url = urlsplit(value)
        host = url.hostname
        if url.scheme != 'https' or not host or url.username or url.password:
            return False
        if url.port is not None and url.port < 1:
            return False
        host = host.encode('idna').decode('ascii').lower().rstrip('.')
        if '%' in host or host == 'localhost' or '.' not in host or host.endswith('.local'):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return not bool(re.fullmatch(r'(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*', host))
    except (ValueError, UnicodeError):
        return False


def _image(path):
    """Header inspection only; not device provenance or visual acceptance."""
    with path.open('rb') as stream:
        header = stream.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR':
            return struct.unpack('>II', header[16:24])
        if header[:2] != b'\xff\xd8':
            raise ValueError('Expected PNG/JPEG signature')
        stream.seek(2)
        # ponytail: inspect at most 1 MiB of JPEG headers; use an image decoder for visual QA.
        while stream.tell() < 1_048_576:
            if stream.read(1) != b'\xff':
                raise ValueError('Malformed JPEG header')
            marker = stream.read(1)
            while marker == b'\xff':
                marker = stream.read(1)
            if marker in (b'\xd9', b'\xda', b''):
                break
            if marker == b'\x00' or marker == b'\xd8' or b'\xd0' <= marker <= b'\xd7':
                continue
            raw = stream.read(2)
            if len(raw) != 2:
                break
            length = struct.unpack('>H', raw)[0]
            if length < 2:
                break
            if marker in [bytes([m]) for m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)]:
                size = stream.read(5)
                if len(size) == 5:
                    height, width = struct.unpack('>HH', size[1:])
                    return width, height
                break
            stream.seek(length - 2, 1)
    raise ValueError('Missing supported image size header')


def preflight(project_root, publishing_root, app_id, platforms, locales):
    """No credentials, remote calls, generated catalogue or store writes."""
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', app_id):
        raise ValueError('app_id must be a canonical lowercase slug')
    if not platforms or len(set(platforms)) != len(platforms) or set(platforms) - {'android', 'ios'}:
        raise ValueError('Select android and/or ios explicitly')
    if not locales or len(set(locales)) != len(locales) or any(
            not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', item) for item in locales):
        raise ValueError('Select distinct locale codes explicitly')
    if 'tr' in locales and 'tr-TR' in locales:
        raise ValueError('Select Turkish once: tr and tr-TR map to the same store locale')
    project, publishing = Path(project_root).absolute(), Path(publishing_root).absolute()
    app = _path(publishing, 'apps/' + app_id)
    issues, facts, checks = [], {}, {}
    protocol = _path(publishing, 'README.md')
    if not protocol.is_file():
        issues.append('Canonical publishing README.md is missing')
    pubspec = _text(project, 'pubspec.yaml')
    version = re.search(r'^version:\s*([^\s#]+)', pubspec or '', re.M)
    facts['source_version'] = version.group(1) if version else None
    if not version:
        issues.append('Source pubspec version is missing')
    for platform in platforms:
        if platform == 'android':
            gradle = _text(project, 'android/app/build.gradle.kts')
            if gradle is None:
                gradle = _text(project, 'android/app/build.gradle')
            match = re.search(r'\bapplicationId\s*(?:=\s*)?[\"\']([^\"\']+)[\"\']', gradle or '')
            identity = match.group(1) if match else None
            store = 'google-play'
            required = {'title': 30, 'short_description': 80, 'full_description': 4000}
            optional = {}
            artifact_name = 'build/app/outputs/bundle/release/app-release.aab'
        else:
            xcode = _text(project, 'ios/Runner.xcodeproj/project.pbxproj')
            identities = set(re.findall(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*[\"\']?([\w.]+)', xcode or ''))
            identities = {item for item in identities if not item.endswith('.RunnerTests')}
            identity = next(iter(identities)) if len(identities) == 1 else None
            store = 'app-store'
            required = {'name': 30, 'description': 4000, 'keywords': 100,
                        'support_url': None, 'privacy_url': None}
            optional = {'subtitle': 30, 'promotional_text': 170, 'release_notes': 4000,
                        'marketing_url': None}
            artifact_name = 'build/ios/ipa'
        facts[platform + '_source_identity'] = identity
        if not identity or identity.startswith('com.example.'):
            issues.append(platform + ': explicit non-placeholder source identity is missing/ambiguous')
        artifact = _path(project, artifact_name)
        candidates = [artifact] if platform == 'android' and artifact.is_file() else (
            sorted(artifact.glob('*.ipa')) if platform == 'ios' and artifact.is_dir() else [])
        facts[platform + '_artifacts'] = []
        for candidate in candidates:
            candidate = _path(project, candidate.relative_to(project))
            if candidate.is_file():
                with candidate.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                facts[platform + '_artifacts'].append({'path': str(candidate), 'bytes': candidate.stat().st_size,
                                                       'sha256': digest, 'signature_verified': False})
        if not facts[platform + '_artifacts']:
            issues.append(platform + ': release artifact is missing')
        checks[platform] = []
        for locale in locales:
            # AppPublishing explicitly uses Android tr-TR and iOS tr.
            selected = ('tr-TR' if platform == 'android' else 'tr') if locale in ('tr', 'tr-TR') else locale
            base = f'stores/{store}/metadata/{selected}'
            entry = {'requested_locale': locale, 'store_locale': selected, 'texts': {}, 'screenshots': []}
            for name, limit in {**required, **optional}.items():
                value = _text(app, f'{base}/{name}.txt')
                if value is None and name in optional:
                    continue
                value = (value or '').strip()
                valid = bool(value) and (limit is None or len(value) <= limit)
                if name.endswith('_url'):
                    valid = valid and _public_url(value)
                entry['texts'][name] = {'valid': bool(valid), 'characters': len(value), 'limit': limit}
                if not valid:
                    issues.append(f'{platform}/{selected}: {name}.txt missing/invalid')
            screenshot_dir = _path(app, f'{base}/images/phoneScreenshots' if platform == 'android'
                                   else f'stores/app-store/screenshots/{selected}')
            if screenshot_dir.is_dir():
                for image in sorted(screenshot_dir.iterdir()):
                    image = _path(app, image.relative_to(app))
                    if image.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
                        continue
                    try:
                        width, height = _image(image)
                        if min(width, height) <= 0:
                            raise ValueError('Zero image dimension')
                        entry['screenshots'].append({'name': image.name, 'width': width, 'height': height,
                                                     'platform_provenance_verified': False})
                    except (OSError, ValueError, struct.error):
                        issues.append(f'{platform}/{selected}: invalid screenshot {image.name}')
            if not entry['screenshots']:
                issues.append(f'{platform}/{selected}: screenshots missing')
            checks[platform].append(entry)
    return {'status': 'BLOCKED' if issues else 'PREPARATION_ONLY', 'store_write': False,
            'local_readiness': {'passed': not issues, 'issues': issues},
            'protocol': str(protocol), 'app_id': app_id, 'facts': facts, 'metadata': checks,
            'external_gates': ['Selected store account/app and actual remote version',
                               'Artifact identity/signature and real-device runtime',
                               'Store locale support, current image requirements and visual/device provenance',
                               'Privacy/data safety/age/content declarations and legal text approval',
                               'Scoped account authorization and exact release target',
                               'iOS requires macOS/Xcode and App Store processing' if 'ios' in platforms else
                               'Google Play first-upload/account/testing prerequisites'],
            'credential_access': 'none'}
