import copy
from datetime import date
import json
from pathlib import Path
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pipeline as p

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.db=p.connect();p.seed(self.db)
        self.today=date(2026,10,27)
        self.e=dict(opportunity_id='E07',dimension='contract_stage',event_date='2026-10-26',publication_date='2026-10-26',value='definitive_contract',source_id='S13',claim='SEFE announced a supply agreement.',locator='Supply agreement announcement',evidence_kind='paraphrased_fixture',source_authority='company')
    def tearDown(self): self.db.close()
    def test_seed_has_28_records_and_valid_sources(self):
        self.assertEqual(self.db.execute('SELECT count(*) FROM opportunities').fetchone()[0],28)
    def test_semantic_duplicate_and_extra_evidence(self):
        self.assertEqual(p.ingest(self.db,self.e,self.today),'new_dimension')
        e=copy.deepcopy(self.e);e['source_id']='S01'
        self.assertEqual(p.ingest(self.db,e,self.today),'duplicate')
        self.assertEqual(self.db.execute('SELECT count(*) FROM event_evidence').fetchone()[0],2)
    def test_old_event_cannot_replace_new_state(self):
        p.ingest(self.db,self.e,self.today)
        e=copy.deepcopy(self.e);e.update(event_date='2026-05-27',publication_date='2026-10-27',value='heads_of_agreement')
        self.assertEqual(p.ingest(self.db,e,self.today),'historical')
        self.assertEqual(json.loads(self.db.execute('SELECT value_json FROM current_state').fetchone()[0]),'definitive_contract')
    def test_same_date_conflict_requires_review(self):
        p.ingest(self.db,self.e,self.today)
        e=copy.deepcopy(self.e);e['value']='cancelled'
        self.assertEqual(p.ingest(self.db,e,self.today),'conflict_review')
        self.assertEqual(self.db.execute('SELECT conflict FROM current_state').fetchone()[0],1)
    def test_legal_and_operational_dimensions_coexist(self):
        e=copy.deepcopy(self.e);e.update(opportunity_id='F06',dimension='legal_permission',value='protocol_permits_compliant_products',source_id='S34')
        p.ingest(self.db,e,self.today)
        e=copy.deepcopy(e);e.update(dimension='certificate_status',value='unavailable',source_id='S32')
        p.ingest(self.db,e,self.today)
        self.assertEqual(self.db.execute('SELECT count(*) FROM current_state').fetchone()[0],2)
    def test_missing_source_rejected(self):
        e=copy.deepcopy(self.e);e['source_id']='invented'
        with self.assertRaises(ValueError):p.ingest(self.db,e,self.today)
    def test_future_event_rejected(self):
        e=copy.deepcopy(self.e);e['event_date']='2027-06-01'
        with self.assertRaises(ValueError):p.ingest(self.db,e,self.today)
    def test_ambiguous_currency_rejected(self):
        e=copy.deepcopy(self.e);e['amount']=dict(value=15,currency='$',kind='contingent_milestone')
        with self.assertRaises(ValueError):p.ingest(self.db,e,self.today)
    def test_real_extraction_needs_support_span(self):
        e=copy.deepcopy(self.e);e['evidence_kind']='source_span'
        with self.assertRaises(ValueError):p.ingest(self.db,e,self.today)
    def test_failed_sources_are_not_no_change(self):
        p.save_health(self.db,'run','S46',False,'blocked')
        text=p.digest(self.db,self.today,[],'run')
        self.assertIn('current status unknown',text)
        self.assertIn('Other sources were not attempted',text)
    def test_no_automatic_top_asks(self):
        text=p.digest(self.db,self.today,[])
        self.assertIn('None automatically approved',text)
    def test_source_free_coverage_is_unknown(self):
        self.assertIn('Coverage unknown',p.digest(self.db,self.today,[]))

if __name__=='__main__':unittest.main()
