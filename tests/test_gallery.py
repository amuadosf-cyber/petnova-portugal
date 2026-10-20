from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from petnova.content import NOTICE, load_config, load_products, plan_day, write_json
from scripts.preparar_galeria import export_gallery
from scripts.publicar_galeria import publish


class TestGallery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contents = self.root / 'conteudos'
        self.output = self.root / 'galeria'
        self.folder = self.contents / '2026-10-20'
        self.path = self.folder / 'manifest.json'
        self.manifest = plan_day(load_config(), load_products(), '2026-10-20')
        self.manifest['private_configuration'] = 'never-export-this-private-value'
        for post in self.manifest['posts']:
            post['generation']['private_token'] = 'never-export-this-private-value'
            target = self.folder / post['id']
            target.mkdir(parents=True)
            for key, name in [('video','video.mp4'),('ad','anuncio.png'),('subtitles','legendas.srt')]:
                (target / name).write_text('00:00:00,000 --> 00:00:06,000\nCães, gatos e amigos.\n', encoding='utf-8')
        (self.folder / '.env').write_text('PRIVATE_TOKEN=never-export-this-private-value')
        write_json(self.path, self.manifest)

    def test_public_export_contains_only_curated_files(self):
        data = export_gallery(self.contents, self.output, '12345', '1')
        self.assertEqual(len(data['posts']), 2)
        self.assertFalse(data['social_publishing_enabled'])
        self.assertNotIn('never-export-this-private-value', json.dumps(data))
        for post in data['posts']:
            self.assertEqual(post['status'], 'rascunho')
            self.assertNotIn('review', post)
            self.assertTrue(post['media']['video'].startswith('https://github.com/amuadosf-cyber/petnova-portugal/releases/download/'))
        with zipfile.ZipFile(self.output / 'petnova-2026-10-20.zip') as archive:
            self.assertNotIn('.env', archive.namelist())
            self.assertNotIn('manifest.json', archive.namelist())
            self.assertEqual(len(archive.namelist()), 14)

    def test_vtt_conversion_preserves_caption_punctuation(self):
        data = export_gallery(self.contents, self.output)
        text = (self.output / (data['posts'][0]['id']+'.vtt')).read_text()
        self.assertTrue(text.startswith('WEBVTT'))
        self.assertIn('00:00:00.000 --> 00:00:06.000', text)
        self.assertIn('Cães, gatos e amigos.', text)

    def test_missing_demo_disclosure_blocks_export(self):
        self.manifest['posts'][0]['captions']['instagram'] = 'Comprar agora'
        write_json(self.path, self.manifest)
        with self.assertRaises(ValueError):
            export_gallery(self.contents, self.output)

    def test_path_traversal_cannot_read_outside_batch(self):
        self.manifest['posts'][0]['media']['video'] = '../../private.txt'
        write_json(self.path, self.manifest)
        with self.assertRaises(ValueError):
            export_gallery(self.contents, self.output)

    def test_publication_is_limited_to_project_workflow(self):
        with patch.dict('os.environ', {}, clear=True), patch('scripts.publicar_galeria.gh') as remote:
            with self.assertRaises(ValueError):
                publish(self.output)
            remote.assert_not_called()


if __name__ == '__main__':
    unittest.main()
