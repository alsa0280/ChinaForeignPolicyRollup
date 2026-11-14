"""Offline reference for an evidence-led opportunity monitor. Python 3.11+.

No live fetch, model invocation, scheduling, messaging or automatic ask approval.
Run: python pipeline.py --demo --out demo-output
"""
from __future__ import annotations
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent.parent   # repo root (this file lives in reference/)

def connect(path=':memory:'):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript((BASE/'schemas/register.sql').read_text())
    return db

def seed(db):
    sources = json.loads((BASE/'data/sources.json').read_text())
    opportunities = json.loads((BASE/'data/opportunities.json').read_text())
    ids = {s['id'] for s in sources}
    for s in sources:
        if not s['url'] or not s['url'].startswith('https://'):
            raise ValueError('Source must have a known HTTPS URL')
        db.execute('INSERT OR IGNORE INTO sources VALUES (?, ?)',(s['id'],json.dumps(s)))
    for o in opportunities:
        if o['top_ask_approved']:
            raise ValueError('This reference pipeline cannot approve a Top Ask')
        if not o['source_ids'] or not set(o['source_ids']) <= ids:
            raise ValueError('Opportunity missing valid source references')
        db.execute('INSERT OR IGNORE INTO opportunities VALUES (?, ?)',(o['opportunity_id'],json.dumps(o)))
    db.commit()
    return opportunities

def validate_event(db, event, as_of):
    required = {'opportunity_id','dimension','event_date','publication_date','value','source_id','claim','locator','evidence_kind','source_authority'}
    if not required <= event.keys():
        raise ValueError('Missing event fields: '+str(required-event.keys()))
    if not db.execute('SELECT 1 FROM sources WHERE id=?',(event['source_id'],)).fetchone():
        raise ValueError('Unknown source')
    if not db.execute('SELECT 1 FROM opportunities WHERE id=?',(event['opportunity_id'],)).fetchone():
        raise ValueError('Unknown opportunity')
    if date.fromisoformat(event['event_date']) > as_of:
        raise ValueError('Future events must be stored as plans, not occurred events')
    if date.fromisoformat(event['publication_date']) > as_of:
        raise ValueError('Future publication date')
    if event['source_authority'] not in {'official','company','reported'}:
        raise ValueError('Unknown evidence authority')
    if event['evidence_kind'] not in {'paraphrased_fixture','source_span'}:
        raise ValueError('Unknown evidence type')
    if event['evidence_kind']=='source_span' and not event.get('original_support_span'):
        raise ValueError('Live extraction requires original source support')
    if not event['claim'].strip() or not event['locator'].strip():
        raise ValueError('Empty claim or locator')
    amount = event.get('amount')
    if amount is not None:
        if not {'value','currency','kind'} <= amount.keys():
            raise ValueError('Money requires value currency and amount type')
        if amount['currency'] not in {'CAD','USD','CNY','EUR','GBP','JPY','HKD'}:
            raise ValueError('Use an explicit supported currency; do not assume dollar currency')
        if not isinstance(amount['value'],(int,float)) or isinstance(amount['value'],bool) or amount['value'] < 0:
            raise ValueError('Invalid monetary value')
        if amount['kind'] not in {'upfront','contingent_milestone','capex','acquisition_equity','annual_sales','financing'}:
            raise ValueError('Unknown amount type')

def fingerprint(event):
    # The demo uses manually resolved IDs. A live implementation needs entity
    # resolution and normalized claims; textual similarity alone is insufficient.
    key = {k:event[k] for k in ('opportunity_id','dimension','event_date','value')}
    return hashlib.sha256(json.dumps(key,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def ingest(db,event,as_of):
    validate_event(db,event,as_of)
    key = fingerprint(event)
    if db.execute('SELECT 1 FROM events WHERE id=?',(key,)).fetchone():
        # Retain each supporting reference even when the semantic event repeats.
        db.execute('INSERT OR IGNORE INTO event_evidence VALUES (?, ?, ?)',(key,event['source_id'],json.dumps(event)))
        db.commit()
        return 'duplicate'
    db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?)',(key,event['opportunity_id'],event['dimension'],event['event_date'],json.dumps(event)))
    db.execute('INSERT INTO event_evidence VALUES (?, ?, ?)',(key,event['source_id'],json.dumps(event)))
    old = db.execute('SELECT * FROM current_state WHERE opportunity_id=? AND dimension=?',(event['opportunity_id'],event['dimension'])).fetchone()
    if old and event['event_date'] < old['event_date']:
        outcome = 'historical'
    elif old and event['event_date']==old['event_date'] and old['value_json']!=json.dumps(event['value'],sort_keys=True):
        # Do not silently adjudicate a contradiction by publication or arrival date.
        db.execute('UPDATE current_state SET conflict=1 WHERE opportunity_id=? AND dimension=?',(event['opportunity_id'],event['dimension']))
        outcome = 'conflict_review'
    else:
        db.execute('INSERT OR REPLACE INTO current_state VALUES (?, ?, ?, ?, ?, ?)',(event['opportunity_id'],event['dimension'],event['event_date'],json.dumps(event['value'],sort_keys=True),key,0))
        outcome = 'new_dimension' if old is None else 'material_change'
    db.commit()
    return outcome

def save_health(db,run_id,source_id,success,error=None):
    if not db.execute('SELECT 1 FROM sources WHERE id=?',(source_id,)).fetchone():
        raise ValueError('Unknown source health ID')
    db.execute('INSERT OR REPLACE INTO source_health VALUES (?, ?, ?, ?)',(run_id,source_id,int(success),error))
    db.commit()

def digest(db,as_of,outcomes,run_id='fixture-demo'):
    opportunities = {r['id']:json.loads(r['payload']) for r in db.execute('SELECT * FROM opportunities')}
    health = [dict(r) for r in db.execute('SELECT * FROM source_health WHERE run_id=?',(run_id,))]
    parts = ['# Demonstration daily digest',f'As of {as_of.isoformat()}. OFFLINE FIXTURE REPLAY. No live monitoring occurred.',
      '', '## Material evidence outcomes']
    for event,outcome in outcomes:
        if outcome not in {'duplicate','historical'}:
            parts += [f"- {event['opportunity_id']} | {outcome} | {event['dimension']}: {event['value']}",
              f"  Evidence: {event['claim']} [{event['source_id']}; {event['locator']}]",
              f"  Review: {opportunities[event['opportunity_id']]['validation_needed']}"]
    parts += ['', '## Expiries within 90 days']
    for o in opportunities.values():
        if o.get('deadline'):
            days = (date.fromisoformat(o['deadline'])-as_of).days
            if 0<=days<=90:
                parts += [f"- {o['opportunity_id']}: {o['deadline']} ({days} days). Confirm any superseding notice."]
    parts += ['', '## Source coverage']
    if not health:
        parts += ['Coverage unknown: no collection health records. This is not evidence of no change.']
    else:
        parts += [f"Fixture records only: {sum(r['success'] for r in health)}/{len(health)} simulated sources successful. Other sources were not attempted."]
        for r in health:
            if not r['success']:
                parts += [f"- {r['source_id']}: collection failed ({r['error']}); current status unknown."]
    parts += ['', '## Top asks', 'None automatically approved. Departmental and company validation belongs in the human workflow.',
      '', 'The public seed register is a separate researched baseline, not the output of this demonstration run.']
    return '\n'.join(parts)+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--out',default='demo-output')
    parser.add_argument('--as-of',default='2026-10-27')
    args=parser.parse_args()
    if not args.demo:
        parser.error('Only --demo is implemented. Build and validate live adapters separately.')
    as_of=date.fromisoformat(args.as_of)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    # Deterministic fresh replay; never overwrite a production database.
    db=connect();seed(db)
    events=[json.loads(s) for s in (BASE/'reference/data/demo_events.jsonl').read_text().splitlines() if s.strip()]
    outcomes=[(e,ingest(db,e,as_of)) for e in events]
    save_health(db,'fixture-demo','S13',True)
    save_health(db,'fixture-demo','S46',False,'simulated HTTP 403')
    (out/'daily_digest.md').write_text(digest(db,as_of,outcomes))
    (out/'event_outcomes.json').write_text(json.dumps([dict(event=e,outcome=o) for e,o in outcomes],indent=2))
    target=sqlite3.connect(out/'register.sqlite');db.backup(target);target.close()
    print(f'{len(events)} fixture events processed; outputs written to {out.resolve()}')

if __name__=='__main__':
    main()
