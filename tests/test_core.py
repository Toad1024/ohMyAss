"""核心逻辑单元测试（时间轴、样式、术语、报告解析）。

运行：python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app_info  # noqa: E402
import config_store  # noqa: E402
import reports  # noqa: E402
import subtitle_core as core  # noqa: E402


class TimeTests(unittest.TestCase):
    def test_parse_ass_time(self):
        self.assertEqual(core.parse_ass_time('0:00:01.23'), 1230)
        self.assertEqual(core.parse_ass_time('1:02:03.45'), 3723450)
        self.assertEqual(core.parse_ass_time('00:00:00.00'), 0)
        self.assertIsNone(core.parse_ass_time('bad'))
        self.assertIsNone(core.parse_ass_time('1:2'))

    def test_format_ass_time(self):
        self.assertEqual(core.format_ass_time(1230), '0:00:01.23')
        self.assertEqual(core.format_ass_time(-5), '0:00:00.00')
        self.assertEqual(core.format_ass_time(3723450), '1:02:03.45')

    def test_srt_time_to_ass(self):
        self.assertEqual(core.srt_time_to_ass('00:00:01,500'), '0:00:01.50')
        self.assertEqual(core.srt_time_to_ass('01:02:03.456'), '1:02:03.45')
        self.assertIsNone(core.srt_time_to_ass('nope'))

    def test_srt_to_ass(self):
        text = (
            '1\n'
            '00:00:01,000 --> 00:00:02,500\n'
            '第一行\n'
            '第二行\n\n'
            '2\n'
            '00:00:03,000 --> 00:00:04,000\n'
            '<i>Hi</i>\n'
        )
        result = core.srt_to_ass(text)
        self.assertIn('Style: Default', result)
        self.assertIn('Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,第一行\\N第二行', result)
        self.assertIn('Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,Hi', result)


class StyleTests(unittest.TestCase):
    def test_default_style_lines_are_complete(self):
        for kind, _label in core.STYLE_CATEGORIES:
            line = core.default_style_line(kind)
            self.assertTrue(line.startswith(f'Style: {kind},'), kind)
            self.assertEqual(len(line.split(',')), 23, kind)

    def test_style_category_maps(self):
        self.assertIn('Default', core.STYLE_KIND_TO_LABEL)
        self.assertEqual(len(core.STYLE_CATEGORIES), 11)
        for kind, label in core.STYLE_CATEGORIES:
            self.assertEqual(core.STYLE_LABEL_TO_KIND[label], kind)

    def test_mid_black_margins_follow_defaults(self):
        kinds = {kind for kind, _label in core.STYLE_CATEGORIES if kind != 'Default'}
        self.assertEqual(set(core.MID_BLACK_MARGINS), kinds)
        for kind in kinds:
            margin = int(core.default_style_line(kind).split(',')[21])
            self.assertEqual(core.MID_BLACK_MARGINS[kind], margin + 44)

    def test_apply_updated_margin_only(self):
        kind = 'zh_dialogue_bilingual'
        base = core.default_style_line(kind).split(',')
        changed = list(base)
        changed[21] = '99'
        updated = core.apply_updated_margin_v(','.join(changed), kind, 58)
        self.assertEqual(updated.split(',')[21], '58')

        other = list(base)
        other[2] = '123'
        self.assertEqual(
            core.apply_updated_margin_v(','.join(other), kind, 58),
            ','.join(other))

    def test_apply_updated_fontsize_only(self):
        kind = 'zh_dialogue_bilingual'
        base = core.default_style_line(kind).split(',')
        changed = list(base)
        changed[2] = '120'
        updated = core.apply_updated_fontsize(','.join(changed), kind, 80)
        self.assertEqual(updated.split(',')[2], '80')

        other = list(base)
        other[21] = '99'
        self.assertEqual(
            core.apply_updated_fontsize(','.join(other), kind, 80),
            ','.join(other))

    def test_linked_fsvp_kinds(self):
        self.assertEqual(
            core.linked_fsvp_kinds('en_dialogue_bilingual'),
            ('zh_dialogue_bilingual', 'en_dialogue_bilingual'))
        self.assertEqual(
            core.linked_fsvp_kinds('zh_note_double_line'),
            ('zh_note_double_line',))


class GlossaryTests(unittest.TestCase):
    def test_normalize_glossary(self):
        data = [
            {'source': ' Apple ', 'target': '苹果'},
            {'source': 'Apple', 'target': '苹果公司', 'case_sensitive': True},
            {'source': '', 'target': '空'},
            ['Banana', '香蕉', True, '备注'],
            'invalid',
        ]
        result = core.normalize_glossary(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['source'], 'Apple')
        self.assertEqual(result[0]['target'], '苹果公司')
        self.assertTrue(result[0]['case_sensitive'])
        self.assertEqual(result[1]['note'], '备注')
        self.assertEqual(core.normalize_glossary(None), [])

    def test_term_in_text(self):
        self.assertTrue(core.term_in_text('Hello World', 'world'))
        self.assertFalse(core.term_in_text('Worldwide', 'world'))
        self.assertFalse(core.term_in_text('Hello World', 'world', case_sensitive=True))
        self.assertTrue(core.term_in_text('这是测试文本', '测试'))
        self.assertFalse(core.term_in_text('', '测试'))

    def test_glossary_consistency(self):
        notices = []

        class FakeSub:
            glossary = core.normalize_glossary([
                {'source': 'Apple', 'target': '苹果'},
                {'source': 'Pear', 'target': '梨子'},
            ])

            def add_notice(self, text):
                notices.append(text)

        sub = FakeSub()
        core.check_glossary_consistency(
            sub,
            [{'text': '我喜欢苹果'}],
            [{'text': 'I like Apple'}],
        )
        self.assertEqual(notices, [])

        notices.clear()
        core.check_glossary_consistency(
            sub,
            [{'text': '我喜欢凤梨'}],
            [{'text': 'I like Pear'}],
        )
        self.assertEqual(len(notices), 1)
        self.assertIn('术语表不符', notices[0])

        notices.clear()
        sub.glossary = []
        core.check_glossary_consistency(sub, [{'text': 'x'}], [{'text': 'Apple'}])
        self.assertEqual(notices, [])


class ReportTests(unittest.TestCase):
    def test_parse_issue_entries(self):
        data = {
            'notices': [
                {'index': 3, 'need': '请处理', 'problem': '对白行数大于2'},
                {'index': '4', 'need': '请验证', 'problem': '疑似英文缺失'},
                {'index': 5, 'need': '请查验', 'problem': '译文缺失'},
                {'index': 5, 'need': '请确认', 'problem': '中文对白行数大于1'},
                {'index': 'bad', 'need': '请处理', 'problem': 'x'},
                {'index': 6, 'need': '请检查', 'problem': 'x'},
            ]
        }
        entries = reports.parse_issue_entries(data)
        self.assertEqual(set(entries), {3, 4, 5})
        self.assertEqual(entries[3]['need'], '请处理')
        self.assertEqual(entries[4]['need'], '请确认')
        self.assertEqual(entries[5]['need'], '请确认')
        self.assertEqual(entries[5]['problems'],
                         ['译文缺失', '中文对白行数大于1'])
        self.assertEqual(reports.parse_issue_entries([]), {})

    def test_build_notices_html(self):
        page = reports.build_notices_html(
            'demo.ass', '片名', [
                '3,对白行数大于2,请处理',
                '5,疑似英文缺失,请验证',
                '6,译文缺失,请查验',
            ])
        self.assertIn('对白行数大于2', page)
        self.assertIn('请处理', page)
        self.assertIn('请确认', page)
        self.assertNotIn('请验证', page)
        self.assertNotIn('请查验', page)
        self.assertIn('问题总数<b>3</b>', page)

    def test_build_notices_html_escapes(self):
        page = reports.build_notices_html(
            'x.ass', '<b>片名</b>', ['1,<script>,请处理'])
        self.assertIn('&lt;b&gt;片名&lt;/b&gt;', page)
        self.assertIn('&lt;script&gt;', page)


class UpdateScriptTests(unittest.TestCase):
    def test_update_script_is_ascii_and_crlf(self):
        import app_update

        script = app_update.build_app_update_script()
        self.assertTrue(script.isascii())
        self.assertIn('copy /Y "%SOURCE%" "%TARGET%"', script)
        self.assertIn('start "" "%TARGET%"', script)
        self.assertIn('%LOG%', script)
        data = script.encode('ascii')
        # 之前的 bug：文本模式写入导致每行变成 CR CR LF
        self.assertNotIn(b'\r\r\n', data)
        self.assertNotIn(b'\n', data.replace(b'\r\n', b''))


class ConfigTests(unittest.TestCase):
    def test_config_roundtrip_and_error_log(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            old_config = config_store.CONFIG_PATH
            old_log = config_store.ERROR_LOG_PATH
            config_store.CONFIG_PATH = os.path.join(folder, 'ohMyAssNoto.json')
            config_store.ERROR_LOG_PATH = os.path.join(folder, 'error.log')
            try:
                config_store.save_config({'theme_mode': 'dark'})
                self.assertEqual(config_store.load_config(), {'theme_mode': 'dark'})

                with open(config_store.CONFIG_PATH, 'w', encoding='utf-8') as handle:
                    handle.write('{broken')
                self.assertEqual(config_store.load_config(), {})
                self.assertTrue(os.path.isfile(config_store.ERROR_LOG_PATH))
            finally:
                config_store.CONFIG_PATH = old_config
                config_store.ERROR_LOG_PATH = old_log

    def test_sanitize_folder_name(self):
        self.assertEqual(config_store.sanitize_folder_name('a:b*c?'), 'a：b＊c？')
        self.assertEqual(config_store.sanitize_folder_name('name. '), 'name')
        self.assertEqual(config_store.sanitize_folder_name('CON'), 'CON_')
        self.assertEqual(config_store.sanitize_folder_name(''), '')


class VersionTests(unittest.TestCase):
    def test_version_tuple(self):
        self.assertEqual(app_info.version_tuple('v0.5.8'), (0, 5, 8))
        self.assertGreater(
            app_info.version_tuple('v0.5.10'),
            app_info.version_tuple('v0.5.9'))
        self.assertEqual(app_info.version_tuple(''), (0,))


if __name__ == '__main__':
    unittest.main()
