import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    'yandex-search', 'yandex-search-web', 'yandex-search-batch', 'yandex-search-serp',
    'yandex-search-competitors', 'yandex-search-rankings', 'yandex-search-clustering',
    'yandex-search-operators', 'yandex-search-research', 'yandex-search-api',
}

class TestPluginLayout(unittest.TestCase):
    def test_codex_manifest_contract(self):
        data = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(data['name'], 'yandex-search')
        self.assertEqual(data['version'], '1.1.0')
        self.assertEqual(data['skills'], './skills/')
    def test_exact_skill_set_exists(self):
        self.assertEqual({p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}, EXPECTED_SKILLS)
    def test_every_skill_is_discoverable(self):
        for skill in EXPECTED_SKILLS:
            text=(ROOT/'skills'/skill/'SKILL.md').read_text(encoding='utf-8'); self.assertTrue(text.startswith('---\n')); self.assertIn('description: Use when',text)
    def test_env_example_has_search_credentials(self):
        text=(ROOT/'.env.example').read_text(encoding='utf-8'); self.assertIn('YANDEX_SEARCH_API_KEY=',text); self.assertIn('YANDEX_SEARCH_IAM_TOKEN=',text); self.assertIn('YANDEX_SEARCH_FOLDER_ID=',text)
    def test_evals_have_scenarios(self):
        data=json.loads((ROOT/'evals/scenarios.json').read_text(encoding='utf-8')); self.assertEqual(data['version'],2); self.assertGreaterEqual(len(data['scenarios']),9)
        for scenario in data['scenarios']:
            expect=scenario['expect']; self.assertIn(expect['outcome'],{'comply','comply_with_limitations','refuse'}); self.assertIn('must_mention_tokens',expect); self.assertIn('must_convey',expect); self.assertIn('must_not_claim',expect)
    def test_package_docs_exist(self):
        for path in ['README.md','CHANGELOG.md','THIRD_PARTY_NOTICES.md']: self.assertTrue((ROOT/path).is_file(),path)
    def test_production_workflow_contracts(self):
        router=(ROOT/'skills/yandex-search/SKILL.md').read_text(encoding='utf-8'); clustering=(ROOT/'skills/yandex-search-clustering/SKILL.md').read_text(encoding='utf-8'); batch=(ROOT/'skills/yandex-search-batch/SKILL.md').read_text(encoding='utf-8'); rankings=(ROOT/'skills/yandex-search-rankings/SKILL.md').read_text(encoding='utf-8'); competitors=(ROOT/'skills/yandex-search-competitors/SKILL.md').read_text(encoding='utf-8'); api=(ROOT/'skills/yandex-search-api/SKILL.md').read_text(encoding='utf-8'); serp=(ROOT/'skills/yandex-search-serp/SKILL.md').read_text(encoding='utf-8')
        for name in sorted(EXPECTED_SKILLS-{'yandex-search'}): self.assertIn(name,router)
        self.assertIn('min_shared_urls',clustering); self.assertIn('bridge_risk',clustering); self.assertIn('GROUP_MODE_FLAT',clustering); self.assertIn('cost preview',batch.lower()); self.assertIn('searchAsync',batch); self.assertIn('config_fingerprint',rankings); self.assertIn('SERP presence rate',competitors); self.assertIn('market share',competitors.lower()); self.assertIn('250', api); self.assertIn('max_supported_results', serp)
    def test_current_reference_set_exists(self):
        expected={'api-2026.md','auth.md','request-model.md','serp.md','async.md','clustering.md','rankings.md','operators.md','quota-pricing.md','safety.md','sources.md'}; self.assertEqual({p.name for p in (ROOT/'references').glob('*.md')},expected)

if __name__ == '__main__': unittest.main()
