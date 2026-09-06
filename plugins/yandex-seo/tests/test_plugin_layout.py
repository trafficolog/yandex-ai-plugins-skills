import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    'yandex-seo','yandex-seo-audit','yandex-seo-opportunities','yandex-seo-clusters',
    'yandex-seo-content-gaps','yandex-seo-cannibalization','yandex-seo-ctr',
    'yandex-seo-conversions','yandex-seo-technical','yandex-seo-prioritize',
    'yandex-seo-topical-architecture','yandex-seo-internal-linking','yandex-seo-weekly-report'
}

class PluginLayoutTests(unittest.TestCase):
    def test_manifest_contract(self):
        p = ROOT / '.codex-plugin/plugin.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(data['name'], 'yandex-seo')
        self.assertEqual(data['version'], '1.1.2')
        self.assertEqual(data['skills'], './skills/')

    def test_exact_skill_set(self):
        got = {p.parent.name for p in (ROOT/'skills').glob('*/SKILL.md')}
        self.assertEqual(got, SKILLS)

    def test_docs_and_dirs(self):
        for rel in ['README.md','CHANGELOG.md','THIRD_PARTY_NOTICES.md','evals/scenarios.json','references','scripts','tests']:
            self.assertTrue((ROOT/rel).exists(), rel)
        self.assertTrue((ROOT/'references/topical-architecture.md').exists())
        self.assertTrue((ROOT/'references/internal-linking.md').exists())
        self.assertTrue((ROOT/'references/weekly-organic-report.md').exists())

    def test_topical_architecture_contract(self):
        text = (ROOT/'skills/yandex-seo-topical-architecture/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('seo-topical-architecture/v1', text)
        self.assertIn('GREENFIELD', text)
        self.assertIn('EXISTING_SITE', text)
        self.assertIn('SERP_VALIDATION_MISSING', text)
        self.assertIn('SERP_VALIDATION_PARTIAL', text)
        self.assertIn('METHODOLOGY', text)

    def test_internal_linking_contract(self):
        text = (ROOT/'skills/yandex-seo-internal-linking/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('preview-only', text.lower())
        self.assertIn('ORPHAN_PAGE', text)
        self.assertIn('DUPLICATE_LINK', text)
        self.assertIn('BROKEN_SEMANTIC_BRIDGE', text)
        self.assertIn('MISSING_JUSTIFIED_LINK', text)
        self.assertIn('exact-match', text.lower())

    def test_weekly_report_contract(self):
        text = (ROOT/'skills/yandex-seo-weekly-report/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('seo-weekly-organic-report/v1', text)
        self.assertIn('yandex-ai-artifact-manifest/v1', text)
        self.assertIn('Webmaster', text)
        self.assertIn('Metrika', text)
        self.assertIn('read-only', text.lower())
        self.assertIn('PREVIEW-ONLY', text)
        self.assertIn('seo_weekly_report.py demo', text)

    def test_no_credentials_contract(self):
        self.assertFalse((ROOT/'.env.example').exists())
        text = (ROOT/'.codex-plugin/plugin.json').read_text(encoding='utf-8')
        for token in ['YANDEX_TOKEN','API_KEY','OAuth','credential']:
            self.assertNotIn(token, text)

if __name__ == '__main__': unittest.main()
