#!/usr/bin/env python3
"""Bounded synthetic host diagnostics. Every admitted suite runs at most once."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

SUITE_MANIFEST = {'core': ['runAppointmentLifecycleChecks', 'runAppointmentRescheduleChecks', 'runAppointmentTerminalChecks', 'runAppointmentBookingChecks', 'runAppointmentBookingCandidateChecks', 'runServiceDirectoryChecks', 'runResourceDirectoryChecks', 'runAppointmentBookingDirectoryChecks', 'runAppointmentBookingClientChecks', 'runMobileAuthContractChecks', 'runBackendReadTransportChecks', 'runReadContractChecks', 'runClientReadChecks', 'runBootstrapChecks', 'runInboxReadChecks', 'runInboxConversationFilesChecks', 'runInboxMessageFilesChecks', 'runInboxMessageObservationChecks', 'runInboxRetryMessageChecks', 'runInboxSelfAssignmentChecks', 'runInboxReadMarkerChecks', 'runInboxPriorityChecks', 'runInboxLifecycleChecks', 'runInboxLinkClientChecks', 'runLeadReadChecks', 'runInboxLinkLeadChecks', 'runDealReferenceChecks', 'runInboxLinkDealChecks', 'runMemberReferenceChecks', 'runInboxTargetAssignmentChecks', 'runInboxTaskSourceChecks', 'runInboxCreateTaskChecks', 'runInboxExistingClientChecks', 'runInboxExistingLeadChecks', 'runInboxExistingDealChecks', 'runTaskReadChecks', 'runNotificationReadChecks', 'runNotificationMarkReadChecks', 'runClientProfileChecks', 'runHomeTodayChecks', 'runAttentionQueueChecks', 'runAgendaDayChecks', 'runAppointmentRelationsChecks', 'runLoadedSearchChecks', 'runClientWorkChecks', 'runInboxClientReadChecks', 'runAppointmentStatusChecks', 'runCommunicationTextChecks', 'runClientDraftChecks', 'runReplyDraftChecks', 'runTaskDraftChecks', 'runClientServerSearchChecks', 'runQuickReplyChecks', 'runClientEditChecks', 'runTaskCommentChecks', 'runTaskQueryChecks', 'runHandoffReadChecks', 'runTaskCancelReasonChecks', 'runTaskCommentSubmissionChecks', 'runTaskScheduleReadChecks', 'runTaskCancellationChecks', 'runTaskPeopleReadChecks', 'runTaskCommentAuthorChecks', 'runTaskCreateValidationChecks', 'runTaskCreationChecks', 'runClientSourceValidationChecks', 'runClientCreationChecks', 'runInboxMessageStateChecks', 'runRelativeAppointmentCandidateChecks', 'runNotificationMarkUnreadChecks', 'runTaskSnoozeChecks', 'runTaskAssignChecks', 'runTaskDateEditChecks', 'runTaskPriorityEditChecks', 'runTaskTitleEditChecks', 'runTaskDescriptionEditChecks', 'runTaskCreateExactTextChecks', 'runTaskCreateDueChecks', 'runTaskCreateReminderChecks', 'runReplyDraftExactTextChecks', 'runInboxReplyReceiptChecks', 'runInboxHandoffChecks', 'runAppointmentReferenceChecks', 'runAppointmentSlotChecks', 'runAppointmentSlotReviewChecks', 'runTaskCreateClientChecks', 'runTaskCreateAppointmentChecks', 'runTaskCreateParentChecks', 'runTaskAppointmentEditChecks', 'runTaskClientEditChecks', 'inlineCore'], 'view-model': ['checkAppointmentDate', 'checkAgendaControls', 'checkAppointmentLifecycle', 'checkAppointmentReschedule', 'checkAppointmentTerminal', 'checkAppointmentBooking', 'checkAppointmentBookingCandidate', 'checkServiceDirectory', 'checkResourceDirectory', 'checkAppointmentBookingDirectory', 'checkAppointmentBookingClient', 'checkAppointmentRelationControls', 'checkClientDirectory', 'checkClientDirectoryControls', 'checkInboxMessageStates', 'checkInboxControls', 'checkInboxConversationFiles', 'checkInboxMessageFiles', 'checkInboxMessageObservation', 'checkInboxRetryMessage', 'checkInboxSelfAssignment', 'checkInboxReadMarkers', 'checkInboxPriority', 'checkInboxLifecycle', 'checkInboxLinkClient', 'checkLeadReference', 'checkInboxLinkLead', 'checkDealReference', 'checkInboxLinkDeal', 'checkMemberReference', 'checkInboxTargetAssignment', 'checkInboxTaskSource', 'checkInboxCreateTask', 'checkInboxExistingClient', 'checkInboxExistingLead', 'checkInboxExistingDeal', 'checkInboxInspectorPresentation', 'checkInbox', 'checkTaskList', 'checkTaskListControls', 'checkNotificationCenter', 'checkNotificationOwnerControls', 'checkNotificationRoute', 'checkNotificationMarkRead', 'checkNotificationMarkUnread', 'checkClientProfile', 'checkHomeToday', 'checkHomeOwnerControls', 'checkAttentionQueue', 'checkAttentionOwnerControls', 'checkAgendaDay', 'checkAppointmentRelations', 'checkLoadedSearch', 'checkLoadedSearchControls', 'checkClientWork', 'checkClientWorkControls', 'checkInboxClient', 'checkInboxClientControls', 'checkInboxListThreadControls', 'checkTaskCompletion', 'checkTaskSelfAssignment', 'checkTaskStart', 'checkTaskReopen', 'checkTaskFileMetadata', 'checkTaskWatcher', 'checkTaskUndoCancel', 'checkTaskSnooze', 'checkTaskAssign', 'checkTaskDateEdit', 'checkTaskPriorityEdit', 'checkTaskTitleEdit', 'checkTaskDescriptionEdit', 'checkTaskCreateExactText', 'checkTaskCreateDue', 'checkTaskCreateReminder', 'checkReplyDraftExactText', 'checkInboxReplyReceipt', 'checkInboxHandoff', 'checkAppointmentReferenceDetails', 'checkAppointmentSlotRead', 'checkAppointmentSlotReview', 'checkTaskCreateClient', 'checkTaskCreateAppointment', 'checkTaskCreateParent', 'checkTaskAppointmentEdit', 'checkTaskClientEdit', 'checkClientDraft', 'checkReplyDraft', 'checkTaskDraft', 'checkClientServerSearch', 'checkClientSearchWindows', 'checkQuickReplies', 'checkQuickReplyControls', 'checkClientEdit', 'checkClientEditControls', 'checkTaskComment', 'checkTaskQuery', 'checkHandoffRead', 'checkTaskCancelReason', 'checkTaskCommentSubmission', 'checkTaskCommentControls', 'checkTaskScheduleRead', 'checkTaskCancellation', 'checkTaskCancelControls', 'checkTaskPeopleRead', 'checkTaskCommentAuthor', 'checkTaskCreateValidation', 'checkTaskCreation', 'checkTaskCreateControls', 'checkClientSourceValidation', 'checkClientCreation', 'checkClientCreateControls', 'inlineAgenda']}
INTERNAL_SECONDS = 285
WORK_SECONDS = 270
SUITE_SECONDS = 15
CAP_BYTES = 2147483648
RESERVE_BYTES = 2147483648
LOG_LIMIT_BYTES = 67108864
DIAGNOSTICS = ['-v', '-Xfrontend', '-debug-time-function-bodies', '-Xfrontend', '-warn-long-expression-type-checking=200']

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)

def event(kind, **details):
    print(json.dumps({'atUtc': utc(), 'event': kind, **details}, sort_keys=True), flush=True)

def allocated(root):
    return sum(p.stat().st_blocks * 512 for p in root.rglob('*') if p.is_file())

class StopPacket(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status

class Packet:
    def __init__(self, mode, root, output, inputs):
        self.mode, self.root, self.output, self.inputs = mode, root.resolve(), output.resolve(), inputs
        self.started = time.monotonic()
        self.work_deadline = self.started + WORK_SECONDS
        self.deadline = self.started + INTERNAL_SECONDS
        self.report = {'mode': mode, 'status': 'RUNNING', 'atUtc': utc(), 'limits': {'internalSeconds': INTERNAL_SECONDS, 'workSeconds': WORK_SECONDS, 'suiteSeconds': SUITE_SECONDS, 'artifactCapBytes': CAP_BYTES, 'diskReserveBytes': RESERVE_BYTES, 'lane': 1}, 'phases': [], 'suites': []}
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / 'logs').mkdir(exist_ok=True)
        self.phase_number = 0

    def save(self):
        self.report['elapsedSeconds'] = round(time.monotonic() - self.started, 3)
        write_json(self.output / (self.mode + '-report.json'), self.report)

    def resources(self):
        disk = os.statvfs(self.output)
        free = disk.f_bavail * disk.f_frsize
        size = allocated(self.output)
        if free < RESERVE_BYTES or size > CAP_BYTES:
            raise StopPacket('RESOURCE_BLOCKED', 'Artifact cap or free-disk reserve reached')
        return {'freeBytes': free, 'allocatedArtifactBytes': size}

    def phase(self, name, command, maximum=None, echo_tail=True):
        remaining = self.work_deadline - time.monotonic()
        if remaining <= 0:
            raise StopPacket('TIMEOUT', 'Packet work deadline reached before ' + name)
        budget = min(remaining, maximum if maximum is not None else remaining)
        if budget <= 2:
            raise StopPacket('TIMEOUT', 'No safe child termination window before ' + name)
        self.resources()
        self.phase_number += 1
        log = self.output / 'logs' / (self.mode + '-' + str(self.phase_number).zfill(3) + '-' + name + '.log')
        start = time.monotonic()
        event('START', mode=self.mode, phase=name, budgetSeconds=round(budget, 3), command=command, log=log.name)
        status, code = 'PASS', None
        child = None
        reason = None
        try:
            with log.open('wb') as sink:
                child = subprocess.Popen(command, stdout=sink, stderr=subprocess.STDOUT, start_new_session=True)
                next_resource = start
                while child.poll() is None:
                    now = time.monotonic()
                    if now >= start + budget - 2:
                        status, reason = 'TIMEOUT', 'Child or packet deadline'
                        break
                    if now >= next_resource:
                        self.resources()
                        if log.stat().st_size > LOG_LIMIT_BYTES:
                            raise StopPacket('RESOURCE_BLOCKED', 'Diagnostic log limit reached')
                        next_resource = now + 2
                    time.sleep(min(0.1, max(0.01, start + budget - 2 - now)))
                if status == 'TIMEOUT':
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=min(1, max(0.1, self.deadline - time.monotonic())))
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                code = child.wait(timeout=1)
                if status == 'PASS' and code != 0:
                    status = 'CRASH' if code < 0 else 'FAIL'
        except BaseException as error:
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=1)
            row = {'phase': name, 'status': error.status if isinstance(error, StopPacket) else 'STARTUP_FAIL', 'exitCode': child.returncode if child is not None else None, 'elapsedSeconds': round(time.monotonic()-start,3), 'log': str(log.relative_to(self.output)), 'reason': str(error)}
            self.report['phases'].append(row)
            self.save()
            event('END', mode=self.mode, **row)
            raise
        row = {'phase': name, 'status': status, 'exitCode': code, 'elapsedSeconds': round(time.monotonic() - start, 3), 'log': str(log.relative_to(self.output)), 'reason': reason}
        self.report['phases'].append(row)
        self.save()
        event('END', mode=self.mode, **row)
        if echo_tail:
            with log.open('rb') as stream:
                stream.seek(max(0, log.stat().st_size - 24000))
                print(stream.read().decode(errors='replace'), flush=True)
        return row, log

    def must(self, name, command, maximum=None):
        row, log = self.phase(name, command, maximum)
        if row['status'] != 'PASS':
            raise StopPacket('BUILD_FAIL' if row['status'] == 'FAIL' else row['status'], name + ' did not complete successfully')
        return log.read_text(errors='replace')

    def input_rows(self, paths):
        return [{'path': str(p.relative_to(self.root)), 'sha256': digest(p)} for p in paths]

    def run(self):
        source = sorted((self.root / 'ios/Sources/CRMCore').glob('*.swift'))
        checks = [Path(p).resolve() for p in self.inputs]
        if not source or not checks or any(not p.is_file() or not p.is_relative_to(self.root) for p in checks):
            raise StopPacket('STARTUP_FAIL', 'Missing or foreign compiler input')
        if self.mode == 'view-model':
            app_inputs = [p for p in checks if p.parent == self.root / 'ios/CRMApp']
            if len(app_inputs) != 89 or len(set(app_inputs)) != 89:
                raise StopPacket('STARTUP_FAIL', 'Expected exact89 App inputs')
        version = self.must('toolchain', ['swiftc', '--version'], 10).strip()
        sdk = self.must('sdk', ['xcrun', '--show-sdk-path'], 10).strip()
        help_text = self.must('diagnostic-support', ['swiftc', '-frontend', '-help-hidden'], 10)
        if not all(flag in help_text for flag in ['-debug-time-function-bodies', '-warn-long-expression-type-checking']):
            raise StopPacket('BLOCKED', 'Selected diagnostic compiler flags are unsupported; no fallback probe')
        sha = self.must('source-sha', ['git', '-C', str(self.root), 'rev-parse', 'HEAD'], 10).strip()
        cache = self.output / 'module-cache'
        cache.mkdir(exist_ok=True)
        base = ['swiftc', '-swift-version', '6']
        library = base + ['-emit-library', '-emit-module', '-module-name', 'CRMCore', '-module-cache-path', str(cache)] + [str(p) for p in source] + ['-emit-module-path', str(self.output / 'CRMCore.swiftmodule'), '-o', str(self.output / 'libCRMCore.dylib')]
        core_identity = {'compiler': version, 'sdk': sdk, 'inputs': self.input_rows(source), 'baseCommand': library, 'diagnosticFlags': DIAGNOSTICS}
        fixtures = sorted((self.root / 'contracts/fixtures').glob('*.json')) + [self.root / 'contracts/ui-copy.json']
        manifest = {'sourceSha': sha, 'compiler': version, 'sdk': sdk, 'coreIdentity': core_identity, 'checkInputs': self.input_rows(checks), 'fixtureInputs': self.input_rows(fixtures), 'diagnosticFlags': DIAGNOSTICS, 'resources': self.resources(), 'limits': self.report['limits']}
        self.report['sourceSha'] = sha
        write_json(self.output / (self.mode + '-inputs.json'), manifest)
        event('INPUT_MANIFEST', mode=self.mode, sha=sha, sourceCount=len(source), checkInputCount=len(checks), compiler=version, sdk=sdk, **manifest['resources'], limits=self.report['limits'])
        receipt_path = self.output / 'shared-core.json'
        if self.mode == 'core':
            self.must('compile-core-library', library + DIAGNOSTICS)
            artifacts = [self.output / 'CRMCore.swiftmodule', self.output / 'libCRMCore.dylib']
            if any(not p.is_file() or p.stat().st_size == 0 for p in artifacts):
                raise StopPacket('BUILD_FAIL', 'Shared Core output missing')
            receipt = {'identity': core_identity, 'sourceSha': sha, 'artifacts': [{'path': str(p), 'sha256': digest(p)} for p in artifacts]}
            write_json(receipt_path, receipt)
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                    stream.write('shared_core_ready=true\n')
        else:
            if not receipt_path.is_file():
                raise StopPacket('BLOCKED', 'Shared Core manifest absent; no automatic rebuild')
            receipt = json.loads(receipt_path.read_text())
            if receipt['identity'] != core_identity or receipt['sourceSha'] != sha or any(not Path(row['path']).is_file() or digest(Path(row['path'])) != row['sha256'] for row in receipt['artifacts']):
                raise StopPacket('BLOCKED', 'Shared Core manifest mismatch; no reuse/rebuild')
            event('VERIFIED_REUSE', mode=self.mode, sourceSha=sha, artifactCount=len(receipt['artifacts']))
        binary = self.output / ('CRMCoreChecks' if self.mode == 'core' else 'AgendaViewModelChecks')
        command = base + ['-parse-as-library', '-I', str(self.output), '-L', str(self.output), '-lCRMCore', '-Xlinker', '-rpath', '-Xlinker', str(self.output), '-module-cache-path', str(cache)] + [str(p) for p in checks] + ['-o', str(binary)]
        self.must('compile-checks', command + DIAGNOSTICS)
        listing = self.must('list-suites', [str(binary), str(self.root / 'contracts/fixtures'), '--list'], 10)
        lists = [json.loads(l[len('SUITES '):]) for l in listing.splitlines() if l.startswith('SUITES ')]
        if lists != [SUITE_MANIFEST[self.mode]]:
            raise StopPacket('STARTUP_FAIL', 'Suite registry mismatch, missing or duplicate suite')
        self.report['expectedSuites'] = SUITE_MANIFEST[self.mode]
        for name in SUITE_MANIFEST[self.mode]:
            if self.work_deadline - time.monotonic() <= 2:
                break
            row, log = self.phase('suite-' + name, [str(binary), str(self.root / 'contracts/fixtures'), '--suite', name], SUITE_SECONDS)
            status, count = row['status'], None
            if status == 'PASS':
                results = [json.loads(l[len('SUITE_RESULT '):]) for l in log.read_text(errors='replace').splitlines() if l.startswith('SUITE_RESULT ')]
                if len(results) != 1 or results[0].get('suite') != name or results[0].get('status') != 'PASS' or type(results[0].get('checks')) is not int or results[0]['checks'] < 0:
                    status = 'STARTUP_FAIL'
                else:
                    count = results[0]['checks']
            elif status == 'FAIL':
                status = 'ASSERTION_FAIL'
            self.report['suites'].append({'suite': name, 'status': status, 'checks': count, 'phase': row['phase'], 'log': row['log'], 'elapsedSeconds': row['elapsedSeconds'], 'exitCode': row['exitCode']})
            self.save()
        self.report['status'] = 'PASS' if len(self.report['suites']) == len(SUITE_MANIFEST[self.mode]) and all(r['status'] == 'PASS' for r in self.report['suites']) else 'FAIL'

    def finish(self):
        done = {r['suite'] for r in self.report['suites']}
        for name in SUITE_MANIFEST[self.mode]:
            if name not in done:
                self.report['suites'].append({'suite': name, 'status': 'NOT_RUN', 'reason': self.report.get('reason', 'Packet budget exhausted')})
        self.report['passedChecks'] = sum(r.get('checks') or 0 for r in self.report['suites'] if r['status'] == 'PASS')
        self.report['completedAtUtc'] = utc()
        self.save()
        event('PACKET_RESULT', mode=self.mode, status=self.report['status'], elapsedSeconds=self.report['elapsedSeconds'], suiteStatuses={s: sum(r['status']==s for r in self.report['suites']) for s in sorted({r['status'] for r in self.report['suites']})}, passedChecks=self.report['passedChecks'])

def summary(output):
    rows = []
    for mode in ['core', 'view-model']:
        path = output / (mode + '-report.json')
        rows.append(json.loads(path.read_text()) if path.is_file() else {'mode': mode, 'status': 'BLOCKED', 'reason': 'Report absent'})
    result = {'status': 'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL', 'packets': rows}
    write_json(output / 'aggregate-report.json', result)
    event('AGGREGATE_RESULT', status=result['status'], packets=[{'mode':r['mode'],'status':r['status'],'reason':r.get('reason')} for r in rows])
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('Synthetic host diagnostics: '+result['status']+'\n\n')
            for row in rows:
                stream.write('- '+row['mode']+': '+row['status']+'\n')
                for suite in row.get('suites', []):
                    if suite['status'] != 'PASS':
                        stream.write('  - '+suite['suite']+': '+suite['status']+'\n')
    return 0 if result['status']=='PASS' else 1

if __name__ == '__main__':
    mode, root, output = sys.argv[1:4]
    if mode == 'summary':
        Path(output).mkdir(parents=True, exist_ok=True)
        sys.exit(summary(Path(output)))
    if mode not in SUITE_MANIFEST:
        raise SystemExit('Unknown diagnostic packet')
    packet = Packet(mode, Path(root), Path(output), sys.argv[4:])
    try:
        packet.run()
    except StopPacket as error:
        packet.report.update(status=error.status, reason=str(error))
    except Exception as error:
        packet.report.update(status='STARTUP_FAIL', reason=type(error).__name__+': '+str(error))
    packet.finish()
    sys.exit(0 if packet.report['status']=='PASS' else 1)
