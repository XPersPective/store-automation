import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest


spec = importlib.util.spec_from_file_location('release', Path(__file__).parents[1] / 'tool/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_https_metadata_rejects_invalid_ports_and_loopback_spellings(self):
        for url in ('https://example.org:notaport/privacy', 'https://example.org:70000/privacy',
                    'https://0x7f.0.0.1/privacy', 'https://0x7f.1/privacy', 'https://127.1/privacy', 'https://0177.0.0.1/privacy',
                    'https://127.0.0.1./privacy', 'https://１２７.０.０.１/privacy',
                    'https://%31%32%37.0.0.1/privacy', 'https://example.org/white space'):
            with self.subTest(url=url):
                self.assertFalse(release._public_url(url))
        self.assertTrue(release._public_url('https://example.org:443/privacy'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'source'
        self.publishing = Path(self.temp.name) / 'publishing'
        self.app = self.publishing / 'apps/sample'
        self.write(self.publishing / 'README.md', 'Existing protocol')
        self.write(self.project / 'pubspec.yaml', 'version: 1.2.3+4\n')
        self.write(self.project / 'android/app/build.gradle.kts', 'applicationId = "org.example.sample"')
        self.write(self.project / 'ios/Runner.xcodeproj/project.pbxproj',
                   'PRODUCT_BUNDLE_IDENTIFIER = org.example.sample;\n'
                   'PRODUCT_BUNDLE_IDENTIFIER = org.example.sample.RunnerTests;')
        self.write(self.project / 'build/app/outputs/bundle/release/app-release.aab', 'fake artifact')
        self.write(self.project / 'build/ios/ipa/sample.ipa', 'fake artifact')
        for store, locale, texts in [('google-play', 'tr-TR',
                                     {'title': 'Sample', 'short_description': 'Summary', 'full_description': 'Details'}),
                                    ('app-store', 'tr', {'name': 'Sample', 'description': 'Details', 'keywords': 'list',
                                                        'support_url': 'https://example.org/support',
                                                        'privacy_url': 'https://example.org/privacy'})]:
            for name, value in texts.items():
                self.write(self.app / f'stores/{store}/metadata/{locale}/{name}.txt', value)
            image = (self.app / f'stores/{store}/metadata/{locale}/images/phoneScreenshots/01.png'
                     if store == 'google-play' else self.app / f'stores/{store}/screenshots/{locale}/01.png')
            # Deliberately header-only: proves preflight never claims decoder/visual acceptance.
            self.write(image, b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + struct.pack('>II', 1080, 1920))

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode())

    def check(self, platforms=('android', 'ios'), locales=('tr-TR',)):
        return release.preflight(self.project, self.publishing, 'sample', platforms, locales)

    def test_complete_local_inputs_still_require_external_gates(self):
        result = self.check()
        self.assertEqual(result['status'], 'PREPARATION_ONLY')
        self.assertFalse(result['store_write'])
        self.assertTrue(result['external_gates'])
        self.assertEqual(result['metadata']['android'][0]['store_locale'], 'tr-TR')
        self.assertEqual(result['metadata']['ios'][0]['store_locale'], 'tr')
        self.assertFalse(result['metadata']['ios'][0]['screenshots'][0]['platform_provenance_verified'])
        self.assertFalse(result['facts']['android_artifacts'][0]['signature_verified'])

    def test_missing_fields_and_oversized_text_block(self):
        (self.app / 'stores/google-play/metadata/tr-TR/title.txt').unlink()
        self.write(self.app / 'stores/app-store/metadata/tr/subtitle.txt', 'x' * 31)
        result = self.check()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(len(result['local_readiness']['issues']), 2)

    def test_private_url_and_invalid_image_block(self):
        self.write(self.app / 'stores/app-store/metadata/tr/privacy_url.txt', 'https://127.0.0.1/privacy')
        self.write(self.app / 'stores/app-store/screenshots/tr/01.png', b'not an image')
        result = self.check(('ios',))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(any('privacy_url' in issue for issue in result['local_readiness']['issues']))
        self.assertTrue(any('invalid screenshot' in issue for issue in result['local_readiness']['issues']))

    def test_credentials_are_never_opened_and_inputs_stay_unchanged(self):
        self.write(self.app / 'credentials/ios/private.p8', 'do not read')
        before = {str(p): p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        real_open = Path.open
        def guarded_open(path, *args, **kwargs):
            self.assertNotIn('credentials', path.parts)
            return real_open(path, *args, **kwargs)
        from unittest.mock import patch
        with patch.object(Path, 'open', guarded_open):
            self.check()
        after = {str(p): p.read_bytes() for p in Path(self.temp.name).rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_traversal_and_unselected_platform_are_refused(self):
        for slug in ('../sample', 'C:/sample', 'a/b'):
            with self.assertRaises(ValueError):
                release.preflight(self.project, self.publishing, slug, ['android'], ['tr-TR'])
        with self.assertRaises(ValueError):
            self.check(('android', 'unknown'))
        with self.assertRaises(ValueError):
            self.check(locales=('../tr',))

    def test_linked_metadata_is_refused(self):
        path = self.app / 'stores/google-play/metadata/tr-TR/title.txt'
        path.unlink()
        try:
            path.symlink_to(self.project / 'pubspec.yaml')
        except OSError:
            self.skipTest('OS does not permit symlink creation for this account')
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_artifact_and_ambiguous_identity_block(self):
        (self.project / 'build/ios/ipa/sample.ipa').unlink()
        self.write(self.project / 'ios/Runner.xcodeproj/project.pbxproj',
                   'PRODUCT_BUNDLE_IDENTIFIER = org.example.one;\nPRODUCT_BUNDLE_IDENTIFIER = org.example.two;')
        result = self.check(('ios',))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIsNone(result['facts']['ios_source_identity'])

    def test_jpeg_dimensions_and_truncated_header(self):
        image = self.app / 'stores/app-store/screenshots/tr/02.jpg'
        self.write(image, b'\xff\xd8\xff\xe0\x00\x04ab\xff\xc0\x00\x07\x08' + struct.pack('>HH', 1280, 720))
        self.assertEqual(release._image(image), (720, 1280))
        self.write(image, b'\xff\xd8\xff\xc0\x00')
        with self.assertRaises(ValueError):
            release._image(image)

    def test_turkish_aliases_cannot_duplicate_store_inputs(self):
        with self.assertRaises(ValueError):
            self.check(locales=('tr', 'tr-TR'))


if __name__ == '__main__':
    unittest.main()
