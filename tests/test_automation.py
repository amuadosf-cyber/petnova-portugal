from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from petnova.content import (NOTICE, ROOT, assisted_hook, fingerprint, load_config, load_products,
                             make_post, media_path, plan_day, read_json, write_json)
from petnova.publish import Ledger, PublishError, process_post, publish_instagram, publish_youtube, readiness
from petnova.render import srt_time, write_subtitles

NOW = datetime(2026, 10, 22, 23, tzinfo=timezone.utc)
ENV = {'YOUTUBE_CLIENT_ID': 'client', 'YOUTUBE_CLIENT_SECRET': 'secret', 'YOUTUBE_REFRESH_TOKEN': 'refresh',
       'IG_USER_ID': '12345', 'IG_ACCESS_TOKEN': 'test-private-token'}


class TestContent(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.products = load_products()

    def test_store_is_locked_in_demo(self):
        self.assertEqual(self.config['store']['mode'], 'demonstracao')
        self.assertIs(self.config['store']['checkout_enabled'], False)
        with tempfile.TemporaryDirectory() as folder:
            self.config['store']['checkout_enabled'] = True
            path = Path(folder) / 'bad.json'
            write_json(path, self.config)
            with self.assertRaises(ValueError):
                load_config(path)

    def test_every_catalog_product_is_demonstrative(self):
        self.assertEqual(len(self.products), 5)
        self.assertTrue(all(p['estado'] == 'demonstracao' for p in self.products))
        self.assertEqual(read_json(ROOT / 'catalogo.json')['products'], self.products)

    def test_two_daily_posts_and_every_caption_discloses_demo(self):
        plan = plan_day(self.config, self.products, '2026-10-20')
        self.assertEqual(len(plan['posts']), 2)
        self.assertEqual(plan, plan_day(self.config, self.products, '2026-10-20'))
        for post in plan['posts']:
            self.assertFalse(post['review']['approved'])
            for platform, caption in post['captions'].items():
                self.assertIn(NOTICE, caption)
                self.assertIn(f'utm_source={platform}', caption)
                self.assertNotIn('Compra agora', caption)

    def test_lisbon_winter_and_summer(self):
        summer = plan_day(self.config, self.products, '2026-07-01')['posts'][0]['scheduled_at']
        winter = plan_day(self.config, self.products, '2026-12-01')['posts'][0]['scheduled_at']
        self.assertTrue(summer.endswith('+01:00'))
        self.assertTrue(winter.endswith('+00:00'))

    def test_product_rotation(self):
        plans = [plan_day(self.config, self.products, f'2026-10-{d}') for d in (20, 21, 22)]
        self.assertEqual({p['product_id'] for plan in plans for p in plan['posts']}, {p['id'] for p in self.products})

    def test_valid_local_ai_response(self):
        self.config['content'].update(ollama_model='installed-test-model')
        response = json.dumps({'message': {'content': json.dumps({'hook': 'Mais tempo para os nossos amigos'})}}).encode()
        captured = []
        def opener(request, timeout):
            captured.append((request, timeout))
            return io.BytesIO(response)
        self.assertEqual(assisted_hook(self.products[0], self.config, opener), 'Mais tempo para os nossos amigos')
        self.assertFalse(json.loads(captured[0][0].data)['stream'])

    def test_ai_cannot_select_external_paid_service(self):
        self.config['content'].update(ollama_model='test', ollama_url='https://external.example')
        with self.assertRaises(ValueError):
            assisted_hook(self.products[0], self.config)

    def test_ai_claims_are_rejected(self):
        self.config['content']['ollama_model'] = 'test'
        for hook in ('Entrega grátis garantida', 'Compra agora com 50% de desconto', '<script>alert</script>', 'Cura todos os problemas'):
            data = json.dumps({'message': {'content': json.dumps({'hook': hook})}}).encode()
            with self.subTest(hook=hook), self.assertRaises(ValueError):
                assisted_hook(self.products[0], self.config, lambda *a, **k: io.BytesIO(data))

    def test_ai_unavailable_falls_back_honestly(self):
        self.config['content']['provider'] = 'ollama'
        with patch('petnova.content.assisted_hook', side_effect=OSError('offline')):
            post = make_post(self.products[0], self.config, '2026-10-20', 0)
        self.assertFalse(post['generation']['ai_used'])
        self.assertEqual(post['generation']['provider'], 'templates')
        self.assertIn('fallback', post['generation'])

    def test_media_cannot_escape_content_directory(self):
        with self.assertRaises(ValueError):
            media_path(ROOT / 'conteudos/test/manifest.json', '../../outside.mp4')

    def test_srt_has_four_timed_scenes(self):
        post = make_post(self.products[0], self.config, '2026-10-20', 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'legendas.srt'
            write_subtitles(post, path, 24)
            self.assertIn('00:00:18,000 --> 00:00:24,000', path.read_text())
            self.assertEqual(path.read_text().count('-->'), 4)
        self.assertEqual(srt_time(60.125), '00:01:00,125')

    def test_repeat_generation_preserves_review_and_edits(self):
        from automacao_conteudos import generate
        with tempfile.TemporaryDirectory() as folder:
            path, manifest = generate(self.config, '2026-10-20', folder, videos=False)
            manifest['posts'][0]['captions']['youtube'] += '\nAlteração manual.'
            write_json(path, manifest)
            _, second = generate(self.config, '2026-10-20', folder, videos=False)
            self.assertEqual(second, manifest)


class TestPublishing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.path = self.folder / 'manifest.json'
        self.config = load_config()
        self.post = plan_day(self.config, load_products(), '2026-10-20')['posts'][0]
        self.config['publishing'].update(enabled=True, instagram_api_version='v24.0')
        self.post['media']['public_video_url'] = 'https://media.example.test/video.mp4'
        for key in ('ad', 'video'):
            path = media_path(self.path, self.post['media'][key])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fake media for mocked API boundary')
        self.post['review'] = {'approved': True, 'fingerprint': fingerprint(self.post, self.path)}
        self.ledger = Ledger(self.folder / 'state.sqlite3')
        self.addCleanup(self.ledger.close)
        self.addCleanup(self.temp.cleanup)

    def process(self, platform='youtube', **kwargs):
        return process_post(self.post, self.path, self.config, platform, ledger=self.ledger, now=NOW, environ=ENV, **kwargs)

    def test_simulation_never_calls_platform_or_claims_ledger(self):
        def unexpected(*a, **k):
            self.fail('A simulação não pode fazer chamadas de rede.')
        report = self.process(transport=unexpected)
        self.assertEqual(report['status'], 'simulation')
        self.assertFalse(report['sent'])
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM publications').fetchone()[0], 0)

    def test_disabled_config_blocks_even_explicit_live_flag(self):
        self.config['publishing']['enabled'] = False
        self.assertEqual(self.process(live=True)['status'], 'blocked')

    def test_no_review_blocks(self):
        self.post['review']['approved'] = False
        self.assertEqual(self.process(live=True)['status'], 'blocked')

    def test_changed_caption_invalidates_review(self):
        self.post['captions']['youtube'] += '\nEditado'
        self.assertIn('Conteúdo alterado desde a revisão.', self.process(live=True)['blockers'])

    def test_changed_media_invalidates_review(self):
        media_path(self.path, self.post['media']['video']).write_bytes(b'changed')
        self.assertIn('Conteúdo alterado desde a revisão.', self.process(live=True)['blockers'])

    def test_future_schedule_is_blocked(self):
        reasons = readiness(self.post, self.path, self.config, 'youtube', now=datetime(2026, 1, 1, tzinfo=timezone.utc), environ=ENV)
        self.assertIn('Horário de publicação ainda não atingido.', reasons)

    def test_missing_credentials_are_reported_without_values(self):
        reasons = readiness(self.post, self.path, self.config, 'youtube', now=NOW, environ={})
        self.assertIn('YOUTUBE_REFRESH_TOKEN', ' '.join(reasons))
        self.assertNotIn('test-private-token', ' '.join(reasons))

    def test_tiktok_is_export_only(self):
        report = self.process('tiktok', live=True)
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['sent'])

    def test_one_youtube_upload_even_if_called_twice(self):
        calls = []
        def transport(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if 'oauth2' in url:
                return {'access_token': 'temporary-private-token'}, {}
            if method == 'POST':
                return {}, {'Location': 'https://www.googleapis.com/upload/test-session'}
            return {'id': 'video_123'}, {}
        self.assertEqual(self.process(live=True, transport=transport)['status'], 'confirmed')
        self.assertEqual(self.process(live=True, transport=transport)['status'], 'already_recorded')
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][2]['json_body']['status']['privacyStatus'], 'private')
        self.assertEqual(calls[2][2]['data'], b'fake media for mocked API boundary')

    def test_uncertain_upload_is_not_retried(self):
        calls = []
        def transport(*args, **kwargs):
            calls.append(args)
            raise PublishError('Simulated provider failure')
        self.assertEqual(self.process(live=True, transport=transport)['status'], 'uncertain')
        self.assertEqual(self.process(live=True, transport=transport)['status'], 'already_recorded')
        self.assertEqual(len(calls), 1)

    def test_concurrent_ledger_claim_has_one_winner(self):
        other = Ledger(self.folder / 'state.sqlite3')
        try:
            self.assertTrue(self.ledger.claim('same-post', 'youtube', 'a'))
            self.assertFalse(other.claim('same-post', 'youtube', 'a'))
            self.assertTrue(other.claim('same-post', 'instagram', 'a'))
        finally:
            other.close()

    def test_instagram_waits_until_video_is_processed(self):
        steps = []
        def transport(method, url, **kwargs):
            steps.append((method, url, kwargs))
            if url.endswith('/media'):
                return {'id': '888'}, {}
            if method == 'GET':
                return {'status_code': 'FINISHED'}, {}
            return {'id': '999'}, {}
        report = self.process('instagram', live=True, transport=transport)
        self.assertEqual(report['status'], 'confirmed')
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0][2]['form']['media_type'], 'REELS')
        self.assertEqual(steps[2][2]['form']['creation_id'], '888')
        self.assertNotIn('access_token=', steps[1][1])

    def test_instagram_process_error_never_calls_publish(self):
        calls = []
        def transport(method, url, **kwargs):
            calls.append(url)
            return ({'id': '888'} if method == 'POST' else {'status_code': 'ERROR'}), {}
        self.assertEqual(self.process('instagram', live=True, transport=transport)['status'], 'uncertain')
        self.assertFalse(any('/media_publish' in url for url in calls))

    def test_instagram_needs_public_https_mp4(self):
        self.post['media']['public_video_url'] = 'file:///private/video.mp4'
        reasons = readiness(self.post, self.path, self.config, 'instagram', now=NOW, environ=ENV)
        self.assertTrue(any('HTTPS' in reason for reason in reasons))

    def test_demo_notice_cannot_be_removed(self):
        self.post['captions']['youtube'] = 'Outra legenda'
        self.assertIn('Falta o aviso de loja em demonstração.', self.process(live=True)['blockers'])

    def test_ledger_survives_restart(self):
        path = self.folder / 'restart.sqlite3'
        first = Ledger(path)
        self.assertTrue(first.claim('post', 'youtube', 'hash'))
        first.close()
        second = Ledger(path)
        self.assertFalse(second.claim('post', 'youtube', 'hash'))
        second.close()


if __name__ == '__main__':
    unittest.main()
