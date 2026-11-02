#!/usr/bin/env python3
"""Local fixture/project consistency only. No backend/app build or network."""
from pathlib import Path
import json,re,sys,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
f=root/'contracts/fixtures'
boot=json.loads((f/'bootstrap.json').read_text())
assert [b['id'] for b in boot['businesses']]==[101,202]
assert boot['active_business']['id'] in [b['id'] for b in boot['businesses']]
for business in [101,202]:
 listing=json.loads((f/f'appointments-{business}.json').read_text())
 assert listing['business']==business and listing['date']=='2026-10-28'
 assert listing['summary']['total']==len(listing['items'])
 assert len({a['id'] for a in listing['items']})==len(listing['items'])
 for item in listing['items']:
  detail=json.loads((f/f'appointment-{business}-{item["id"]}.json').read_text())
  assert detail['business']==business and detail['appointment']==item
  assert set(['id','title','status','start_at','end_at']) <= item.keys()
for business in [101,202]:
 clients=json.loads((f/f'clients-{business}.json').read_text())
 assert clients['business']==business and clients['summary']['total']>=len(clients['items'])
 assert len({client['id'] for client in clients['items']})==len(clients['items'])
 for client in clients['items']:
  assert isinstance(client['id'],int) and client['id']>0
  assert all(client.get(key) is None or isinstance(client[key],str) for key in ['title','phone','email'])
for business in [101,202]:
 inbox=json.loads((f/f'inbox-{business}.json').read_text())
 assert inbox['business']==business and inbox['summary']['open']>=len(inbox['items'])
 assert len({item['id'] for item in inbox['items']})==len(inbox['items'])
 for item in inbox['items']:
  thread=json.loads((f/f'inbox-{business}-{item["id"]}.json').read_text())
  assert thread['business']==business and thread['conversation']=={k:v for k,v in item.items() if k!='last_message_preview'}
  assert len(thread['messages'])<=thread['payload_budget']['max_messages']
  assert len({m['id'] for m in thread['messages']})==len(thread['messages'])
  assert all(m['conversation_id']==item['id'] for m in thread['messages'])
  preview=item['last_message_preview']; last=thread['messages'][-1] if thread['messages'] else None
  assert preview['text']==((last['text'] or '')[:160] if last else '')
for business in [101,202]:
 tasks=json.loads((f/f'tasks-{business}.json').read_text())
 assert tasks['business']==business and tasks['summary']['total']>=len(tasks['items'])
 assert len({t['id'] for t in tasks['items']})==len(tasks['items'])
 for task in tasks['items']:
  detail=json.loads((f/f'task-{business}-{task["id"]}.json').read_text())
  assert detail['business']==business and detail['task']==task
  assert task['priority'] is None or isinstance(task['priority'],str)
  assert len(detail['comments'])<=detail['payload_budget']['max_comments']
  assert len({c['id'] for c in detail['comments']})==len(detail['comments'])
for business,thread_id,client_id in [(101,901,701),(202,951,801)]:
 thread=json.loads((f/f'inbox-{business}-{thread_id}.json').read_text())
 profile=json.loads((f/f'client-{business}-{client_id}.json').read_text())
 assert thread['business']==profile['business']==business
 assert thread['details']['client']['id']==profile['client']['id']==client_id
 # Only the explicit ID is consumed for routing; the independently read profile
 # owns contacts/notes and the user action must not reuse source-thread contacts.
 assert thread['details']['lead'] is None
for business in [101,202]:
 notifications=json.loads((f/f'notifications-{business}.json').read_text())
 assert notifications['business']==business and notifications['summary']['total']>=len(notifications['items'])
 assert len({n['id'] for n in notifications['items']})==len(notifications['items'])
 for item in notifications['items']:
  if item['action_url'].startswith('/app/calendar'):
   target=json.loads((f/f'appointment-{business}-{item["appointment_id"]}.json').read_text())
   assert target['business']==business and target['appointment']['id']==item['appointment_id']
for business in [101,202]:
 clients=json.loads((f/f'clients-{business}.json').read_text())['items']
 history=json.loads((f/f'appointments-history-{business}.json').read_text())
 assert history['business']==business and history['date']=='2026-10-27'
 for client in clients:
  profile=json.loads((f/f'client-{business}-{client["id"]}.json').read_text())
  assert profile['business']==business and profile['client']['id']==client['id']
  assert profile['client']['notes']==(profile['details']['notes'] or '')[:160]
  assert len(profile['related']['appointments'])<=profile['payload_budget']['max_related_per_section']
  for record in profile['related']['appointments']:
   assert record['client_id']==client['id'] and record in history['items']
   detail=json.loads((f/f'appointment-{business}-{record["id"]}.json').read_text())
   assert detail['business']==business and detail['appointment']==record
# Client work windows are independent source projections, not joins against loaded
# global lists. Every clickable fixture must have a separately scoped GET body.
for business,client_id in [(101,701),(202,801)]:
 profile=json.loads((f/f'client-{business}-{client_id}.json').read_text())
 limit=profile['payload_budget']['max_related_per_section']
 assert 1<=limit<=5
 for section,prefix,body_key in [('tasks','task','task'),('conversations','inbox','conversation')]:
  rows=profile['related'][section]
  assert len(rows)<=limit and len({row['id'] for row in rows})==len(rows)
  global_rows=json.loads((f/f'{"tasks" if section=="tasks" else "inbox"}-{business}.json').read_text())['items']
  assert not {row['id'] for row in rows}&{row['id'] for row in global_rows}, 'Related fixture accidentally rebound global list records'
  for row in rows:
   assert isinstance(row['id'],int) and row['id']>0
   target=json.loads((f/f'{prefix}-{business}-{row["id"]}.json').read_text())
   assert target['business']==business and target[body_key]==row
   if section=='tasks':
    assert row['client_id']==client_id
    assert len(target['comments'])<=target['payload_budget']['max_comments']
   else:
    assert target['details']['client']['id']==client_id and row['unread_count']>=0
    assert len(target['messages'])<=target['payload_budget']['max_messages']
    assert len({message['id'] for message in target['messages']})==len(target['messages'])
    assert all(message['conversation_id']==row['id'] for message in target['messages'])
for business in [101,202]:
 home=json.loads((f/f'home-{business}.json').read_text()); today=json.loads((f/f'today-{business}.json').read_text())
 agenda=json.loads((f/f'appointments-{business}.json').read_text()); tasks=json.loads((f/f'tasks-{business}.json').read_text()); inbox=json.loads((f/f'inbox-{business}.json').read_text())
 assert home['business']==today['business']==business and today['date']==agenda['date']
 assert home['limit']==home['payload_budget']['max_items_per_section']==5
 assert today['limit']==today['payload_budget']['max_items_per_section']==20
 assert home['sections']['appointments']['today']==today['sections']['appointments']['total']==agenda['summary']['total']
 assert today['sections']['appointments']['items']==agenda['items']
 assert home['sections']['tasks']['open']==tasks['summary']['open']
 assert home['sections']['conversations']['unread']==inbox['summary']['unread']
 assert home['sections']['conversations']['open']==inbox['summary']['open']
 assert home['attention']['total']==sum(item['count'] for item in home['attention']['items'])
 for name in ['appointments','tasks']:
  section=today['sections'][name]
  assert section['date']==today['date'] and section['total']>=len(section['items'])
  assert len(section['items'])<=today['limit'] and len({item['id'] for item in section['items']})==len(section['items'])
 assert all(item in tasks['items'] for item in today['sections']['tasks']['items'])
 assert all(item['status'] not in ['done','cancelled'] and item['due_at'].startswith(today['date']) for item in today['sections']['tasks']['items'])
 assert home['sections']['tasks']['today']==today['sections']['tasks']['total']==len(today['sections']['tasks']['items'])
for business in [101,202]:
 queue=json.loads((f/f'actions-{business}.json').read_text())
 assert queue['business']==business and queue['total']==len(queue['items'])
 assert 1<=queue['limit']<=50 and queue['payload_budget']['max_items']==queue['limit'] and len(queue['items'])<=queue['limit']
 assert len({(row['key'],row['type'],row['entity']['id']) for row in queue['items']})==len(queue['items'])
 assert [row['priority'] for row in queue['items']]==sorted(row['priority'] for row in queue['items'])
 for row in queue['items']:
  entity=row['entity']; assert isinstance(entity['id'],int) and entity['id']>0
  if (row['key'],row['type'])==('complete_task','task'):
   assert entity['href']==f"/app/tasks?task={entity['id']}"
   detail=json.loads((f/f"task-{business}-{entity['id']}.json").read_text())
   assert detail['business']==business and detail['task']==entity
  elif (row['key'],row['type'])==('reply_conversation','conversation'):
   assert entity['href']==f"/app/conversations?conversation={entity['id']}"
   detail=json.loads((f/f"inbox-{business}-{entity['id']}.json").read_text())
   assert detail['business']==business and detail['conversation']==entity and all(message['conversation_id']==entity['id'] for message in detail['messages'])
  elif (row['key'],row['type'])==('confirm_appointment','appointment'):
   assert entity['href']==f"/app/calendar?appointment={entity['id']}"
   detail=json.loads((f/f"appointment-{business}-{entity['id']}.json").read_text())
   assert detail['business']==business and detail['appointment']==entity
edge=json.loads((f/'appointments-agenda-edge-101.json').read_text())
assert edge['business']==101 and edge['date']=='2026-10-29' and edge['summary']['total']>len(edge['items'])
assert len({row['id'] for row in edge['items']})==len(edge['items'])
for row in edge['items']:
 detail=json.loads((f/f"appointment-101-{row['id']}.json").read_text())
 assert detail['business']==101 and detail['appointment']==row and 'resource' not in row
 assert row['start_at'] is None or isinstance(row['start_at'],str)
 assert row['end_at'] is None or isinstance(row['end_at'],str)
dst=json.loads((f/'appointments-agenda-dst-101.json').read_text())
assert dst['business']==101 and dst['date']=='2026-11-01' and len(dst['items'])==2
parent=json.loads((f/'appointment-101-501.json').read_text())
assert parent['appointment']['client_id']==parent['details']['client']['id']==7001
assert parent['payload_budget']['max_related_per_section']==5 and len(parent['related']['tasks'])==5
for task in parent['related']['tasks']:
 target=json.loads((f/f"task-101-{task['id']}.json").read_text())
 assert target['business']==parent['business'] and target['task']==task and target['details']['appointment_id']==parent['appointment']['id']
for business,id,appointment in [(101,7001,501),(202,7003,601)]:
 profile=json.loads((f/f'client-{business}-{id}.json').read_text()); record=json.loads((f/f'appointment-{business}-{appointment}.json').read_text())
 assert profile['business']==record['business']==business and profile['client']['id']==record['appointment']['client_id']==record['details']['client']['id']==id
 assert profile['client']['notes']==profile['details']['notes'][:160]
 assert all(visit['client_id']==id for visit in profile['related']['appointments'])
partial=json.loads((f/'appointments-partial.json').read_text())
assert partial['summary']['total']>len(partial['items'])
dictionaries=json.loads((root/'contracts/ui-copy.json').read_text())
assert set(dictionaries)=={'ru','kk','en'}
expected=set(dictionaries['en'])
for locale, values in dictionaries.items():
 assert set(values)==expected and all(isinstance(v,str) and v.strip() for v in values.values()), locale
assert dictionaries['ru']['resource']=='Специалист' and dictionaries['kk']['resource']=='Маман'
copy=dictionaries['en']
assert {'fixtureMode','configurationRequired','empty','retry','partial'} <= copy.keys()
assert 'API' in copy['fixtureMode']
# Generated build/lint caches can use .xml for non-XML serialization.
# Validate project sources without interpreting generated outputs.
for p in (root/'android/app/src').rglob('*.xml'): ET.parse(p)
for p in (root/'ios/PlatformaCRM.xcodeproj/xcshareddata/xcschemes').rglob('*.xcscheme'): ET.parse(p)
project=(root/'ios/PlatformaCRM.xcodeproj/project.pbxproj').read_text()
app_configs=[value for value in re.findall(r'buildSettings = \{([^}]+)\}',project) if 'PRODUCT_BUNDLE_IDENTIFIER' in value]
assert len(app_configs)==2
for config in app_configs:
 assert 'PRODUCT_BUNDLE_IDENTIFIER = kz.zani.mobile;' in config
 for field in ['MARKETING_VERSION','CURRENT_PROJECT_VERSION']:
  assert re.search(field+r'\s*=\s*[^;\s]+\s*;',config), field
android=(root/'android/app/build.gradle.kts').read_text()
assert 'applicationId = "kz.zani.mobile"' in android
assert re.search(r'versionName\s*=\s*"[^"\s]+"',android)
assert re.search(r'versionCode\s*=\s*[1-9][0-9]*',android)
manifest=ET.parse(root/'android/app/src/main/AndroidManifest.xml').getroot()
assert not manifest.findall('uses-permission'), 'No device/provider/network permission in fixture slice'
assert 'FixtureTransport' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert '#if DEBUG' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'if (BuildConfig.DEBUG)' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
for path in ['ios/CRMApp/AgendaViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/AgendaViewModel.kt','android/app/src/main/java/kz/zani/mobile/ui/AgendaScreen.kt']:
 assert '2026-10-28' not in (root/path).read_text(), 'Fixture day leaked into production view state: '+path
assert not list(root.rglob('*.env')) and not (root/'package.json').exists()
# Complete synthetic query producer data, deliberately separate from the
# bounded Directory response. Not a wire response or real permission grant.
for business,first in [(101,1701),(202,2701)]:
 catalogue=json.loads((f/f'client-search-catalogue-{business}.json').read_text())
 rows=catalogue['items'];original=json.loads((f/f'clients-{business}.json').read_text())['items']
 assert catalogue['business']==business and catalogue['fixture_only'] and len(rows)==54+len(original)
 assert len({r['id'] for r in rows})==len(rows)
 assert rows==sorted(rows,key=lambda r:(r.get('updated_at',''),r['id']),reverse=True)
 assert not any(r['id']==first for r in original)
 assert not any(r['id']==first for r in rows[:50])
 assert [r['id'] for r in rows if 'Beyond' in r['title']]==[first]
 assert [r['id'] for r in rows if 'fixture-note-tag' in r.get('notes','')]==[first+1]
 assert all(isinstance(r['title'],str) and isinstance(r.get('notes',''),str) for r in rows)
# QuickReplyTemplateSerializer/DRF fixture pages. No new HTTP/native route.
for business in [101,202]:
 for channel in ['website','telegram','whatsapp','instagram']:
  page=json.loads((f/f'quick-replies-{business}-{channel}.json').read_text());rows=page['results']
  assert page['count']==len(rows) and page['next'] is None and page['previous'] is None
  assert len({r['id'] for r in rows})==len(rows)
  assert rows==sorted(rows,key=lambda r:(r['sort_order'],r['title']))
  assert all(r['business']==business and r['is_active'] is True and r['channel'] in ['all',channel] and r['sort_order']>=0 and r['text'].strip() for r in rows)
  assert all(set(['id','business','title','text','category','channel','sort_order','is_active','created_at','updated_at'])==set(r) for r in rows)
assert 'FixtureQuickReplyRepository' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'FixtureQuickReplyRepository' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
assert '/api/quick-replies/' not in (root/'ios/Sources/CRMCore/NativeRequestBuilder.swift').read_text()
assert '/api/quick-replies/' not in (root/'android/app/src/main/java/kz/zani/mobile/data/NativeRequestBuilder.kt').read_text()
# Mark-read fake command data is separate from GET, with explicitly pinned outcome data.
mark_read=json.loads((f/'notification-mark-read.json').read_text())
assert mark_read['fixture_only'] is True and len(mark_read['validation_cases'])==20
assert len({r['name'] for r in mark_read['validation_cases']})==20
for scenario in mark_read['scenarios']:
 grant=scenario['grant']; business=grant['business']
 assert type(grant['update']) is bool and grant['update'] is True and grant['actor']>0
 source_page=json.loads((f/f'notifications-{business}.json').read_text())
 source=next(n for n in source_page['items'] if n['id']==grant['notification'])
 if scenario['outcome']=='response':
  response=scenario['reply']; assert response['ok'] is True and type(response['replayed']) is bool
  assert set(response)=={'ok','notification','replayed'}
  returned=response['notification']; assert returned['read_at'] is not None
  assert {k:v for k,v in returned.items() if k!='read_at'}=={k:v for k,v in source.items() if k!='read_at'}
 else: assert scenario['outcome']=='unknown' and 'reply' not in scenario
for row in mark_read['validation_cases']:
 assert type(row['status']) is int and type(row['decode']) is bool and type(row['confirmed']) is bool
 assert row['source']['id']==2101 and 'read_at' in row['source']
 assert not row['confirmed'] or row['decode']
# Completion uses a separate fake web-action catalogue, never the GET projection.
completion=json.loads((f/'task-complete-outcome.json').read_text())
assert completion['fixture_only'] is True and len(completion['scenarios'])==3
assert len(completion['validation_cases'])==18 and len({r['name'] for r in completion['validation_cases']})==18
assert {r['outcome'] for r in completion['scenarios']}=={'response','unknown','rejected_without_write'}
for row in completion['scenarios']:
 g=row['grant'];assert g['business'] in [101,202] and type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task'] and original['task']['status'] in ['open','in_progress']
 assert 'completed_by' not in original['task'] and 'completed_at' not in original['task']
 if row['outcome']=='response':
  r=row['response'];assert r['business']==g['business'] and r['id']==g['task'] and r['completed_by']==g['actor'] and r['status']=='done' and 'snoozed_until' in r and r['snoozed_until'] is None
 else:assert row['response'] is None
assert [r['name'] for r in completion['validation_cases'] if r['expected']=='confirmed']==['source_complete200']
for key in ['taskCompleteAction','taskCompleteFakeSubmit','taskCompleteFakeConfirmed','taskCompleteFakeRejected','taskCompleteFakeUnknown']:assert key in expected
self_assign=json.loads((f/'task-self-assign-outcome.json').read_text())
assert self_assign['fixture_only'] is True and len(self_assign['scenarios'])==3
assert len(self_assign['validation_cases'])==18 and len({r['name'] for r in self_assign['validation_cases']})==18
assert {r['outcome'] for r in self_assign['scenarios']}=={'response','unknown','rejected_without_write'}
for row in self_assign['scenarios']:
 g=row['grant'];assert g['business'] in [101,202] and type(g['update']) is bool and g['update'] is True and type(g['active_member']) is bool and g['active_member'] is True and type(g['actor']) is int and g['actor']>0
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task'] and original['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':
  r=row['response'];assert r['business']==g['business'] and r['id']==g['task'] and r['assignee']==g['actor'] and r['status']=='in_progress' and type(r['updated_at']) is str
  assert 'assignee_id' not in r
 else:assert row['response'] is None
assert [r['name'] for r in self_assign['validation_cases'] if r['expected']=='confirmed']==['source_assign_self200']
for key in ['taskSelfAssignAction','taskSelfAssignFakeSubmit','taskSelfAssignFakeConfirmed','taskSelfAssignFakeRejected','taskSelfAssignFakeUnknown']:assert key in expected
start=json.loads((f/'task-start-outcome.json').read_text())
assert start['fixture_only'] is True and len(start['scenarios'])==3
assert len(start['validation_cases'])==22 and len({r['name'] for r in start['validation_cases']})==22
assert {r['outcome'] for r in start['scenarios']}=={'response','unknown','rejected_without_write'}
for row in start['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task'] and original['task']['status']=='open'
 if row['outcome']=='response':
  r=row['response'];assert r['business']==g['business'] and r['id']==g['task'] and r['status']=='in_progress' and 'assignee' in r and r['assignee'] is None and original['details']['assignee'] is None and 'actor' not in r
 else:assert row['response'] is None
assert {r['name'] for r in start['validation_cases'] if r['expected']=='confirmed'}=={'source_start200_unassigned_stays_null','known_assignee_stays_not_actor'}
for key in ['taskStartAction','taskStartFakeSubmit','taskStartFakeConfirmed','taskStartFakeRejected','taskStartFakeUnknown','taskActionRetained']:assert key in expected
reopen=json.loads((f/'task-reopen-outcome.json').read_text())
assert reopen['fixture_only'] is True and len(reopen['scenarios'])==3
assert len(reopen['validation_cases'])==38 and len({r['name'] for r in reopen['validation_cases']})==38
assert {r['outcome'] for r in reopen['scenarios']}=={'response','unknown','rejected_without_write'}
for row in reopen['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task']
 if row['outcome']=='response':
  r=row['response'];assert original['task']['status'] in ['done','cancelled'] and r['id']==g['task'] and r['business']==g['business'] and r['status']=='open' and r['assignee'] is None and original['details']['assignee'] is None
  assert all(k in r and r[k] is None for k in ['completed_at','completed_by','cancelled_at','cancelled_by']) and r['cancel_reason']=='' and 'actor' not in r
 else:assert row['response'] is None
assert {r['name'] for r in reopen['validation_cases'] if r['expected']=='confirmed'}=={'source_reopen200_unassigned_stays_null','known_assignee_stays_not_actor'}
for key in ['taskReopenAction','taskReopenFakeSubmit','taskReopenFakeConfirmed','taskReopenFakeRejected','taskReopenFakeUnknown','taskReopenClearsMetadata']:assert key in expected
files=json.loads((f/'task-file-metadata.json').read_text())
assert files['fixture_only'] is True and len(files['scenarios'])==3
assert len(files['validation_cases'])==37 and len({c['name'] for c in files['validation_cases']})==37
for row in files['scenarios']:
 source=json.loads((f/('task-%s-%s.json'%(row['business'],row['task']))).read_text());assert source['business']==row['business'] and source['task']['id']==row['task']
 assert len({r['id'] for r in row['items']})==len(row['items'])
 for r in row['items']:assert r['business']==row['business'] and r['entity_type']=='task' and type(r['entity_id']) is str and r['entity_id']==str(row['task']) and r['visibility']=='private' and type(r['size']) is int and r['size']>=0 and 'scan_status' not in r and 'file' not in r
for key in ['taskFileMetadata','fileMetadataLoad','fileMetadataWindow','fileVerificationUnknown','fileOriginalName','fileContentType','fileSizeBytes','fileCreatedAt','fileMetadataReadFailed','fileMetadataEmpty']:assert key in expected
watcher=json.loads((f/'task-watcher-outcome.json').read_text())
assert watcher['fixture_only'] is True and len(watcher['scenarios'])==3
assert len(watcher['validation_cases'])==33 and len({c['name'] for c in watcher['validation_cases']})==33
for row in watcher['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['active_member']) is bool and g['active_member'] is True and type(g['actor']) is int and g['actor']>0
 source=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text());assert source['task']['status'] in ['open','in_progress'] and source['business']==g['business']
 if row['outcome']=='response':
  r=row['response'];assert r['id']==g['task'] and r['business']==g['business'] and r['status']==source['task']['status'] and g['actor'] in r['watchers'] and len(set(r['watchers']))==len(r['watchers']) and all(type(x) is int and x>0 for x in r['watchers']) and 'actor' not in r
 else:assert row['response'] is None
for key in ['taskWatcherAction','taskWatcherFakeSubmit','taskWatcherFakeConfirmed','taskWatcherFakeRejected','taskWatcherFakeUnknown','taskWatcherContract']:assert key in expected
undo=json.loads((f/'task-undo-cancel-outcome.json').read_text())
assert undo['fixture_only'] is True and len(undo['scenarios'])==3
assert len(undo['validation_cases'])==39 and len({r['name'] for r in undo['validation_cases']})==39
profile=json.loads((f/'task-101-3167.json').read_text());catalogue=json.loads((f/'task-query-source-101.json').read_text())
assert profile==catalogue['profiles']['3167'] and profile['task']['status']=='cancelled' and any(t['id']==3167 for t in catalogue['queries']['cancelled|']['items'])
for row in undo['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 assert all(k not in g for k in ['target_status','audit_id','version','key'])
 if row['outcome']=='response':
  r=row['response'];assert r['id']==g['task'] and r['business']==g['business'] and r['status'] in ['open','in_progress','done'] and r['cancelled_at'] is None and r['cancelled_by'] is None and r['cancel_reason']=='' and 'completed_at' in r and 'completed_by' in r
 else:assert row['response'] is None
for key in ['taskUndoCancelAction','taskUndoCancelFakeSubmit','taskUndoCancelFakeConfirmed','taskUndoCancelFakeRejected','taskUndoCancelFakeUnknown','taskUndoCancelContract','taskUndoCancelCompletionAt']:assert key in expected

relative=json.loads((f/'relative-appointment-candidate.json').read_text())
assert relative['fixture_only'] is True
for row in relative['parse_cases']:
 raw=row['raw'];m=re.fullmatch(r'/app/calendar(?:\?appointment=([1-9][0-9]*)|/([1-9][0-9]*)/?)',raw)
 digits=next((x for x in m.groups() if x),None) if m else None
 candidate=digits if digits is not None and int(digits)<=9223372036854775807 else None
 assert row['candidate_id']==candidate,row['name']
for row in relative['corroboration_cases']:
 s=row['source'];target=s.get('appointment_id')
 if row['target'] is not None:assert type(target) is int and target>0 and row['target']==target and s['action_url'] in [f'/app/calendar?appointment={target}',f'/app/calendar/{target}',f'/app/calendar/{target}/']
for key in ['relativeRouteCheck','relativeRouteInput','relativeRouteReview','relativeRouteUnsupported','relativeRouteUntrusted','relativeRouteMatched']:assert key in expected

unread=json.loads((f/'notification-mark-unread.json').read_text())
assert unread['fixture_only'] is True and len(unread['scenarios'])==3
assert {r['outcome'] for r in unread['scenarios']}=={'response','unknown','rejected_without_write'}
for row in unread['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0
 original=next(x for x in json.loads((f/('notifications-%s.json'%g['business'])).read_text())['items'] if x['id']==g['notification'])
 if row['outcome']=='response':
  r=row['reply'];assert r['id']==original['id'] and r['business']==g['business'] and r['read_at'] is None and r['is_read'] is False and r['appointment']==original['appointment_id'] and 'ok' not in r and 'replayed' not in r
 else:assert row['reply'] is None
assert len({r['name'] for r in unread['validation_cases']})==len(unread['validation_cases'])
for key in ['notificationFakeUnreadPrepare','notificationFakeUnreadReview','notificationFakeUnreadSubmit','notificationFakeUnreadConfirmed','notificationFakeUnreadRejected','notificationFakeUnreadUnknown','notificationFakeUnreadEdit']:assert key in expected

# Independent stdlib calendar oracle for explicitly supported local snooze inputs.
# This checks fixture/source consistency only; it does not execute native code.
import datetime
snooze=json.loads((f/'task-snooze-outcome.json').read_text())
assert snooze['fixture_only'] is True and len(snooze['input_cases'])==49 and len(snooze['validation_cases'])==32
for row in snooze['input_cases']:
 raw=row['raw'];m=re.fullmatch(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})',raw);value=None
 if m and m.group(8)!='-00:00':
  try:
   parts=list(map(int,m.groups()[:6]));frac=int((m.group(7) or '').ljust(6,'0'));zone=m.group(8);offset=0
   if zone!='Z':
    oh,om=int(zone[1:3]),int(zone[4:6]);assert oh<24 and om<60
    offset=(oh*3600+om*60)*(1 if zone[0]=='+' else -1)
   utc=datetime.datetime(*parts,microsecond=frac)-datetime.timedelta(seconds=offset);delta=utc-datetime.datetime(1970,1,1)
   value=(delta.days*86400+delta.seconds)*1000000+delta.microseconds
  except (ValueError,OverflowError,AssertionError):pass
 assert row['microseconds']==value,row['name']
assert len({row['name'] for row in snooze['input_cases']})==49 and len({row['name'] for row in snooze['validation_cases']})==32
for row in snooze['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task'] and original['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':
  r=row['response'];assert r['id']==g['task'] and r['business']==g['business'] and r['status']==original['task']['status'] and r['due_at']==original['task']['due_at'] and r['reminder_at']==original['details']['reminder_at'] and 'actor' not in r
 else:assert row['response'] is None
for key in ['taskSnoozeAction','taskSnoozeInput','taskSnoozeInputIssue','taskSnoozeFakeSubmit','taskSnoozeFakeConfirmed','taskSnoozeFakeRejected','taskSnoozeFakeUnknown','taskSnoozeContract','taskSnoozeReturned']:assert key in expected
# Every literal copy key used by the new native content must exist in all dictionaries.
for file in ['ios/CRMApp/TaskSnoozeView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskSnoozeContent.kt']:
 text=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',text):assert key in expected,(file,key)
# Explicit assignment: selected target context is synthetic, not a member API or GET grant.
assignment=json.loads((f/'task-assign-outcome.json').read_text())
assert assignment['fixture_only'] is True and len(assignment['input_cases'])==20 and len(assignment['validation_cases'])==30
for row in assignment['input_cases']:
 raw=row['raw'];expected_id=int(raw) if re.fullmatch(r'[1-9][0-9]*',raw) and int(raw)<=9223372036854775807 else None
 assert row['user_id']==expected_id,row['name']
for row in assignment['scenarios']:
 g=row['grant'];assert type(g['actor']) is int and g['actor']>0 and type(g['update']) is bool and g['update'] is True
 members=g['eligible_members'];assert len(members)>0 and len(set(members))==len(members) and all(type(i) is int and 0<i<=9223372036854775807 for i in members)
 original=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text())
 assert original['business']==g['business'] and original['task']['id']==g['task'] and original['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':
  r=row['response'];assert r['id']==g['task'] and r['business']==g['business'] and r['status']==original['task']['status'] and r['assignee'] in members and type(r['assignee']) is int and 'eligible_members' not in r and 'actor' not in r and 'user_id' not in r
 else:assert row['response'] is None
assert len({row['name'] for row in assignment['input_cases']})==20 and len({row['name'] for row in assignment['validation_cases']})==30
for key in ['taskAssignAction','taskAssignInput','taskAssignInputIssue','taskAssignSyntheticMembers','taskAssignFakeSubmit','taskAssignFakeConfirmed','taskAssignFakeRejected','taskAssignFakeUnknown','taskAssignContract','taskAssignReturned']:assert key in expected
for file in ['ios/CRMApp/TaskAssignView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskAssignContent.kt']:
 content=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',content):assert key in expected,(file,key)
# One-selected-date partial body: independent datetime oracle and exact omitted-field proof.
dates=json.loads((f/'task-date-partial-outcome.json').read_text())
assert dates['fixture_only'] is True and len(dates['input_cases'])==18 and len(dates['validation_cases'])==35
def explicit_date_value(raw):
 if type(raw) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})',raw) or raw.endswith('-00:00'):return None
 try:return datetime.datetime.fromisoformat(raw.replace('Z','+00:00')).astimezone(datetime.timezone.utc)
 except (ValueError,OverflowError):return None
for row in dates['input_cases']:
 field=row['field'];assert field in ['due_at','reminder_at'] and row['mode'] in ['set','clear']
 expected_body={field:None} if row['mode']=='clear' else {field:row['raw']} if explicit_date_value(row['raw']) is not None else None
 assert row['expected_body']==expected_body,row['name']
 if expected_body is not None:assert set(expected_body)=={field} and len(expected_body)==1 and not {'description','title','assignee','status','snoozed_until','expected_updated_at','idempotency_key'} & set(expected_body)
for row in dates['validation_cases']:
 r=row['response'];field=row['field'];confirmed=type(r) is dict and row['status']==200 and type(r.get('id')) is int and r['id']==1101 and type(r.get('business')) is int and r['business']==101 and r.get('status')==row['source_status'] and field in r and explicit_date_value(r.get('updated_at')) is not None
 if confirmed:
  confirmed=r[field] is None if row['mode']=='clear' else explicit_date_value(r[field]) is not None and explicit_date_value(r[field])==explicit_date_value(row['raw'])
 assert (row['expected']=='confirmed')==confirmed,row['name']
for row in dates['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 source=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text());assert source['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':assert row['response']['id']==g['task'] and row['response']['business']==g['business'] and row['response']['due_at']==source['task']['due_at'] and row['response']['reminder_at']==source['details']['reminder_at']
 else:assert row['response'] is None
for key in ['taskDateAction','taskDateChooseField','taskDateSet','taskDateRemove','taskDateInputIssue','taskDateFakeSubmit','taskDateFakeConfirmed','taskDateFakeRejected','taskDateFakeUnknown','taskDateContract','taskDateReturned']:assert key in expected
for file in ['ios/CRMApp/TaskDateEditView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDateEditContent.kt']:
 content=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',content):assert key in expected,(file,key)
# Explicit one-priority partial update: independent finite-choice and result oracle.
priority_edit=json.loads((f/'task-priority-partial-outcome.json').read_text())
assert priority_edit['fixture_only'] is True and len(priority_edit['input_cases'])==16 and len(priority_edit['validation_cases'])==34
priority_choices=['low','normal','high','urgent']
for row in priority_edit['input_cases']:
 assert row['expected_body']==({'priority':row['raw']} if row['raw'] in priority_choices else None),row['name']
for row in priority_edit['validation_cases']:
 r=row['response'];yes=type(r) is dict and row['status']==200 and type(r.get('id')) is int and r['id']==1101 and type(r.get('business')) is int and r['business']==101 and r.get('status')==row['source_status'] and type(r.get('priority')) is str and r['priority'] in priority_choices and r['priority']==row['selected'] and explicit_date_value(r.get('updated_at')) is not None
 assert yes==(row['expected']=='confirmed'),row['name']
for row in priority_edit['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 source=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text());assert source['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':assert row['response']['id']==g['task'] and row['response']['business']==g['business'] and row['response']['status']==source['task']['status'] and row['response']['priority']==source['task']['priority']
 else:assert row['response'] is None
for key in ['taskPriorityEditAction','taskPriorityEditInputIssue','taskPriorityEditFakeSubmit','taskPriorityEditFakeConfirmed','taskPriorityEditFakeRejected','taskPriorityEditFakeUnknown','taskPriorityEditContract','taskPriorityEditReturned']:assert key in expected
for file in ['ios/CRMApp/TaskPriorityEditView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskPriorityEditContent.kt']:
 content=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',content):assert key in expected,(file,key)
# Source composition checks; not an execution or semantic replacement for native tests.
for file in ['ios/CRMApp/TaskListViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskListViewModel.kt']:
 content=(root/file).read_text();lines=content.splitlines()
 for peer in ['completion','selfAssignment','start','reopen','watcher','undoCancel','snooze','targetAssign','dateEdit']:
  line=next(l for l in lines if ('func '+peer+'Current(' in l or 'fun '+peer+'Current(' in l));assert 'priorityEditBarrier' in line and 'priorityEdit?.ownsEditor' in line,(file,peer)
 hidden=next(l for l in lines if 'hasHiddenRetainedAction' in l);assert 'priorityEdit?.blocks(' in hidden and 'priorityEdit?.submission' in hidden
 assert 'openPriorityEdit(' in content and 'priorityEditSubmission' in content
 for method in ['openDateEdit','openTargetAssign','openSnooze','prepareUndoCancel','prepareWatcher','prepareReopen','prepareStart','prepareCompletion','prepareSelfAssignment']:
  line=next(l for l in lines if ('func '+method+'(' in l or 'fun '+method+'(' in l));assert 'priorityEdit?.interrupt()' in line,(file,method)
# Existing-supported native title-only subset; independent Python scalar/strip oracle.
# This is source/fixture verification, not installed DRF or native execution.
title_edit=json.loads((f/'task-title-partial-outcome.json').read_text())
assert title_edit['fixture_only'] is True and len(title_edit['input_cases'])==25 and len(title_edit['validation_cases'])==43
js_title_space='\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'
def supported_title(raw):
 v=raw.strip(js_title_space).strip()
 return v if v and len(v)<=255 and not any(ord(c)==0 or 0xd800<=ord(c)<=0xdfff for c in v) else None
for row in title_edit['input_cases']:
 v=supported_title(row['raw']);assert row['title']==v and row['expected_body']==({'title':v} if v is not None else None),row['name']
for row in title_edit['validation_cases']:
 r=row['response'];v=supported_title(row['raw']);yes=type(r) is dict and row['status']==200 and type(r.get('id')) is int and r['id']==1101 and type(r.get('business')) is int and r['business']==101 and r.get('status')==row['source_status'] and type(r.get('title')) is str and r['title']==v and explicit_date_value(r.get('updated_at')) is not None
 assert yes==(row['expected']=='confirmed'),row['name']
for row in title_edit['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 source=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text());assert source['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':assert row['response']['id']==g['task'] and row['response']['business']==g['business'] and row['response']['status']==source['task']['status'] and row['response']['title']==source['task']['title']
 else:assert row['response'] is None
for key in ['taskTitleEditAction','taskTitleEditInputIssue','taskTitleEditFakeSubmit','taskTitleEditFakeConfirmed','taskTitleEditFakeRejected','taskTitleEditFakeUnknown','taskTitleEditContract','taskTitleEditReturned','taskTitleEditRaw','taskTitleEditProposed']:assert key in expected
for file in ['ios/CRMApp/TaskTitleEditView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskTitleEditContent.kt']:
 content=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',content):assert key in expected,(file,key)
for file in ['ios/CRMApp/TaskListViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskListViewModel.kt']:
 content=(root/file).read_text();lines=content.splitlines()
 for peer in ['completion','selfAssignment','start','reopen','watcher','undoCancel','snooze','targetAssign','dateEdit','priorityEdit']:
  line=next(l for l in lines if ('func '+peer+'Current(' in l or 'fun '+peer+'Current(' in l));assert 'titleEditBarrier' in line and 'titleEdit?.ownsEditor' in line,(file,peer)
 hidden=next(l for l in lines if 'hasHiddenRetainedAction' in l);assert 'titleEdit?.blocks(' in hidden and 'titleEdit?.submission' in hidden
 assert 'openTitleEdit(' in content and 'titleEditSubmission' in content
 for method in ['openDateEdit','openTargetAssign','openSnooze','openPriorityEdit','prepareUndoCancel','prepareWatcher','prepareReopen','prepareStart','prepareCompletion','prepareSelfAssignment']:
  line=next(l for l in lines if ('func '+method+'(' in l or 'fun '+method+'(' in l));assert 'titleEdit?.interrupt()' in line,(file,method)
# Explicit full-description replacement/clear supported native subset, no excerpt roundtrip.
description_edit=json.loads((f/'task-description-replace-outcome.json').read_text())
assert description_edit['fixture_only'] is True and len(description_edit['input_cases'])==16 and len(description_edit['validation_cases'])==36
def replacement_description(mode,raw):
 if mode=='clear':return ''
 v=raw.strip()
 return v if mode=='replace' and v and not any(ord(c)==0 or 0xd800<=ord(c)<=0xdfff for c in v) else None
for row in description_edit['input_cases']:
 v=replacement_description(row['mode'],row['raw']);assert row['value']==v and row['expected_body']==({'description':v} if v is not None else None),row['name']
for row in description_edit['validation_cases']:
 r=row['response'];v=replacement_description(row['mode'],row['raw']);yes=type(r) is dict and row['status']==200 and type(r.get('id')) is int and r['id']==1101 and type(r.get('business')) is int and r['business']==101 and r.get('status')==row['source_status'] and type(r.get('description')) is str and r['description']==v and explicit_date_value(r.get('updated_at')) is not None
 assert yes==(row['expected']=='confirmed'),row['name']
for row in description_edit['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] is True and type(g['actor']) is int and g['actor']>0 and 'active_member' not in g
 source=json.loads((f/('task-%s-%s.json'%(g['business'],g['task']))).read_text());assert source['task']['status'] in ['open','in_progress']
 if row['outcome']=='response':assert row['response']['id']==g['task'] and row['response']['business']==g['business'] and row['response']['status']==source['task']['status'] and type(row['response']['description']) is str
 else:assert row['response'] is None
for key in ['taskDescriptionEditAction','taskDescriptionEditInputIssue','taskDescriptionEditFakeSubmit','taskDescriptionEditFakeConfirmed','taskDescriptionEditFakeRejected','taskDescriptionEditFakeUnknown','taskDescriptionEditContract','taskDescriptionEditReturned','taskDescriptionEditRaw','taskDescriptionEditProposed','taskDescriptionEditReplace','taskDescriptionEditRemove']:assert key in expected
for file in ['ios/CRMApp/TaskDescriptionEditView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDescriptionEditContent.kt']:
 content=(root/file).read_text()
 for key in re.findall(r'(?:AppCopy\.text|text)\("([A-Za-z0-9]+)"\)',content):assert key in expected,(file,key)
for file in ['ios/CRMApp/TaskListViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskListViewModel.kt']:
 content=(root/file).read_text();lines=content.splitlines()
 for peer in ['completion','selfAssignment','start','reopen','watcher','undoCancel','snooze','targetAssign','dateEdit','priorityEdit','titleEdit']:
  line=next(l for l in lines if ('func '+peer+'Current(' in l or 'fun '+peer+'Current(' in l));assert 'descriptionEditBarrier' in line and 'descriptionEdit?.ownsEditor' in line,(file,peer)
 hidden=next(l for l in lines if 'hasHiddenRetainedAction' in l);assert 'descriptionEdit?.blocks(' in hidden and 'descriptionEdit?.submission' in hidden
 assert 'openDescriptionEdit(' in content and 'descriptionEditSubmission' in content
 for method in ['openDateEdit','openTargetAssign','openSnooze','openPriorityEdit','openTitleEdit','prepareUndoCancel','prepareWatcher','prepareReopen','prepareStart','prepareCompletion','prepareSelfAssignment']:
  line=next(l for l in lines if ('func '+method+'(' in l or 'fun '+method+'(' in l));assert 'descriptionEdit?.interrupt()' in line,(file,method)
# Existing create exact raw/preview/result semantics; no Unicode canonical conversion.
create_exact=json.loads((f/'task-create-exact-text.json').read_text())
assert create_exact['fixture_only'] is True and len(create_exact['cases'])==18 and len(create_exact['snapshot_cases'])==4
for row in create_exact['cases']:
 raw=row['raw'];v={'title':raw['title'].strip(js_title_space).strip(),'description':raw['description'].strip(),'priority':raw['priority']};assert row['preview']==v
 r=row['response'];yes=row['status']==201 and type(r.get('id')) is int and r['id']>0 and r.get('business')==101 and r.get('created_by')==9001 and r.get('status')=='open' and all(type(r.get(k)) is str and r[k]==v[k] for k in v) and explicit_date_value(r.get('created_at')) is not None and explicit_date_value(r.get('updated_at')) is not None
 assert yes==(row['expected']=='confirmed'),row['name']
for row in create_exact['snapshot_cases']:
 a,b=row['left'],row['right'];assert (a==b)==row['raw_equal']
 def p(v):return (v['title'].strip(js_title_space).strip(),v['description'].strip(),v['priority'])
 assert (p(a)==p(b))==row['preview_equal'],row['name']
create_source=(root/'ios/Sources/CRMCore/TaskCreation.swift').read_text();assert 'task.title.map({$0.utf8.elementsEqual(value.title.utf8)})==true' in create_source and 'task.description.map({$0.utf8.elementsEqual(value.description.utf8)})==true' in create_source
for struct in ['TaskDraftValues','TaskDraftPreview']:
 part=(root/'ios/Sources/CRMCore/TaskDraft.swift').read_text().split('public struct '+struct+':',1)[1].split('public struct ',1)[0];assert 'public static func ==(lhs:Self,rhs:Self)' in part and 'lhs.title.utf8.elementsEqual(rhs.title.utf8)' in part and 'lhs.description.utf8.elementsEqual(rhs.description.utf8)' in part
# Optional create due_at is a set/omitted field, never null-clear/default-date proof.
create_due=json.loads((f/'task-create-due-at.json').read_text())
assert create_due['fixture_only'] is True and len(create_due['input_cases'])==13 and len(create_due['validation_cases'])==19
for row in create_due['input_cases']:
 valid=row['mode']=='omit' or explicit_date_value(row['raw']) is not None;body={'business':101,'title':'Task','description':'Note','priority':'normal'}
 if row['mode']=='setDate':body['due_at']=row['raw']
 assert valid==row['valid'] and row['expected_body']==(body if valid else None),row['name']
for row in create_due['validation_cases']:
 r=row['response'];date_ok=row['mode']=='omit' or explicit_date_value(r.get('due_at')) is not None and explicit_date_value(r['due_at'])==explicit_date_value(row['raw'])
 yes=row['status']==201 and type(r.get('id')) is int and r['id']>0 and r.get('business')==101 and r.get('created_by')==9001 and r.get('status')=='open' and r.get('title')=='Task' and r.get('description')=='Note' and r.get('priority')=='normal' and explicit_date_value(r.get('created_at')) is not None and explicit_date_value(r.get('updated_at')) is not None and date_ok
 assert yes==(row['expected']=='confirmed'),row['name']
for key in ['taskCreateDueOmit','taskCreateDueSet']:assert key in expected
for file in ['ios/CRMApp/TaskDraftScreen.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftContent.kt']:
 content=(root/file).read_text();assert 'taskCreateDueOmit' in content and 'taskCreateDueSet' in content and 'chooseDue' in content and 'dueAt' in content
for file in ['ios/Sources/CRMCore/TaskCreation.swift','android/app/src/main/java/kz/zani/mobile/core/TaskCreation.kt']:
 content=(root/file).read_text();assert 'preparedBody' in content and '.dueDate.matches(' in content and 'due_at' in content
# Independent optional reminder, create-only selected reply evidence, same whole form.
create_reminder=json.loads((f/'task-create-reminder.json').read_text())
assert create_reminder['fixture_only'] is True and len(create_reminder['input_cases'])==13 and len(create_reminder['validation_cases'])==24
for row in create_reminder['input_cases']:
 body={'business':101,'title':'Task','description':'Note','priority':'normal'};valid=True
 for prefix,key in [('due','due_at'),('reminder','reminder_at')]:
  if row[prefix+'_mode']=='setDate':valid=valid and explicit_date_value(row[prefix+'_raw']) is not None;body[key]=row[prefix+'_raw']
 assert row['valid']==valid and row['expected_body']==(body if valid else None),row['name']
for row in create_reminder['validation_cases']:
 r=row['response'];date_ok=True
 for prefix,key in [('due','due_at'),('reminder','reminder_at')]:
  if row[prefix+'_mode']=='setDate':date_ok=date_ok and (prefix!='reminder' or row['include_evidence']) and explicit_date_value(r.get(key)) is not None and explicit_date_value(r[key])==explicit_date_value(row[prefix+'_raw'])
 yes=row['status']==201 and type(r.get('id')) is int and r['id']>0 and r.get('business')==101 and r.get('created_by')==9001 and r.get('status')=='open' and r.get('title')=='Task' and r.get('description')=='Note' and r.get('priority')=='normal' and explicit_date_value(r.get('created_at')) is not None and explicit_date_value(r.get('updated_at')) is not None and date_ok
 assert yes==(row['expected']=='confirmed'),row['name']
for key in ['taskCreateReminderOmit','taskCreateReminderSet','taskCreateReminderReturned']:assert key in expected
for file in ['ios/CRMApp/TaskDraftScreen.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftContent.kt']:
 content=(root/file).read_text();assert 'chooseReminder' in content and 'taskCreateReminderOmit' in content and 'taskCreateReminderSet' in content and 'taskCreateReminderReturned' in content
for file in ['ios/Sources/CRMCore/TaskCreation.swift','android/app/src/main/java/kz/zani/mobile/core/TaskCreation.kt']:
 content=(root/file).read_text();assert 'reminderDate.matches(' in content and 'reminderAt' in content and 'reminder_at' in content
# Source composition does not add reminder evidence to bounded/general WorkTask GET models.
for file in ['ios/Sources/CRMCore/Models.swift','android/app/src/main/java/kz/zani/mobile/core/Models.kt']:
 content=(root/file).read_text();part=content.split('struct WorkTask',1)[-1] if 'struct WorkTask' in content else content.split('data class WorkTask',1)[-1];part=part.split('\n}',1)[0];assert 'reminderAt' not in part and 'reminder_at' not in part,file
# Inbox manual exact raw/review foundation, not a SEND receipt or input500 cap.
reply_exact=json.loads((f/'reply-draft-exact-text.json').read_text())
assert reply_exact['fixture_only'] is True and len(reply_exact['cases'])==11 and len(reply_exact['snapshot_cases'])==5
for row in reply_exact['cases']:
 assert row['text']==row['raw'].strip() and row['valid']==bool(row['text']) and row['codepoints']==len(row['text']),row['name']
for row in reply_exact['snapshot_cases']:
 assert row['text_equal']==(row['left'].strip()==row['right'].strip()) and row['review_equal']==(row['left']==row['right']),row['name']
reply_source=(root/'ios/Sources/CRMCore/ReplyDraft.swift').read_text();assert 'public let raw:String' in reply_source and 'lhs.raw.utf8.elementsEqual(rhs.raw.utf8)' in reply_source and 'raw:text)' in reply_source
reply_vm=(root/'ios/CRMApp/ReplyDraftViewModel.swift').read_text();assert '!session.text.utf8.elementsEqual(before.utf8)' in reply_vm
# Existing reply request-shaped fake lane and independent bounded receipt oracle.
reply_result=json.loads((f/'inbox-reply-outcome.json').read_text())
assert reply_result['fixture_only'] is True and len(reply_result['validation_cases'])==41 and len(reply_result['scenarios'])==5
def reply_receipt_matches(row):
 r=row['response'];text=row['raw'].strip()
 if row['status']!=200 or type(r) is not dict or r.get('ok') is not True or type(r.get('replayed')) is not bool:return False
 c=r.get('conversation');m=r.get('message')
 if type(c) is not dict or type(m) is not dict:return False
 if any(type(v) is not int or not 1<=v<=2147483647 for v in [c.get('id'),m.get('conversation_id'),m.get('id')]):return False
 if c['id']!=901 or m['conversation_id']!=901 or m.get('direction')!='outbound' or m.get('sender_type')!='manager':return False
 if type(m.get('text')) is not str or m['text']!=text or len(text)>500 or any(0xd800<=ord(v)<=0xdfff for v in m['text']):return False
 status=m.get('status')
 if status not in ['queued','sent','failed'] or explicit_date_value(m.get('created_at')) is None or 'sent_at' not in m:return False
 sent=m['sent_at']
 return (status=='sent' and explicit_date_value(sent) is not None) or (status!='sent' and sent is None)
for row in reply_result['validation_cases']:assert reply_receipt_matches(row)==(row['expected']=='confirmed'),row['name']
for row in reply_result['scenarios']:
 g=row['grant'];assert type(g['update']) is bool and g['update'] and type(g['actor']) is int and g['actor']>0 and g['keys'] and len(set(g['keys']))==len(g['keys']) and all(type(k) is str and k and k==k.strip() for k in g['keys'])
 source=json.loads((f/('inbox-%s-%s.json'%(g['business'],g['conversation']))).read_text());assert source['conversation']['id']==g['conversation'] and source['details']['status']=='open'
 if row['outcome']=='response':assert row['response']['conversation']['id']==g['conversation'] and row['response']['message']['conversation_id']==g['conversation'] and row['response']['message']['status'] in ['queued','sent','failed']
 else:assert row['outcome'] in ['unknown','rejected_without_write'] and row['response'] is None
for key in ['inboxReplyFakeSubmit','inboxReplyFakeConfirmed','inboxReplyFakeRejected','inboxReplyFakeUnknown','inboxReplyTestUnavailable','inboxReplyReceipt','inboxReplyReceiptQueued','inboxReplyReceiptSent','inboxReplyReceiptFailed','inboxReplyReceiptReplayed','inboxReplyReceiptNew','inboxReplyNoDeliveryProof']:assert key in expected
for file in ['ios/CRMApp/InboxReplyReceiptView.swift','android/app/src/main/java/kz/zani/mobile/ui/InboxReplyReceiptContent.kt']:
 content=(root/file).read_text();assert 'record.attempt.review.text' in content and 'inboxReplyNoDeliveryProof' in content and 'acknowledge' in content and 'error_text' not in content
for file in ['ios/Sources/CRMCore/InboxReplySubmission.swift','android/app/src/main/java/kz/zani/mobile/core/InboxReplySubmission.kt']:
 content=(root/file).read_text()
 for token in ['Idempotency-Key','preparedBody','preparedHeaders','usedKeys','canBegin','blocked','rejectedWithoutWrite' if file.endswith('.swift') else 'RejectedWithoutWrite']:assert token in content,(file,token)
 for token in ['URLSession','HttpURLConnection','OkHttp','expected_updated_at','error_text','UUID','Random','retryAfter','Timer']:assert token not in content,(file,token)
for file in ['ios/CRMApp/ReplyDraftViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/ReplyDraftModel.kt']:
 content=(root/file).read_text();assert 'submissionBlocked' in content and 'canSubmit' in content and 'ledger.begin' in content and 'ledger.complete' in content and 'attempt==attempt' in content
assert 'FixtureInboxReplyPort' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
android_composition=(root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text();assert 'FixtureInboxReplyPort' in android_composition and 'BuildConfig.DEBUG' in android_composition
assert 'InboxReplyReceiptView.swift' in (root/'ios/PlatformaCRM.xcodeproj/project.pbxproj').read_text() and 'InboxReplyReceiptView.swift' in (root/'scripts/check_swift_view_model.sh').read_text()
# Existing manual handoff direct saved-flag receipt; no AI return/time policy inferred.
handoff_result=json.loads((f/'inbox-handoff-outcome.json').read_text())
assert handoff_result['fixture_only'] is True and len(handoff_result['input_cases'])==13 and len(handoff_result['validation_cases'])==41 and len(handoff_result['review_pairs'])==4 and len(handoff_result['scenarios'])==3
for row in handoff_result['input_cases']:
 value=row['raw'].strip();valid=not any(ord(c)==0 or 0xd800<=ord(c)<=0xdfff for c in value)
 assert row['valid']==valid and row['reason']==(value if valid else None) and row['expected_body']==({'reason':value} if valid else None),row['name']
for row in handoff_result['review_pairs']:assert row['equal']==(row['left']==row['right']),row
for row in handoff_result['validation_cases']:
 r=row['response'];yes=row['status']==200 and type(r) is dict and type(r.get('id')) is int and r['id']==901 and type(r.get('business')) is int and r['business']==101 and r.get('handoff_required') is True and r.get('bot_enabled') is False and type(r.get('handoff_reason')) is str and r['handoff_reason']==row['raw'].strip() and explicit_date_value(r.get('updated_at')) is not None
 assert yes==(row['expected']=='confirmed'),row['name']
for row in handoff_result['scenarios']:
 g=row['grant'];assert g['update'] is True and type(g['actor']) is int and g['actor']>0 and set(g)=={'business','conversation','actor','update'}
 source=json.loads((f/('inbox-%s-%s.json'%(g['business'],g['conversation']))).read_text());assert source['business']==g['business'] and source['conversation']['id']==g['conversation']
 if row['outcome']=='response':assert row['response']['id']==g['conversation'] and row['response']['business']==g['business'] and row['response']['handoff_required'] is True and row['response']['bot_enabled'] is False
 else:assert row['response'] is None and row['outcome'] in ['unknown','rejected_without_write']
for key in ['handoffTestAction','handoffReason','handoffReasonOptional','handoffReasonIssue','handoffBlankReason','handoffLocalOnly','handoffNoReturnProof','handoffTestSubmit','handoffTestResult','handoffTestConfirmed','handoffTestRejected','handoffTestUnknown']:assert key in expected
for file in ['ios/Sources/CRMCore/InboxHandoff.swift','android/app/src/main/java/kz/zani/mobile/core/InboxHandoff.kt']:
 content=(root/file).read_text()
 for token in ['HandoffReason','HandoffReview','HandoffLedger','preparedHeaders','preparedBody','handoff_required','bot_enabled','handoff_reason','updated_at','/api/inbox/conversations/']:assert token in content,(file,token)
 for token in ['URLSession','HttpURLConnection','OkHttp','Idempotency-Key','expected_updated_at','Timer','retryAfter','UUID']:assert token not in content,(file,token)
for file in ['ios/CRMApp/InboxHandoffViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/InboxHandoffModel.kt']:
 content=(root/file).read_text()
 for token in ['clearConfirmation','contentRevision','blocked','canSubmit','ledger.begin','ledger.complete','attempt==attempt']:assert token in content,(file,token)
 assert 'sourceStatus' not in content,file
for file in ['ios/CRMApp/InboxHandoffView.swift','android/app/src/main/java/kz/zani/mobile/ui/InboxHandoffContent.kt']:
 content=(root/file).read_text();assert 'handoffLocalOnly' in content and 'handoffNoReturnProof' in content and 'handoffTestConfirmed' in content and 'error_text' not in content
for file in ['ios/CRMApp/InboxViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/InboxViewModel.kt']:
 content=(root/file).read_text();assert 'handoff.returnControl' in content and 'openHandoff' in content and 'handoff.blocks(context)' in content and 'handoff.pause()' in content and 'handoff.verified' in content
assert 'handoffSubmission:FixtureHandoffPort' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'FixtureHandoffPort(assets)' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
# Create receipts validate their selected fields without converting untouched GET due_at into evidence.
for file in ['ios/Sources/CRMCore/TaskCreation.swift','android/app/src/main/java/kz/zani/mobile/core/TaskCreation.kt']:
 content=(root/file).read_text();assert ('task.id>0' in content if file.endswith('.swift') else 't.id>0' in content) and 'dueDate.matches' in content and 'reminderDate.matches' in content
 assert 'task.valid,' not in content and 't.valid()' not in content
# Fixture-only original JSON texts preserve FEFF and numeric lexemes under native fixture loading.
for name in ['task-title-partial-outcome','task-description-replace-outcome','inbox-reply-outcome','inbox-handoff-outcome']:
 catalog=json.loads((f/(name+'.json')).read_text())
 for row in catalog.get('input_cases',[]):assert json.loads(row['raw_json'])==row['raw'] and json.loads(row['expected_body_json'])==row['expected_body']
 for row in catalog.get('validation_cases',[]):assert json.loads(row['raw_json'])==row['raw'] and json.loads(row['response_json'])==row['response']
 for row in catalog.get('review_pairs',[]):assert json.loads(row['left_json'])==row['left'] and json.loads(row['right_json'])==row['right']
# Source-defined Service/Resource reference detail identity, not catalogue/slot/booking authority.
reference=json.loads((f/'appointment-reference-read-cases.json').read_text())
assert reference['fixture_only'] is True and len(reference['cases'])==45 and len(reference['parent_cases'])==6
reference_types={'staff':'referenceTypeStaff','room':'referenceTypeRoom','hall':'referenceTypeHall','box':'referenceTypeBox','equipment':'referenceTypeEquipment','other':'referenceTypeOther'}
for row in reference['cases']:
 r=row['response'];yes=row['status']==200 and type(r) is dict and type(r.get('id')) is int and 0<r['id']<=2147483647 and r['id']==row['id'] and type(r.get('business')) is int and 0<r['business']<=2147483647 and r['business']==row['business'] and type(r.get('name')) is str
 assert row['valid']==yes and json.loads(row['response_json'])==r and json.loads(row['name_json'])==r.get('name'),row['name']
 active=r.get('is_active') if type(r.get('is_active')) is bool else None
 type_value=r.get('resource_type') if row['kind']=='resource' and type(r.get('resource_type')) is str else None
 assert row['active'] is active and row['resource_type']==type_value and row['type_key']==reference_types.get(type_value,'notAvailable'),row['name']
for row in reference['parent_cases']:
 for kind in ['service','resource']:assert row[kind+'_valid']==(type(row[kind]) is int and 0<row[kind]<=2147483647),row['name']
assert json.loads(reference['parent_202_variant_json'])==reference['parent_202_variant']
for kind,ids in [('service',[8001,8002]),('resource',[9001,9002])]:
 for id in ids:
  record=json.loads((f/(kind+'-reference-'+str(id)+'.json')).read_text());assert record['id']==id and record['business']==(101 if id in [8001,9001] else 202) and type(record['is_active']) is bool
for key in ['referenceResourceTitle','referenceActivityTitle','referenceActive','referenceInactive','referenceActivityUnknown','referenceReadOnly','referenceNoBookingProof']+list(reference_types.values()):assert key in expected
for file in ['ios/CRMApp/AppointmentReferenceContent.swift','android/app/src/main/java/kz/zani/mobile/ui/AppointmentReferenceContent.kt']:
 content=(root/file).read_text();assert 'referenceReadOnly' in content and 'referenceNoBookingProof' in content and 'activityCopyKey' in content and 'resourceTypeCopyKey' in content
for file in ['ios/Sources/CRMCore/AppointmentReferenceRead.swift','android/app/src/main/java/kz/zani/mobile/data/AppointmentReferenceRepository.kt']:
 content=(root/file).read_text();assert 'ReadTransport' in content
 for token in ['POST','PATCH','Idempotency-Key','expected_updated_at','available-slots','branch_id','resource_id','service_id']:assert token not in content,(file,token)
for file in ['ios/CRMApp/AppointmentRelationsViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/AppointmentRelationsViewModel.kt']:
 content=(root/file).read_text();assert 'referenceAvailable' in content and 'openReference' in content and 'loadReference' in content and 'reference=nil' in content.replace(' ','').replace('null','nil')
assert 'references:APIAppointmentReferenceRepository' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'APIAppointmentReferenceRepository(FixtureTransport(assets))' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
# Independent candidate-read fixture oracle. Static only, not native/runtime/booking acceptance.
from datetime import date as slot_date,datetime as slot_datetime
from zoneinfo import ZoneInfo
slot_catalog=json.loads((f/'appointment-slot-read-cases.json').read_text())
assert slot_catalog['fixture_only'] is True and len(slot_catalog['cases'])==41 and len(slot_catalog['intent_cases'])==12
slot_instant_pattern=re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})')
def slot_instant(raw):
 assert type(raw) is str and slot_instant_pattern.fullmatch(raw) and not raw.endswith('-00:00')
 assert int(raw[11:13])<24 and int(raw[14:16])<60 and int(raw[17:19])<60
 if not raw.endswith('Z'):
  hours,minutes=map(int,raw[-5:].split(':'));assert hours<=18 and minutes<60 and (hours<18 or minutes==0)
 return slot_datetime.fromisoformat(raw.replace('Z','+00:00'))
def slot_body_valid(raw,day,zone):
 try:
  assert type(raw) is list
  for item in raw:
   assert type(item) is dict
   a,b=slot_instant(item['start_at']),slot_instant(item['end_at']);assert b>a and a.astimezone(ZoneInfo(zone)).date().isoformat()==day
  return True
 except (AssertionError,ValueError,KeyError,TypeError):return False
for row in slot_catalog['cases']:
 assert json.loads(row['response_json'])==row['response']
 assert row['valid']==(row['status']==200 and slot_body_valid(row['response'],row['day'],row['timezone'])),row['name']
for row in slot_catalog['intent_cases']:
 assert json.loads(row['day_json'])==row['day']
 try:
  yes=re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',row['day']) is not None and slot_date.fromisoformat(row['day']).isoformat()==row['day']
 except ValueError:yes=False
 assert row['valid']==yes,row['day']
slot_fixture=json.loads((f/'appointment-slot-read-fixtures.json').read_text());assert slot_fixture['fixture_only'] is True and len(slot_fixture['reads'])==8
slot_queries=set()
for row in slot_fixture['reads']:
 q=row['query'];key=json.dumps(q,sort_keys=True);assert key not in slot_queries;slot_queries.add(key)
 assert set(q) in [set(['business_id','service_id','date']),set(['business_id','service_id','date','resource_id'])]
 assert (q['business_id'],q['service_id']) in [('101','8001'),('202','8002')] and q['date'] in ['2026-11-02','2026-11-03']
 if 'resource_id' in q:assert q['resource_id']==('9001' if q['business_id']=='101' else '9002')
 assert json.loads(row['response_json'])==row['response'] and slot_body_valid(row['response'],q['date'],'Asia/Almaty')
for key in ['slotReadOpen','slotReadTitle','slotReadBoundary','slotReadDate','slotReadChooseResource','slotReadUnspecified','slotReadLinkedResource','slotReadSubmit','slotReadEdit','slotReadEmpty']:assert key in expected
for file in ['ios/CRMApp/AppointmentSlotReadContent.swift','android/app/src/main/java/kz/zani/mobile/ui/AppointmentSlotReadContent.kt']:
 content=(root/file).read_text();assert 'slotReadBoundary' in content and 'slotReadChooseResource' in content and 'slotReadEmpty' in content
for file in ['ios/Sources/CRMCore/AppointmentSlotRead.swift','android/app/src/main/java/kz/zani/mobile/data/AppointmentSlotRepository.kt']:
 content=(root/file).read_text();assert 'ReadTransport' in content
 for token in ['POST','PATCH','expected_updated_at','Idempotency-Key','exclude_appointment_id','branch_id']:assert token not in content,(file,token)
assert 'slots:APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'APIAppointmentSlotRepository(FixtureAppointmentSlotTransport(assets))' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
# Local current-read membership/reference context, never booking availability or authority.
slot_reviews=json.loads((f/'appointment-slot-review-cases.json').read_text());assert slot_reviews['fixture_only'] is True and len(slot_reviews['cases'])==23
for row in slot_reviews['cases']:
 for key in ['context_business','context_service','context_resource','response']:assert json.loads(row[key+'_json'])==row[key],(row['name'],key)
 b,s,r=row['context_business'],row['context_service'],row['context_resource']
 yes=slot_body_valid(row['response'],'2026-11-02',row['intent_timezone']) and type(b) is dict and type(b.get('id')) is int and b['id']==101 and type(b.get('name')) is str and b.get('timezone')==row['intent_timezone'] and type(s) is dict and type(s.get('id')) is int and s['id']==8001 and type(s.get('business')) is int and s['business']==101 and type(s.get('name')) is str
 if row['request_resource']:yes=yes and type(r) is dict and type(r.get('id')) is int and r['id']==9001 and type(r.get('business')) is int and r['business']==101 and type(r.get('name')) is str
 else:yes=yes and r is None
 assert row['context_valid']==yes,row['name']
 assert row['review_valid']==(yes and type(row['index']) is int and 0<=row['index']<len(row['response'])),row['name']
 assert json.loads(row['service_name_json'])==s.get('name')
 if r is not None:assert json.loads(row['resource_name_json'])==r.get('name')
for key in ['slotReviewTitle','slotReviewChoose','slotReviewBack','slotReviewRefresh','slotReviewBoundary']:assert key in expected
for file in ['ios/CRMApp/AppointmentSlotReadContent.swift','android/app/src/main/java/kz/zani/mobile/ui/AppointmentSlotReadContent.kt']:
 content=(root/file).read_text();assert 'slotReviewBoundary' in content and 'slotReviewChoose' in content and 'slotReviewRefresh' in content and 'context.service.name' in content and 'context.business.name' in content
for file in ['ios/Sources/CRMCore/AppointmentSlotReview.swift','android/app/src/main/java/kz/zani/mobile/core/AppointmentSlotReview.kt']:
 content=(root/file).read_text()
 for token in ['ReadTransport','POST','PATCH','expected_updated_at','Idempotency-Key','exclude_appointment_id','branch_id']:assert token not in content,(file,token)
# Independently scoped optional Task.client choice and generic action receipt, not GET alias/grant.
task_clients=json.loads((f/'task-create-client-cases.json').read_text());assert task_clients['fixture_only'] is True and len(task_clients['choice_cases'])==12 and len(task_clients['receipt_cases'])==23
for row in task_clients['choice_cases']:
 p=row['profile'];assert json.loads(row['profile_json'])==p and json.loads(row['title_json'])==p['client'].get('title')
 appointments=p['related']['appointments'];limit=p['payload_budget']['max_related_per_section'];business=row['business'];id=row['id']
 yes=type(business) is int and 0<business<=2147483647 and type(id) is int and 0<id<=2147483647 and p['business']==business and p['client']['id']==id and limit>0 and len(appointments)<=limit and len({x['id'] for x in appointments})==len(appointments)
 yes=yes and all(x['client_id']==id and x['id']>0 and slot_instant(x['end_at'])>slot_instant(x['start_at']) for x in appointments)
 assert row['valid']==yes,row['name']
for row in task_clients['receipt_cases']:
 body=row['body'];assert json.loads(row['body_json'])==body
 value=body.get('client','absent');kind='notSet' if 'client' in body and value is None else 'client' if type(value) is int and 0<value<=2147483647 else 'unknown'
 assert row['kind']==kind and row['id']==(value if kind=='client' else None),row['name']
 assert row['accepted']==(row['status']==201 and (row['selected'] is None or kind=='client' and value==row['selected'])),row['name']
for key in ['taskDraftClient','taskDraftClientChoose','taskDraftClientRemove','taskDraftClientUse','taskDraftClientOmit','taskCreateClientReturned']:assert key in expected
for file in ['ios/CRMApp/TaskDraftClientPickerContent.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftClientPickerContent.kt']:
 content=(root/file).read_text();assert 'taskDraftClientUse' in content and 'matchesClientPicker' in content and 'clientSearchCount' in content
 for token in ['details.notes','work.related','onContact','SyntheticTaskCreateGrant']:assert token not in content,(file,token)
for file in ['ios/Sources/CRMCore/TaskDraftClient.swift','android/app/src/main/java/kz/zani/mobile/core/TaskDraftClient.kt']:
 content=(root/file).read_text();assert 'ClientProfile' in content and 'TaskCreateClientRead' in content
 for token in ['POST','PATCH','expected_updated_at','Idempotency-Key','ReadTransport']:assert token not in content,(file,token)
assert 'draftClients:APIReadRepository' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'draftClients=APIReadRepository' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
print('PASS: shared Actions/Home/Today/Appointment/reference-detail/explicit-slot-read/current-candidate-review/client/Inbox/Inbox handoff/reply fake-receipt/exact-raw/Task create-client/create-reminder/create-due-at/create-exact-text/description-replace/title-partial/priority-partial/one-date-partial/explicit-assign/snooze/undo-cancel/watcher/file metadata/reopen+start+completion+self-assignment/Notification read+unread/relative candidate fixture identity/scope/partial/null, RU/KK/EN key parity and generic terms, XML, debug-only composition')
print('NOT_RUN_BY_THIS_SCRIPT: native compile/unit tests, app builds, current-backend compatibility, visual/device/remote CI')

# Independently scoped optional manual Task.appointment (not canonical follow-up/booking).
ta=json.loads((f/'task-create-appointment-cases.json').read_text());assert ta['fixture_only'] and len(ta['choice_cases'])==14 and len(ta['receipt_cases'])==24
for row in ta['choice_cases']:
 p=row['detail'];assert json.loads(row['detail_json'])==p and json.loads(row['title_json'])==p['appointment'].get('title')
 b=row['business'];i=row['id'];assert row['valid']==(type(b) is int and 0<b<=2147483647 and type(i) is int and 0<i<=2147483647 and p['business']==b and p['appointment']['id']==i),row['name']
for row in ta['receipt_cases']:
 body=row['body'];assert json.loads(row['body_json'])==body;v=body.get('appointment','absent');kind='notSet' if 'appointment' in body and v is None else 'appointment' if type(v) is int and 0<v<=2147483647 else 'unknown'
 assert row['kind']==kind and row['id']==(v if kind=='appointment' else None),row['name']
 assert row['accepted']==(row['status']==201 and (row['selected'] is None or kind=='appointment' and v==row['selected'])),row['name']
import datetime as appointment_date, re as appointment_re
for row in ta['day_cases']:
 v=json.loads(row['day_json']);assert row['day']==v
 try:yes=bool(appointment_re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',v)) and appointment_date.date.fromisoformat(v).isoformat()==v
 except ValueError:yes=False
 assert row['valid']==yes
for row in ta['page_cases']:
 p=row['page'];items=p['items'];assert json.loads(row['page_json'])==p
 yes=p['business']==101 and p['date']=='2026-10-30' and len(items)<=50 and p['summary']['total']>=len(items) and all(type(x['id']) is int and 0<x['id']<=2147483647 for x in items) and len({x['id'] for x in items})==len(items)
 assert row['valid']==yes,row['name']
for key in ['taskDraftAppointment','taskDraftAppointmentChoose','taskDraftAppointmentUse','taskDraftAppointmentRemove','taskDraftAppointmentOmit','taskDraftAppointmentDay','taskDraftAppointmentDayIssue','taskCreateAppointmentReturned']:assert key in expected
for file in ['ios/CRMApp/TaskDraftAppointmentPickerContent.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftAppointmentPickerContent.kt']:
 content=(root/file).read_text();assert 'matchesAppointmentPicker' in content and 'taskDraftAppointmentUse' in content and 'clientSearchCount' in content and 'taskDraftAppointmentDay' in content
 for token in ['details.notes','clientRefID','SyntheticTaskCreateGrant','POST','PATCH']:assert token not in content,(file,token)
assert 'draftAppointments:APIReadRepository' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'draftAppointments=APIReadRepository' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
print('PASS: manual Task optional Appointment source identity/day/window/receipt oracle and paired copy/UI composition; no native/device/live acceptance')

# Exact existing safe read categories and accessible status hooks, source-only (not reader/device acceptance).
for row in ta['read_feedback_cases']:
 assert row['copy_key']=={'denied':'denied','not_found':'notFound','unavailable':'unavailable','invalid_payload':'unavailable','invalid_context':'unavailable'}[row['problem']]
 assert all(dictionaries[lang][row['copy_key']].strip() for lang in ['ru','kk','en'])
for file in ['ios/CRMApp/TaskDraftAppointmentPickerContent.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftAppointmentPickerContent.kt']:
 content=(root/file).read_text();assert 'TaskAppointmentReadFeedback.copyKey' in content
 assert ('accessibilityAddTraits(.isHeader)' in content and 'accessibilityHint' in content) if file.endswith('.swift') else ('heading()' in content and 'contentDescription=readScope+": "+text("loading")' in content and 'liveRegion=LiveRegionMode.Polite' in content)
print('PASS: Appointment denied/notFound/unavailable safe copy RU/KK/EN and paired heading/loading/validation/error accessibility source hooks; device/reader NOT_RUN')

# Explicit optional parent_task uses current supplied Task list/detail and separate fake generic receipt.
parents=json.loads((f/'task-create-parent-cases.json').read_text());assert parents['fixture_only'] and len(parents['choice_cases'])==17 and len(parents['receipt_cases'])==26 and len(parents['page_cases'])==9
for row in parents['choice_cases']:
 p=row['detail'];assert json.loads(row['detail_json'])==p and json.loads(row['title_json'])==p['task'].get('title')
 b=row['business'];i=row['id'];comments=p['comments'];limit=p['payload_budget']['max_comments'];due=p['task'].get('due_at')
 yes=type(b) is int and 0<b<=2147483647 and type(i) is int and 0<i<=2147483647 and p['business']==b and p['task']['id']==i and limit>0 and len(comments)<=limit and len({x['id'] for x in comments})==len(comments) and all(x['id']>0 for x in comments)
 if due is not None:
  try:yes=yes and bool(slot_instant(due))
  except (ValueError,TypeError,AssertionError):yes=False
 assert row['valid']==yes,row['name']
for row in parents['receipt_cases']:
 body=row['body'];assert json.loads(row['body_json'])==body;v=body.get('parent_task','absent');kind='notSet' if 'parent_task' in body and v is None else 'parent' if type(v) is int and 0<v<=2147483647 else 'unknown'
 assert row['kind']==kind and row['id']==(v if kind=='parent' else None),row['name']
 assert row['accepted']==(row['status']==201 and row['client_echo']==701 and row['appointment_echo']==501 and (row['selected'] is None or kind=='parent' and v==row['selected'])),row['name']
for row in parents['page_cases']:
 p=row['page'];items=p['items'];assert json.loads(row['page_json'])==p
 yes=p['business']==101 and len(items)<=50 and p['summary']['total']>=len(items) and all(type(x['id']) is int and 0<x['id']<=2147483647 for x in items) and len({x['id'] for x in items})==len(items)
 for item in items:
  if item.get('due_at') is not None:
   try:yes=yes and bool(slot_instant(item['due_at']))
   except (ValueError,TypeError,AssertionError):yes=False
 assert row['valid']==yes,row['name']
for key in ['taskDraftParent','taskDraftParentChoose','taskDraftParentUse','taskDraftParentRemove','taskDraftParentOmit','taskDraftParentLoad','taskCreateParentReturned']:assert key in expected
for file in ['ios/CRMApp/TaskDraftParentPickerContent.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskDraftParentPickerContent.kt']:
 content=(root/file).read_text();assert 'matchesParentPicker' in content and 'taskDraftParentUse' in content and 'clientSearchCount' in content and 'taskDraftParentLoad' in content
 for token in ['details.description','comments','SyntheticTaskCreateGrant','POST','PATCH','searchSubmit','TextField']:assert token not in content,(file,token)
for file in ['ios/CRMApp/TaskParentPickerViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskParentPickerModel.kt']:
 content=(root/file).read_text();assert 'TaskReadRepository' in content and 'taskDetails' in content and 'TaskDraftParentChoice' in content
 for token in ['Date()','LocalDate','TaskDueFilter','SyntheticTaskCreateGrant','POST','PATCH','bootstrap']:assert token not in content,(file,token)
assert 'draftParents:APIReadRepository' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'draftParents=APIReadRepository' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
print('PASS: manual optional Task parent_task identity/window/generic FK receipt oracle and paired explicit selector/UI copy source; no hierarchy/inheritance/live acceptance')

# Generic native read errors reuse existing neutral copy, preserving Appointment-only source wording.
assert dictionaries['en']['notFound']=='Appointment unavailable'
assert dictionaries['en']['notAvailable']=='unavailable'
assert 'case .notFound: text("notAvailable")' in (root/'ios/CRMApp/AppCopy.swift').read_text()
for file in ['ClientDirectoryScreen.kt','ClientSearchContent.kt','QuickReplyContent.kt','TaskDraftParentPickerContent.kt']:
 content=(root/'android/app/src/main/java/kz/zani/mobile/ui'/file).read_text().replace(' ','')
 assert 'ReadProblem.NOT_FOUND->"notAvailable"' in content and 'ReadProblem.NOT_FOUND->"notFound"' not in content,file
assert 'case .notFound:return "notFound"' in (root/'ios/Sources/CRMCore/TaskDraftAppointment.swift').read_text()
print('PASS: existing neutral generic read-error key, four Compose generic consumers and Swift mapper; original RU/KK/EN dictionaries and Appointment-specific copy retained')

# Same-response existing original FK presence and explicit one-field Appointment update-details lens.
relation=json.loads((f/'task-appointment-partial-cases.json').read_text());assert relation['fixture_only'] and len(relation['original_cases'])==14 and len(relation['result_cases'])==30
for row in relation['original_cases']:
 p=row['payload'];assert json.loads(row['payload_json'])==p;fields=p.get('details',{});v=fields.get('appointment_id','absent')
 kind='notSet' if 'appointment_id' in fields and v is None else 'appointment' if type(v) is int and 0<v<=2147483647 else 'unknown'
 assert row['kind']==kind and row['id']==(v if kind=='appointment' else None),row['name']
for row in relation['result_cases']:
 p=row['response'];assert json.loads(row['response_json'])==p;v=p.get('appointment','absent')
 yes=row['status']==200 and type(p.get('id')) is int and p['id']==1101 and type(p.get('business')) is int and p['business']==101 and p.get('status')=='open'
 yes=yes and ((row['mode']=='clear' and 'appointment' in p and v is None) or (row['mode']=='set' and type(v) is int and v==501))
 try:yes=yes and bool(slot_instant(p.get('updated_at')))
 except (ValueError,TypeError,AssertionError):yes=False
 assert row['accepted']==yes,row['name']
metadata=json.loads((f/'task-appointment-partial-outcome.json').read_text());assert metadata['fixture_only'] is True
for row in metadata['scenarios']:
 g=row['grant'];assert set(g)=={'business','task','actor','update'} and type(g['update']) is bool and all(type(g[x]) is int and g[x]>0 for x in ['business','task','actor'])
for key in ['taskAppointmentAction','taskAppointmentSet','taskAppointmentRemove','taskAppointmentOriginal','taskAppointmentOriginalUnknown','taskAppointmentInputIssue','taskAppointmentReturned','taskAppointmentFakeConfirmed','taskAppointmentFakeRejected','taskAppointmentFakeUnknown','taskAppointmentFakeSubmit','taskAppointmentContract']:assert key in expected
for file in ['ios/CRMApp/TaskAppointmentEditView.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskAppointmentEditContent.kt']:
 content=(root/file).read_text();assert 'taskAppointmentOriginalUnknown' in content and 'taskAppointmentContract' in content and 'taskAppointmentFakeUnknown' in content and 'clientSearchCount' in content and 'taskDraftAppointmentDay' in content
 for token in ['source.task.description','details.description','source.task.client','POST','PATCH','expected_version','Idempotency-Key']:assert token not in content,(file,token)
for file in ['ios/Sources/CRMCore/TaskAppointmentEdit.swift','android/app/src/main/java/kz/zani/mobile/core/TaskAppointmentEdit.kt']:
 content=(root/file).read_text();assert 'TaskAppointmentOriginal' in content and 'choiceRead' in content and 'TaskAppointmentDay.valid' in content and '"appointment"' in content
 for token in ['ReadTransport','expected_updated_at','expectedVersion','Idempotency-Key','booking_key','ttl']:assert token not in content,(file,token)
for file in ['ios/CRMApp/TaskListViewModel.swift','android/app/src/main/java/kz/zani/mobile/ui/TaskListViewModel.kt']:
 content=(root/file).read_text();assert 'appointmentEditBarrier' in content and 'appointmentEditCurrent' in content and 'appointmentEditSubmission' in content and 'appointmentEditReads' in content
 current=next(line for line in content.splitlines() if ('func appointmentEditCurrent(' in line or 'fun appointmentEditCurrent(' in line));assert 'appointmentEditBarrier' not in current
assert 'appointmentEditSubmission:FixtureTaskAppointmentEditPort' in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text()
assert 'appointmentEditSubmission=FixtureTaskAppointmentEditPort' in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
assert 'TaskDetails.sourceDecoder(response.data)' in (root/'ios/Sources/CRMCore/ReadRepository.swift').read_text()
assert 'd.userInfo[TaskAppointmentOriginal.decoderKey]=TaskAppointmentOriginal.decode(data)' in (root/'ios/Sources/CRMCore/TaskRead.swift').read_text()
assert 'TaskAppointmentOriginal.decode(json)' in (root/'android/app/src/main/java/kz/zani/mobile/data/JsonContracts.kt').read_text()
print('PASS: exact original relation/null/unknown and one-field Appointment partial result oracle, separate fake UPDATE/read ports, owner barriers, paired UI/copy, no full-original resave/version/key/live claim')

# Raw date editing uses local stable input visits; list/detail/choice tickets remain independent.
for name in ["mobile/ios/CRMApp/TaskAppointmentPickerViewModel.swift", "mobile/android/app/src/main/java/kz/zani/mobile/ui/TaskAppointmentPickerModel.kt"]:
    text=(root.parent/name).read_text()
    assert "TaskAppointmentPickerInputControl" in text and "inputVisit" in text
for name,fragment in [("mobile/ios/CRMApp/TaskDraftAppointmentPickerContent.swift", "read.updateDay($0,input:input)"), ("mobile/android/app/src/main/java/kz/zani/mobile/ui/TaskDraftAppointmentPickerContent.kt", "read.updateDay(it,input=input)"), ("mobile/ios/CRMApp/TaskAppointmentEditView.swift", "model.updateDay($0,input:input)"), ("mobile/android/app/src/main/java/kz/zani/mobile/ui/TaskAppointmentEditContent.kt", "model.updateDay(it,input)")]:
    assert fragment in (root.parent/name).read_text(), name
print("PASS: paired Appointment raw date bindings use independent stable input visits; strict read/choice controls retained, device/IME NOT_RUN")

# Client-only Task partial original/result are separate exact existing source fields.
client_partial=json.loads((f/"task-client-partial-cases.json").read_text())
for row in client_partial["original_cases"]:
    obj=json.loads(row["payload_json"]);header=obj.get("task",{});v=header.get("client_id")
    kind="unknown" if "client_id" not in header else "notSet" if v is None else "client" if type(v) is int and 1<=v<=2147483647 else "unknown"
    assert kind==row["kind"] and (kind!="client" or v==row["id"]), row["name"]
for row in client_partial["result_cases"]:
    obj=json.loads(row["response_json"])
    positive=lambda v:type(v) is int and 1<=v<=2147483647
    selected="client" in obj and (obj["client"] is None if row["mode"]=="clear" else positive(obj["client"]) and obj["client"]==1754)
    stamp=obj.get("updated_at")
    try:
        import datetime
        valid_stamp=isinstance(stamp,str) and len(stamp)>=20 and datetime.datetime.fromisoformat(stamp.replace("Z","+00:00")).tzinfo is not None
    except (TypeError,ValueError):valid_stamp=False
    valid=row["status"]==200 and positive(obj.get("id")) and obj["id"]==1101 and positive(obj.get("business")) and obj["business"]==101 and obj.get("status")=="open" and selected and valid_stamp
    assert valid==row["accepted"],row["name"]
repo=(root/"ios/Sources/CRMCore/ReadRepository.swift").read_text();fixture_context=(root/"ios/Sources/CRMCore/TaskCommentDraft.swift").read_text()
assert "TaskDetails.sourceDecoder(response.data)" in repo and "TaskDetails.decodeSource(data)" in fixture_context
for folder,ext in [("ios/Sources/CRMCore/","swift"),("android/app/src/main/java/kz/zani/mobile/core/","kt")]:
    original=(root/(folder+"TaskClientOriginal."+ext)).read_text();command=(root/(folder+"TaskClientEdit."+ext)).read_text()
    assert '"task"' in original and '"client_id"' in original and '"details"' not in original
    assert '"client"' in command and '"appointment"' not in command and '"client_id"' not in command
    assert all(word not in command for word in ["expected_version","idempotency","httpClient","URLSession"])
for name in ["ios/CRMApp/TaskListViewModel.swift","android/app/src/main/java/kz/zani/mobile/ui/TaskListViewModel.kt"]:
    text=(root/name).read_text();assert "clientEditSubmission" in text and "clientEditReads" in text and "clientEditBarrier" in text
    line=next(x for x in text.splitlines() if "clientEditCurrent(" in x and ("func " in x or "fun " in x))
    assert "!clientEditBarrier" not in line and "!appointmentEditBarrier" in line
client_copy=json.loads((root/"contracts/ui-copy.json").read_text())
for key in [k for k in client_copy["en"] if k.startswith("taskClient")]:
    assert all(client_copy[lang][key] for lang in ["ru","kk","en"])
assert len(client_partial["original_cases"])==14 and len(client_partial["result_cases"])==30
print("PASS: exact task.client_id presence and client-only partial body/result oracle, shared same-response decoder/fixture equality path, separate fake UPDATE/read ports and owner lane; no Appointment inheritance/current write acceptance")

# Source-defined raw Client query parity; strip is the only submitted transformation.
import unicodedata
raw_client_cases=json.loads((f/"client-search-raw-unicode-cases.json").read_text())["cases"]
for row in raw_client_cases:
    assert row["changed"]==(row["before"].encode()!=row["after"].encode())
    assert row["canonical_equivalent"]==(unicodedata.normalize("NFC",row["before"])==unicodedata.normalize("NFC",row["after"]))
    assert row["before_submitted"]==row["before"].strip() and row["after_submitted"]==row["after"].strip()
assert sum(row["changed"] and row["canonical_equivalent"] for row in raw_client_cases)>=5
assert "!query.utf8.elementsEqual(value.utf8)" in (root/"ios/Sources/CRMCore/ClientSearch.swift").read_text()
assert "!query.utf8.elementsEqual(session.query.utf8)" in (root/"ios/CRMApp/ClientSearchViewModel.swift").read_text()
print("PASS: shared raw Unicode Client search/Task partial input parity cases, exact Swift raw guards and existing source strip; no normalization/automatic GET/device IME acceptance")

# QuickReply raw input correlates local choices/windows; existing JS trim/lower and literal insertion remain.
quick_unicode=json.loads((f/"quick-reply-raw-unicode-cases.json").read_text())["cases"]
assert len(quick_unicode)==7
for row in quick_unicode:
    assert row["changed"]==(row["before"].encode()!=row["after"].encode())
    assert row["page"]["count"]==1 and row["page"]["next"] is None and len(row["page"]["results"])==1
    template=row["page"]["results"][0];assert template["business"]==101 and template["channel"]=="website" and template["is_active"] is True
    for raw in [row["before"],row["after"]]:assert raw.strip().lower() in template["title"].lower()
    assert row["inserted"]=="  Operator own\n"+template["text"] and "{{client}}" in template["text"]
assert "!query.utf8.elementsEqual(value.utf8)" in (root/"ios/Sources/CRMCore/QuickReplies.swift").read_text()
assert "!session.query.utf8.elementsEqual(before.utf8)" in (root/"ios/CRMApp/QuickReplyViewModel.swift").read_text()
print("PASS: scoped raw Unicode QuickReply choices/literal insertion fixtures and paired source guards; unknown attempt/read/send/current boundaries retained")

# Existing reply body is a per-attempt immutable local snapshot, not regenerated serialization.
reply_attempt=(root/"ios/Sources/CRMCore/InboxReplySubmission.swift").read_text()
assert "private let bodyData:Data?" in reply_attempt and "public func preparedBody()->Data? {bodyData}" in reply_attempt
reply_attempt_k=(root/"android/app/src/main/java/kz/zani/mobile/core/InboxReplySubmission.kt").read_text()
assert "private val bodySnapshot=" in reply_attempt_k and "fun preparedBody():String=bodySnapshot" in reply_attempt_k
print("PASS: paired immutable prepared reply-body snapshots retain existing business/text fields and opaque key/header/unknown boundaries")

# Inbox raw query changes expire actions independently of its continuous input visit.
inbox_raw_cases=json.loads((f/"inbox-list-raw-unicode-cases.json").read_text())["cases"]
assert len(inbox_raw_cases)==7 and any(row["partial"] for row in inbox_raw_cases) and any(not row["partial"] for row in inbox_raw_cases)
for row in inbox_raw_cases:
    page=row["list"];assert page["business"]==101 and [x["id"] for x in page["items"]]==row["loaded_ids"]
    assert row["changed"]==(row["before"].encode()!=row["after"].encode()) and row["total"]==page["summary"]["open"] and row["partial"]==(row["total"]>len(page["items"]))
    for raw in [row["before"],row["after"]]:assert raw.strip().lower() in page["items"][0]["title"].lower()
    assert page["items"][0]["unread_count"]==2 and page["summary"]["unread"]==1
assert "!query.utf8.elementsEqual(oldValue.utf8)" in (root/"ios/CRMApp/InboxViewModel.swift").read_text()
print("PASS: scoped Inbox raw Unicode query/window and complete/partial/unread fixtures; stale row/retry/filter ownership paired, no request/send/unknown boundary changes")

# Exact loaded-header identity oracle, deliberately separate from text-query collation.
loaded_headers = json.loads((root / "contracts/fixtures/loaded-search-exact-header-cases.json").read_text())
assert loaded_headers["fixture_only"] and len(loaded_headers["cases"]) == 9
for row in loaded_headers["cases"]:
    left, right = row["before_title"], row["after_title"]
    assert row["changed"] == (left != right)
    assert "shared" in left.lower()
    if right: assert "shared" in right.lower()
assert any(row["after_title"] is None for row in loaded_headers["cases"])
assert any(row["after_title"] == "" for row in loaded_headers["cases"])
header_core=(root / "ios/Sources/CRMCore/LoadedSearch.swift").read_text()
assert "SourceTextIdentity.same(lhs,rhs)" in header_core and "LoadedSearchHeader.same($0.title,hit.title)" in header_core
assert "title.range(of: needle, options: .caseInsensitive)" in header_core
assert "!LoadedSearchHeader.same(title,hit.title)" in (root / "ios/CRMApp/LoadedSearchViewModel.swift").read_text()
print("PASS: exact loaded row/hit/source/header identity and withheld/empty raw fixtures; existing query collation, scoped independent reads and no command/current acceptance retained")

# Raw-query input ownership is independent from the list action window and read ticket.
query_windows=json.loads((root / "contracts/fixtures/loaded-search-query-window-cases.json").read_text())
assert query_windows["fixture_only"] and len(query_windows["cases"])==8
for row in query_windows["cases"]:
    assert row["changed"]==(row["before"]!=row["after"])
    assert row["before"].strip().lower() in row["title"].lower() and row["after"].strip().lower() in row["title"].lower()
svm=(root / "ios/CRMApp/LoadedSearchViewModel.swift").read_text();kvm=(root / "android/app/src/main/java/kz/zani/mobile/ui/LoadedSearchViewModel.kt").read_text()
assert "!query.utf8.elementsEqual(oldValue.utf8)" in svm and "LoadedSearchInputControl" in svm and "inputControl==input" in svm
assert "query!=state.query" in kvm and "fun searchInput" in kvm and "inputControl==input" in kvm
assert "model.search($0,input:input)" in (root / "ios/CRMApp/LoadedSearchScreen.swift").read_text()
assert "model.searchInput(it,input)" in (root / "android/app/src/main/java/kz/zani/mobile/ui/LoadedSearchScreen.kt").read_text()
print("PASS: shared exact raw search query/action windows with independent continuous input, paired UI bindings and existing scoped GET/read/feed/header boundaries")

comment_exact=json.loads((root / "contracts/fixtures/task-comment-exact-text-cases.json").read_text())
assert comment_exact["fixture_only"] and len(comment_exact["cases"])==7
base_comment=next(row["response"] for row in json.loads((f / "task-comment-submit.json").read_text())["validation_cases"] if row["expected"]=="confirmed")
for row in comment_exact["cases"]:
    assert row["changed"]==(row["before"]!=row["after"])
    for side in ("before","after"):
        assert row[side].strip()==row[side+"_preview"]
        response=json.loads(row[side+"_response_json"]);assert response["text"]==row[side+"_preview"]
        assert {k:v for k,v in response.items() if k!="text"}=={k:v for k,v in base_comment.items() if k!="text"}
comment_source=(root / "ios/Sources/CRMCore/TaskCommentSubmission.swift").read_text()
assert "TaskCommentText.preview(raw).utf8.elementsEqual(review.text.utf8)" in comment_source and "comment.text?.utf8.elementsEqual(attempt.text.utf8)==true" in comment_source
assert "preparedBody" not in comment_source and "Idempotency-Key" not in comment_source
assert "!session.text.utf8.elementsEqual(before.utf8)" in (root / "ios/CRMApp/TaskCommentViewModel.swift").read_text()
print("PASS: Task comment exact raw/review/typed201 echo/destructive-clear fixtures; source metadata/strip/fake UPDATE authority and unknown no-replay boundaries retained, no HTTP body invented")

# Typed Task free-text identity keeps all other fields; bounded and action projections remain separate.
task_text=json.loads((f / "task-read-text-identity-cases.json").read_text());assert task_text["fixture_only"] and len(task_text["cases"])==50 and len(task_text["nontext_cases"])==25
for row in task_text["cases"]:
    assert row["changed"]==(row["before"]!=row["after"])
    a,b=json.loads(row["before_json"]),json.loads(row["after_json"])
    if row["field"]=="task.title":left,right=a["task"].pop("title"),b["task"].pop("title")
    elif row["field"]=="details.description":left,right=a["details"].pop("description"),b["details"].pop("description")
    elif row["field"]=="comments.text":left,right=a["comments"][0].pop("text"),b["comments"][0].pop("text")
    else:left,right=a.pop(row["field"].split(".")[1]),b.pop(row["field"].split(".")[1])
    assert left==row["before"] and right==row["after"] and a==b
identity=(root / "ios/Sources/CRMCore/SourceTextTrim.swift").read_text();assert "left.utf8.elementsEqual(right.utf8)" in identity
read_source=(root / "ios/Sources/CRMCore/TaskRead.swift").read_text()
for start,end,fields in [("public struct WorkTask:","public struct TaskPage:",["id","title","status","priority","due_at","client_id","business","cancelled_at","cancelled_by","cancel_reason","updated_at","description","created_by","created_at"]),("public struct TaskComment:","public enum TaskScheduleValue:",["id","text","created_at","task","author","author_name","author_email","authorRead"]),("public struct Fields:","public struct Budget:",["description","appointment_id","appointmentRead","reminder_at","snoozed_until","created_by","assignee"])]:
    section=read_source.split(start,1)[1].split(end,1)[0]
    for field in fields:assert "lhs."+field in section and "rhs."+field in section
assert "return Self.verified(detail,reference:reference)" in (root / "ios/Sources/CRMCore/TaskCommentDraft.swift").read_text()
print("PASS: typed Task optional free-text identity, all comparator fields and separate bounded/action fixtures; reference admission remains read-only, not UPDATE/JSON-byte proof")

users=json.loads((f / "mobile-user-display-text-cases.json").read_text());assert users["fixture_only"] and len(users["cases"])==72
for row in users["cases"]:
    a,b=json.loads(row["before_user_json"]),json.loads(row["after_user_json"])
    assert set(a)==set(b)=={"id","email","full_name"} and a["id"]==b["id"] and row["changed"]==(a!=b)
    for side,u in [("before",a),("after",b)]:
        display=u["full_name"] if u["full_name"].strip() else u["email"] if u["email"].strip() else None
        assert display==row[side+"_display"]
user_source=(root / "ios/Sources/CRMCore/MobileUserItem.swift").read_text()
assert "lhs.id==rhs.id" in user_source and "SourceTextIdentity.same(lhs.email,rhs.email)" in user_source and "SourceTextIdentity.same(lhs.full_name,rhs.full_name)" in user_source
assert "public var valid: Bool {id>0}" in user_source
print("PASS: existing _user_item exact provided display strings, original id/valid/fallback and nested Task reference fixtures; no auth/session/security/membership/permission or command inference")

# Exact existing generic duplicate response, explicitly separate local fixture envelope.
duplicates=json.loads((f/'client-duplicate-preview.json').read_text())
assert duplicates['fixture_only'] is True
assert len(duplicates['scenarios'])==5 and len(duplicates['decode_cases'])==29
assert len({(s['business'],s['phone'],s['email']) for s in duplicates['scenarios']})==5
known={'phone','email','whatsapp_id','telegram_id','instagram_id'}
def valid_duplicate_response(raw):
 try:
  value=json.loads(raw);rows=value['duplicates'];assert type(rows) is list
  ids=[]
  for row in rows:
   assert type(row) is dict and type(row['id']) is int and row['id']>0
   assert all(type(row[k]) is str for k in ['full_name','phone','email'])
   fields=row['matched_fields'];assert type(fields) is list and all(type(v) is str and v in known for v in fields) and len(set(fields))==len(fields)
   ids.append(row['id'])
  assert len(set(ids))==len(ids);return True
 except (AssertionError,KeyError,TypeError):return False
for row in duplicates['decode_cases']:assert valid_duplicate_response(row['response_json'])==row['valid'],row['name']
for row in duplicates['scenarios']:assert valid_duplicate_response(json.dumps(row['response']))
for name in ['ios/CRMApp/PlatformaCRMApp.swift','android/app/src/main/java/kz/zani/mobile/MainActivity.kt']:assert 'duplicateSource' in (root/name).read_text()
print('PASS: exact existing duplicate response fixtures, explicit local source injection and paired draft review ownership; no real duplicate POST/matching/grant/merge/archive/current acceptance')

merge=json.loads((f/'client-merge-preview.json').read_text())
assert merge['fixture_only'] is True and len(merge['catalogs'])==3
fields=['leads','appointments','conversations','bot_conversations','tasks','deals','notes','activity_events','analytics_events','notifications','tags','attachments','custom_field_values']
def valid_merge_preview(raw):
 try:
  v=json.loads(raw);assert type(v['target_client_id']) is int and v['target_client_id']>0
  s=v['duplicate'];assert type(s['id']) is int and s['id']>0 and s['id']!=v['target_client_id']
  assert all(type(s[k]) is str for k in ['full_name','phone','email','whatsapp_id','telegram_id','instagram_id','source']) and type(s['is_archived']) is bool
  counts=v['transferred'];assert type(counts) is dict and set(counts)==set(fields) and all(type(n) is int and n>=0 for n in counts.values())
  assert v['will_delete_duplicate'] is False and v['policy']=='archive_duplicate_after_transfer';return True
 except (KeyError,TypeError,AssertionError):return False
for row in merge['decode_cases']:assert valid_merge_preview(row['response_json'])==row['valid'],row['name']
assert len(merge['snapshot_identity_pairs'])==7
for g in merge['catalogs']:
 assert all(valid_merge_preview(json.dumps(v)) and v['target_client_id']==g['target'] for v in g['previews'])
 assert len({v['duplicate']['id'] for v in g['previews']})==len(g['previews'])
for name in ['ios/CRMApp/PlatformaCRMApp.swift','android/app/src/main/java/kz/zani/mobile/MainActivity.kt']:assert 'mergeSource' in (root/name).read_text()
print('PASS: exact merge-dry-run13 counts/archive policy and explicit local target/choice/catalog fixtures; no real merge/archive/POST/permission/outcome or current acceptance')

connection=json.loads((f/'backend-read-transport.json').read_text())
assert connection['fixture_only'] is True and len(connection['config_cases'])==24 and len(connection['status_cases'])==7
assert {r['expected'] for r in connection['status_cases']}=={'loaded','unavailable','denied','notFound'}
assert all(set(row['values'])<= {'CRM_API_ORIGIN','CRM_READ_TIMEOUT_SECONDS'} or row['expected']=='unexpectedKey' for row in connection['config_cases'])
for name in ['ios/Sources/CRMCore/BackendReadTransport.swift','android/app/src/main/java/kz/zani/mobile/data/BackendReadTransport.kt']:
 text=(root/name).read_text();assert 'NativeReadHTTPExchange' in text and 'BackendReadTransport' in text;assert ('ensureActive' in text if name.endswith('.kt') else 'Task.checkCancellation' in text)
assert 'BackendReadTransport(' not in (root/'ios/CRMApp/PlatformaCRMApp.swift').read_text() and 'BackendReadTransport(' not in (root/'android/app/src/main/java/kz/zani/mobile/MainActivity.kt').read_text()
print('PASS: explicit public config/GET HTTP-exchange adapters and existing repository/status/owner fixtures; no implicit session/credentials/env/global target/retry/fallback or network execution in checks')

# Pure source-defined auth schema preparation; no live client/session/UI binding.
auth_catalog = json.loads((f / "mobile-auth-contracts.json").read_text())
assert auth_catalog["fixture_only"] is True and len(auth_catalog["request_cases"]) == 7 and len(auth_catalog["response_cases"]) == 116
for row in auth_catalog["request_cases"]:
    assert row["values"] == row["expected_body"]
    if row["operation"] == "login":
        assert set(row["values"]) <= {"device_id", "platform", "email", "password", "business", "app_version", "build_number", "os_version", "device_model"}
        assert {"device_id", "platform", "email", "password"} <= set(row["values"])
for name in ["mobile/ios/CRMApp/PlatformaCRMApp.swift", "mobile/android/app/src/main/java/kz/zani/mobile/MainActivity.kt"]:
    assert "MobileAuthJSON" not in (root.parent / name).read_text()
print("PASS: paired pure login/refresh/logout schemas, exact optional/raw synthetic fixtures, source Business/device/descriptor context and redacted debug values; no native auth UI/session/network/credential operation")

lifecycle_catalog = json.loads((f / "appointment-lifecycle.json").read_text())
assert lifecycle_catalog["fixture_only"] is True and len(lifecycle_catalog["scenarios"]) == 9 and len(lifecycle_catalog["receipt_cases"]) == 52
for scenario in lifecycle_catalog["scenarios"]:
    assert scenario["grant"]["update"] is True and scenario["grant"]["actor"] == 5001
    assert scenario["action"] in {"confirm", "cancel", "reschedule"}
    if scenario["outcome"] == "response":
        response = json.loads(scenario["response_json"])
        assert set(response) == {"ok", "appointment", "replayed"}
        assert set(response["appointment"]) == {"id", "title", "status", "client_id", "lead_id", "service_id", "start_at", "end_at", "href"}
for key in ["appointmentLifecycle", "appointmentLifecycleConfirm", "appointmentLifecycleCancel", "appointmentLifecycleReview", "appointmentLifecycleSubmit", "appointmentLifecycleAccepted", "appointmentLifecycleRejected", "appointmentLifecycleUnknown", "appointmentLifecycleReplay"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
assert "AppointmentLifecycleViewModel.swift" in (root/"scripts/check_swift_view_model.sh").read_text()
print("PASS: paired selected Appointment confirm/cancel local review/attempt/receipt and explicit fixture UPDATE/key context; unknown cross-action quarantine, no GET mutation/real lifecycle or invented reason/version/date/key")

reschedule_catalog = json.loads((f / "appointment-reschedule.json").read_text())
assert reschedule_catalog["fixture_only"] is True and len(reschedule_catalog["time_cases"]) == 19 and len(reschedule_catalog["receipt_cases"]) == 55
assert len([row for row in lifecycle_catalog["scenarios"] if row["action"] == "reschedule"]) == 3
for row in lifecycle_catalog["scenarios"]:
    if row["action"] == "reschedule":
        assert set(row["input"]) == {"start_at", "reason_raw", "resource"}
        assert row["grant"]["reschedule_key"].startswith("synthetic-")
for key in ["appointmentLifecycleReschedule", "appointmentRescheduleTime", "appointmentRescheduleTimeHint", "appointmentRescheduleTimeInvalid", "appointmentRescheduleReason", "appointmentRescheduleClear", "appointmentRescheduleLinked", "appointmentRescheduleChoice", "appointmentRescheduleReceiptLimits", "appointmentRescheduleReview"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
print("PASS: paired bounded reschedule raw time/source reason/explicit clear-or-scoped Resource read and shared lifecycle ledger; exact input/receipt fixtures, stable input visits and no absent resource/reason/availability/version proof or real booking")

terminal_catalog = json.loads((f / "appointment-terminal.json").read_text())
assert terminal_catalog["fixture_only"] is True and len(terminal_catalog["scenarios"]) == 5
for row in terminal_catalog["scenarios"]:
    assert row["action"] in {"complete", "no-show"} and row["grant"]["update"] is True and row["grant"]["actor"] == 5001
    assert set(row["grant"]) == {"business", "appointment", "actor", "update", "actions"}
    if row["outcome"] == "response":
        response = json.loads(row["response_json"])
        assert response["id"] == row["grant"]["appointment"] and response["business"] == row["grant"]["business"]
        assert response["status"] == {"complete":"completed", "no-show":"no_show"}[row["action"]]
        assert not {"ok", "appointment", "replayed"} & set(response)
for key in ["appointmentLifecycleComplete", "appointmentLifecycleNoShow", "appointmentTerminalLimits"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
print("PASS: paired generic complete/no-show local review/plain bounded receipt and separate synthetic UPDATE/actor context, empty supported body/business query; shared5-action unknown barrier, no invented mobile key/envelope/version/replayed or actual lifecycle/followup/audit")

booking_catalog = json.loads((f / "appointment-booking.json").read_text())
assert booking_catalog["fixture_only"] is True and len(booking_catalog["scenarios"]) == 3
for row in booking_catalog["scenarios"]:
    assert set(row["grant"]) == {"business", "from_appointment", "actor", "create"} and row["grant"]["create"] is True
    assert set(row["input"]) == {"client", "service", "resource", "start_at"}
    if row["outcome"] == "response":
        response = json.loads(row["response_json"])
        assert row["status"] == 201 and response["client"] == row["input"]["client"] and response["service"] == row["input"]["service"]
        assert not {"ok", "appointment", "replayed"} & set(response)
for key in ["bookingOpen", "bookingTitle", "bookingReadClient", "bookingReadService", "bookingReadResource", "bookingReview", "bookingLimits"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
assert "AppointmentBookingViewModel.swift" in (root/"scripts/check_swift_view_model.sh").read_text()
print("PASS: paired bounded new Appointment form from explicit scoped Client/Service/Resource reads, blank time/explicit resource review, exact5 generic create body/plain201 fixture and separate synthetic CREATE/actor; immutable unknown no-repeat and no GET mutation/defaults/key/version/real booking")

candidate_time = json.loads((f / "appointment-booking-candidate-time.json").read_text())
assert candidate_time["fixture_only"] is True and len(candidate_time["cases"]) == 18
assert "bookingUseCandidateTime" in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
for name in ["ios/Sources/CRMCore/AppointmentBookingCandidateTime.swift", "android/app/src/main/java/kz/zani/mobile/core/AppointmentBookingCandidateTime.kt"]:
    assert "rawStart" in (root/name).read_text()
print("PASS: paired explicit current-candidate start-only bridge with parent/read/service/resource/timezone/index/precision/control guards; Client/Resource/CREATE remain explicit, no reservation/end_at/booking or unknown replay")

service_directory = json.loads((f / "service-directory.json").read_text())
assert service_directory["fixture_only"] is True and len(service_directory["cases"]) == 53
for case in service_directory["cases"]:
    body = json.loads(case["response_json"])
    assert isinstance(case["valid"], bool)
assert {"/api/services/", "/api/services/8001/", "/api/services/8002/", "/api/services/8003/"} == {x["path"] for x in service_directory["reads"]}
for path in ["ios/Sources/CRMCore/ServiceDirectory.swift", "android/app/src/main/java/kz/zani/mobile/core/ServiceDirectory.kt"]:
    assert "ServiceDirectoryWindow" in (root/path).read_text()
print("PASS: paired bounded Service list projection, independent detail/read-choice, no total/end/grant/currency/default inference; 53 meaningful shared cases")

resource_directory = json.loads((f / "resource-directory.json").read_text())
assert resource_directory["fixture_only"] is True and len(resource_directory["cases"]) == 54
assert {"/api/resources/", "/api/resources/9001/", "/api/resources/9002/", "/api/resources/9003/"} == {row["path"] for row in resource_directory["reads"]}
for name in ["ios/Sources/CRMCore/DirectoryReadWindow.swift", "android/app/src/main/java/kz/zani/mobile/core/DirectoryReadWindow.kt"]:
    assert "DirectoryReadEnvelope" in (root/name).read_text()
print("PASS: paired bounded Resource7-field read selector and shared strict envelope; 54 Resource cases plus original53 Service cases retained, no type/activity/availability/CREATE defaults")

booking_directory = json.loads((f / "appointment-booking-directory.json").read_text())
assert booking_directory["fixture_only"] is True and len(booking_directory["cases"]) == 17
for key in ["bookingSelectService","bookingSelectResource","bookingUseService","bookingUseResource"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
print("PASS: form-owned Service/Resource independently read snapshot binding, existing5 wire body and separate CREATE/unknown, 17 shared proof/legacy/scope/client/raw cases; no actual booking/availability acceptance")

# Independent fixture oracle for scoped Client relation observation, distinct from native execution.
booking_client = json.loads((f / "appointment-booking-client.json").read_text())
assert len(booking_client["cases"]) == 20
for row in booking_client["cases"]:
    proof_valid = (row["proof_source_epoch"] > 0 and row["context_business"] == 101 and row["context_epoch"] == row["proof_source_epoch"] and row["selection_generation"] > 0 and row["profile_generation"] > 0 and row["read_business"] == row["profile_business"] == 101 and row["read_id"] == row["selected_id"] == row["profile_id"] and row["read_revision"] > 0)
    chosen = (proof_valid and row["source_epoch"] == row["proof_source_epoch"] and row["client"] == row["profile_id"] and row["client_title"] == row["proof_title"]) if row["proof"] else row["client"] == 7001
    assert (row["source_epoch"] > 0 and chosen) == row["valid"], row["name"]
for key in ["bookingSelectClient", "bookingUseClient"]:
    assert key in json.loads((root/"contracts/ui-copy.json").read_text())["ru"]
for name in ["ios/CRMApp/AppointmentBookingClientPickerContent.swift", "android/app/src/main/java/kz/zani/mobile/ui/AppointmentBookingClientPickerContent.kt"]:
    source = (root/name).read_text()
    assert "matchesClientPicker" in source and "confirmClient" in source and "clientSearchCount" in source and "partial" in source
for name in ["ios/Sources/CRMCore/AppointmentBookingClient.swift", "android/app/src/main/java/kz/zani/mobile/core/AppointmentBookingClient.kt"]:
    assert "TaskDraftClientChoice" in (root/name).read_text()
print("PASS:20 independent Client relation scope/raw/withheld/legacy fixture oracle cases and paired private search/profile/explicit Use source hooks; unchanged5 body/CREATE/unknown. Native checks prepared, NOT_RUN")

# Independent source-shape fixture oracle only; this does not execute Swift or Kotlin.
from datetime import datetime as _file_datetime
inbox_files = json.loads((f/"inbox-conversation-files.json").read_text())
assert inbox_files["fixture_only"] is True and len(inbox_files["cases"]) == 94
assert {row["path"] for row in inbox_files["reads"]} == {"/api/inbox/conversations/901/", "/api/inbox/conversations/951/"}
def _inbox_file_oracle(body, context):
    def positive(value): return type(value) is int and 0 < value <= 2147483647
    if not (positive(context["business"]) and positive(context["conversation"]) and context["epoch"] > 0 and context["revision"] > 0): return False
    if not (isinstance(body, dict) and positive(body.get("id")) and positive(body.get("business")) and body["id"] == context["conversation"] and body["business"] == context["business"] and isinstance(body.get("attachments"), list)): return False
    seen = set()
    for row in body["attachments"]:
        if not isinstance(row, dict): return False
        if not (positive(row.get("id")) and row["id"] not in seen and positive(row.get("business")) and row["business"] == context["business"]): return False
        seen.add(row["id"])
        if not (type(row.get("size")) is int and 0 <= row["size"] <= 9223372036854775807): return False
        if not all(isinstance(row.get(key), str) for key in ["original_name", "content_type", "entity_type", "entity_id", "visibility", "created_at"]): return False
        if not (row["entity_type"] == "bot_conversation" and row["entity_id"] == str(context["conversation"]) and row["visibility"] == "private"): return False
        try:
            if _file_datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).tzinfo is None: return False
        except ValueError: return False
    return True
for row in inbox_files["cases"]:
    assert _inbox_file_oracle(json.loads(row["response_json"]), row["context"]) == row["valid"], row["name"]
for name in ["ios/CRMApp/InboxConversationFilesContent.swift", "android/app/src/main/java/kz/zani/mobile/ui/InboxConversationFilesContent.kt"]:
    source = (root/name).read_text()
    assert all(key in source for key in ["fileMetadataEmpty", "fileVerificationUnknown", "fileSizeBytes", "inboxFilesTitle", "isCurrent"])
    assert "download_url" not in source and "uploaded_by" not in source
for name in ["ios/CRMApp/InboxViewModel.swift", "android/app/src/main/java/kz/zani/mobile/ui/InboxViewModel.kt"]:
    source = (root/name).read_text()
    assert "filesPresentationControl" in source and "filesEntryControl" in source and "matchesFiles" in source
print("PASS:94 independent generic conversation attachment metadata scope/raw/strict/empty/unknown fixture oracles and paired manual inspector/peer guards; no URL/file bytes/send/scan/current acceptance. Native checks prepared NOT_RUN")
# Independent generic first-window/selected-message oracle; native suites run separately.
message_files = json.loads((f/"inbox-message-files.json").read_text())
assert message_files["fixture_only"] is True
assert len(message_files["cases"]) == 145 and len(message_files["anchor_cases"]) == 22 and len(message_files["source_identity_cases"]) == 11

def _message_context(c):
    return all(type(c.get(k)) is int and 0<c[k]<=2147483647 for k in ["business","conversation","message"]) and all(type(c.get(k)) is int and c[k]>0 for k in ["epoch","revision"]) and type(c.get("limit")) is int and 1<=c["limit"]<=300

def _message_anchor(body,c):
    return _message_context(c) and isinstance(body,dict) and all(type(body.get(k)) is int and body[k]==c[v] for k,v in [("id","conversation"),("business","business")])

def _message_window(body,c):
    if not _message_context(c) or not isinstance(body,dict):return "invalidPayload"
    if not all(k in body for k in ["count","next","previous","results","next_before_id","has_more"]):return "invalidPayload"
    rows=body["results"];count=body["count"];more=body["has_more"];cursor=body["next_before_id"]
    if not (isinstance(rows,list) and len(rows)<=c["limit"] and type(count) is int and len(rows)<=count<=9223372036854775807 and type(more) is bool and body["previous"] is None):return "invalidPayload"
    if more:
        if not (len(rows)==c["limit"] and type(cursor) is int and 0<cursor<=2147483647 and body["next"]==str(cursor)):return "invalidPayload"
    elif body["next"] is not None or cursor is not None:return "invalidPayload"
    ids=set();files=set();found=False
    for row in rows:
        if not isinstance(row,dict) or not (type(row.get("id")) is int and 0<row["id"]<=2147483647 and row["id"] not in ids and type(row.get("conversation")) is int and row["conversation"]==c["conversation"] and isinstance(row.get("attachments"),list)):return "invalidPayload"
        ids.add(row["id"])
        # Reuse the independently checked nine-field schema after explicitly remapping source entity identity.
        converted=[]
        for attachment in row["attachments"]:
            if not isinstance(attachment,dict) or attachment.get("entity_type")!="bot_message" or attachment.get("entity_id")!=str(row["id"]) or attachment.get("id") in files:return "invalidPayload"
            files.add(attachment.get("id"));converted.append(dict(attachment,entity_type="bot_conversation",entity_id=str(c["conversation"])))
        if not _inbox_file_oracle(dict(id=c["conversation"],business=c["business"],attachments=converted),c):return "invalidPayload"
        found=found or row["id"]==c["message"]
    return "valid" if found else "unavailable"

for row in message_files["anchor_cases"]:
    assert _message_anchor(json.loads(row["response_json"]),row["context"]) == row["valid"],row["name"]
for row in message_files["cases"]:
    assert _message_window(json.loads(row["response_json"]),row["context"]) == row["expected"],row["name"]
for row in message_files["source_identity_cases"]:
    def identity(value):return (value["id"],value["conversation_id"],*[value.get(k) for k in ["direction","sender_type","text","created_at"]],value.get("status") if value.get("status") in ["received","queued","sent","failed"] else "unknown")
    assert (identity(row["left"])==identity(row["right"])) == row["same"],row["name"]
for row in message_files["reads"]:
    if row["path"].endswith("/messages/"):assert row["query"]=={"limit":"30"}
    else:assert row["query"]=={}
for name in ["ios/CRMApp/InboxMessageFilesContent.swift","android/app/src/main/java/kz/zani/mobile/ui/InboxMessageFilesContent.kt"]:
    source=(root/name).read_text();assert all(key in source for key in ["inboxMessageFilesTitle","inboxMessageFilesWindow","fileMetadataEmpty","fileVerificationUnknown","isCurrent"])
    assert "download_url" not in source and "uploaded_by" not in source
for name in ["ios/CRMApp/InboxViewModel.swift","android/app/src/main/java/kz/zani/mobile/ui/InboxViewModel.kt"]:
    source=(root/name).read_text();assert all(key in source for key in ["messageFilesEntryControl","messageFilesPresentationControl","matchesMessageFiles","messageFilesOwner"])
print("PASS:145 first-window/all-row/selected scope +22 anchor +11 raw bounded identity fixture oracles; separate owner-gated GET stages, supplied limit/count/has-more, no cursor/full-history/file-byte/send outcome inference. Swift/Kotlin checks separate")

# Independent four-field presence/raw observation oracle; not native execution.
observations=json.loads((f/"inbox-message-observations.json").read_text())
assert observations["fixture_only"] is True and len(observations["cases"])==78 and len(observations["window_cases"])==138 and len(observations["identity_pairs"])==6
_observed_keys=["status","sent_at","delivered_at","read_at"]
def _observed_shape(row):return all(k not in row or row[k] is None or type(row[k]) is str for k in _observed_keys)
def _observed_projection(row):return {k:dict(kind="missing") if k not in row else dict(kind="null") if row[k] is None else dict(kind="value",raw=row[k]) for k in _observed_keys}
def _observed_state(row):return row.get("status") if row.get("status") in ["received","queued","sent","failed"] else "unknown"
for row in observations["cases"]:
    value=json.loads(row["response_json"]);c=row["context"]
    valid=_message_context(c) and isinstance(value,dict) and type(value.get("id")) is int and value["id"]==c["message"] and type(value.get("conversation")) is int and value["conversation"]==c["conversation"] and _observed_shape(value)
    assert valid==row["valid"],row["name"]
    if valid:assert _observed_projection(value)==row["observed"] and _observed_state(value)==row["state"]
for row in observations["window_cases"]:
    value=json.loads(row["response_json"]);result=_message_window(value,row["context"])
    if result!="invalidPayload" and not all(_observed_shape(x) for x in value["results"]):result="invalidPayload"
    assert result==row["expected"],row["name"]
    if result=="valid":
        selected=next(x for x in value["results"] if x["id"]==row["context"]["message"])
        assert _observed_projection(selected)==row["observed"] and _observed_state(selected)==row["state"]
for row in observations["identity_pairs"]:assert (_observed_projection(row["left"])==_observed_projection(row["right"]))==row["same"]
for name in ["ios/CRMApp/InboxMessageFilesContent.swift","android/app/src/main/java/kz/zani/mobile/ui/InboxMessageFilesContent.kt"]:
    text=(root/name).read_text();assert all(k in text for k in ["messageObservedStatus","messageObservedStatusRaw","messageObservedSentAt","messageObservedDeliveredAt","messageObservedReadAt","messageObservationMissing","messageObservationNull","messageObservationEmpty","messageObservationLimits"])
for name in ["ios/Sources/CRMCore/InboxMessageObservation.swift","android/app/src/main/java/kz/zani/mobile/core/InboxMessageObservation.kt"]:
    text=(root/name).read_text();assert "TaskSnoozeValue" not in text and "DateFormatter" not in text and "InboxMessageState" in text
print("PASS:78 strict presence/raw/status observation +138 combined all-row window +6 identity fixture oracles; same staged read/metadata projection, no timestamp parsing/default/chronology or own unknown-attempt recovery inference. Native execution separate")

# Generic retry-message fixture contract only: no HTTP command execution in this oracle.
retry=json.loads((f/"inbox-retry-message.json").read_text())
assert retry["fixture_only"] is True and len(retry["source_cases"])==67 and len(retry["receipt_cases"])==65

def _retry_source(row,c):
    return isinstance(row,dict) and _message_context(c) and type(row.get("id")) is int and row["id"]==c["message"] and type(row.get("conversation")) is int and row["conversation"]==c["conversation"] and all(type(row.get(k)) is str for k in ["direction","sender_type","text","status"])
def _retry_eligible(row):return row["direction"]=="outbound" and row["sender_type"] in ["client","bot","manager","ai"] and row["status"] in ["received","queued","failed"]
def _retry_receipt(row,source,c):
    return _retry_source(source,c) and _retry_eligible(source) and isinstance(row,dict) and type(row.get("id")) is int and 0<row["id"]<=2147483647 and row["id"]!=c["message"] and type(row.get("conversation")) is int and row["conversation"]==c["conversation"] and row.get("direction")=="outbound" and type(row.get("sender_type")) is str and row["sender_type"]==source["sender_type"] and type(row.get("text")) is str and row["text"]==source["text"] and row.get("status") in ["queued","sent","failed"] and isinstance(row.get("payload_json"),dict) and type(row["payload_json"].get("retry_of_message_id")) is int and row["payload_json"]["retry_of_message_id"]==c["message"] and type(row.get("created_at")) is str and bool(row["created_at"]) and "sent_at" in row and (row["sent_at"] is None or type(row["sent_at"]) is str)
for case in retry["source_cases"]:
    row=json.loads(case["response_json"]);valid=_retry_source(row,case["context"]);assert valid==case["valid"],case["name"]
    assert (valid and _retry_eligible(row))==case["eligible"],case["name"]
for case in retry["receipt_cases"]:assert _retry_receipt(json.loads(case["response_json"]),json.loads(case["source_json"]),retry["context"])==case["valid"],case["name"]
assert len(retry["reads"])==4 and all(_message_window(json.loads(x["response_json"]),dict(retry["context"],**({"business":202,"conversation":951,"message":9512} if "/951/" in x["path"] else {})))=="valid" for x in retry["reads"] if x["path"].endswith("/messages/"))
for case in retry["scenarios"]:assert case["outcome"] in ["response","unknown"] and set(case)<= {"business","conversation","message_id","outcome","status","response_json"}
for path in ["ios/CRMApp/InboxMessageFilesViewModel.swift","android/app/src/main/java/kz/zani/mobile/ui/InboxMessageFilesModel.kt"]:
    source=(root/path).read_text();assert all(k in source for k in ["retryReview","retryRecord","prepareRetry","submitRetry","acknowledgeRetry","commandsBlocked","blocksCommands"])
for path in ["ios/CRMApp/ReplyDraftViewModel.swift","ios/CRMApp/InboxHandoffViewModel.swift","android/app/src/main/java/kz/zani/mobile/ui/ReplyDraftModel.kt","android/app/src/main/java/kz/zani/mobile/ui/InboxHandoffModel.kt"]:assert "!externalCommandBlocked()" in (root/path).read_text()
for path in ["ios/CRMApp/InboxMessageFilesContent.swift","android/app/src/main/java/kz/zani/mobile/ui/InboxMessageFilesContent.kt"]:
    source=(root/path).read_text();assert all(k in source for k in ["inboxRetryUnknown","inboxRetryPrepare","inboxRetrySubmit","inboxRetryResponse","inboxRetryLimits","isCurrent"])
for path in ["ios/Sources/CRMCore/InboxRetryMessage.swift","android/app/src/main/java/kz/zani/mobile/core/InboxRetryMessage.kt"]:
    source=(root/path).read_text();assert "message_id" in source and "retry_of_message_id" in source and "Idempotency-Key" not in source
for path in (root/"android/app/src").rglob("*.kt"):assert chr(0) not in path.read_text(),str(path)
print("PASS:67 independent generic retry-source +65 plain201 raw/scope/new-message/retry-of receipt fixture oracles; exact one-field selector, separate synthetic UPDATE/fake execute, retained unknown and sibling submit barriers. Android lexical NUL guard PASS; native execution separate")
