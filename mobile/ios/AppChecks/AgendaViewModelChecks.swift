import Foundation
import CRMCore
import Darwin

// Console-only checks of the actual ViewModel using the host macOS SwiftUI module.
// No App/Scene, window, simulator, device or network transport is constructed.
actor ControlledRepository: AgendaRepository {
    private let fixtures: APIReadRepository
    private var nextRequest = 0
    private var pending: [Int: CheckedContinuation<AppointmentDetail, any Error>] = [:]
    private var waiters: [Int: CheckedContinuation<Void, Never>] = [:]
    private let holdFirstBootstrap: Bool
    private let failFirstBootstrap: Bool
    private var bootstrapRequests = 0
    private var bootstrapWaiter: CheckedContinuation<Void, Never>?
    private var heldBootstrap: CheckedContinuation<Void, Never>?
    private var listResults: [Result<AppointmentList, ReadFailure>] = []
    init(directory: URL, holdFirstBootstrap: Bool = false, failFirstBootstrap: Bool = false) {
        fixtures = APIReadRepository(transport: FixtureTransport(directory: directory))
        self.holdFirstBootstrap = holdFirstBootstrap
        self.failFirstBootstrap = failFirstBootstrap
    }
    func bootstrap() async throws -> Bootstrap {
        bootstrapRequests += 1
        bootstrapWaiter?.resume(); bootstrapWaiter = nil
        if failFirstBootstrap && bootstrapRequests == 1 { throw ReadFailure.unavailable }
        if holdFirstBootstrap && bootstrapRequests == 1 {
            await withCheckedContinuation { heldBootstrap = $0 }
        }
        return try await fixtures.bootstrap()
    }
    func waitForBootstrapRequest() async {
        if bootstrapRequests > 0 { return }
        await withCheckedContinuation { bootstrapWaiter = $0 }
    }
    func bootstrapRequestCount() -> Int { bootstrapRequests }
    func releaseBootstrap() { heldBootstrap?.resume(); heldBootstrap = nil }
    func appointments(business: Int, day: String) async throws -> AppointmentList {
        if !listResults.isEmpty { return try listResults.removeFirst().get() }
        return try await fixtures.appointments(business: business, day: day)
    }
    func enqueueList(_ result: Result<AppointmentList, ReadFailure>) { listResults.append(result) }
    func appointment(business: Int, id: Int) async throws -> AppointmentDetail {
        let request = nextRequest; nextRequest += 1
        return try await withCheckedThrowingContinuation { continuation in
            pending[request] = continuation
            waiters.removeValue(forKey: request)?.resume()
        }
    }
    func waitForRequest(_ request: Int) async {
        if pending[request] != nil { return }
        await withCheckedContinuation { waiters[request] = $0 }
    }
    func resolve(_ request: Int, with result: Result<AppointmentDetail, ReadFailure>) {
        guard let continuation = pending.removeValue(forKey: request) else { preconditionFailure("Missing controlled request") }
        switch result {
        case .success(let detail): continuation.resume(returning: detail)
        case .failure(let error): continuation.resume(throwing: error)
        }
    }
}

struct ViewModelCheckFailure: Error { let message: String }
@main struct AgendaViewModelChecks {
    @MainActor static func main() async {
        do { try await runChecks() }
        catch {
            FileHandle.standardError.write(Data("FAIL: \(error)\n".utf8))
            exit(1)
        }
    }
    @MainActor static func runChecks() async throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1])
        let data = try Data(contentsOf: directory.appendingPathComponent("appointment-101-501.json"))
        let detail = try JSONDecoder().decode(AppointmentDetail.self, from: data)
        var redactedJSON = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        var item = redactedJSON["appointment"] as! [String: Any]
        item["title"] = NSNull(); redactedJSON["appointment"] = item
        let redacted = try JSONDecoder().decode(AppointmentDetail.self, from: JSONSerialization.data(withJSONObject: redactedJSON))
        let repository = ControlledRepository(directory: directory)
        let model = AgendaViewModel(repository: repository, initialDate: Appointment.instant("2026-10-28T07:00:00Z")!)
        var count = try checkAppointmentDate(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAgendaControls\n".utf8))
        count += try await checkAgendaControls(directory: directory)
        count += try await checkAppointmentLifecycle(directory: directory)
        count += try await checkAppointmentReschedule(directory: directory)
        count += try await checkAppointmentTerminal(directory: directory)
        count += try await checkAppointmentBooking(directory: directory)
        count += try await checkAppointmentBookingCandidate(directory: directory)
        count += try await checkServiceDirectory(directory: directory)
        count += try await checkResourceDirectory(directory: directory)
        count += try await checkAppointmentBookingDirectory(directory: directory)
        count += try await checkAppointmentBookingClient(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAppointmentRelationControls\n".utf8))
        count += try await checkAppointmentRelationControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientDirectory\n".utf8))
        count += try await checkClientDirectory(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientDirectoryControls\n".utf8))
        count += try await checkClientDirectoryControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInboxMessageStates\n".utf8))
        count += try await checkInboxMessageStates(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInboxControls\n".utf8))
        count += try await checkInboxControls(directory: directory)
        count += try await checkInboxConversationFiles(directory:directory)
        count += try await checkInboxMessageFiles(directory:directory)
        count += try await checkInboxMessageObservation(directory:directory)
        count += try await checkInboxRetryMessage(directory:directory)
        count += try await checkInboxSelfAssignment(directory:directory)
        count += try await checkInboxReadMarkers(directory:directory)
        count += try await checkInboxPriority(directory:directory)
        count += try await checkInboxLifecycle(directory:directory)
        count += try await checkInboxLinkClient(directory:directory)
        count += try await checkLeadReference(directory:directory)
        count += try await checkInboxLinkLead(directory:directory)
        count += try await checkDealReference(directory:directory)
        count += try await checkInboxLinkDeal(directory:directory)
        count += try await checkMemberReference(directory:directory)
        count += try await checkInboxTargetAssignment(directory:directory)
        count += try await checkInboxTaskSource(directory:directory)
        count += try await checkInboxCreateTask(directory:directory)
        count += try await checkInboxExistingClient(directory:directory)
        count += try await checkInboxExistingLead(directory:directory)
        count += try await checkInboxExistingDeal(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkInboxInspectorPresentation\n".utf8))
        count += try await checkInboxInspectorPresentation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInbox\n".utf8))
        count += try await checkInbox(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskList\n".utf8))
        count += try await checkTaskList(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskListControls\n".utf8))
        count += try await checkTaskListControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkNotificationCenter\n".utf8))
        count += try await checkNotificationCenter(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkNotificationOwnerControls\n".utf8))
        count += try await checkNotificationOwnerControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkNotificationRoute\n".utf8))
        count += try await checkNotificationRoute(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkNotificationMarkRead\n".utf8))
        count += try await checkNotificationMarkRead(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkNotificationMarkUnread\n".utf8))
        count += try await checkNotificationMarkUnread(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkClientProfile\n".utf8))
        count += try await checkClientProfile(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkHomeToday\n".utf8))
        count += try await checkHomeToday(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkHomeOwnerControls\n".utf8))
        count += try await checkHomeOwnerControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAttentionQueue\n".utf8))
        count += try await checkAttentionQueue(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAttentionOwnerControls\n".utf8))
        count += try await checkAttentionOwnerControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAgendaDay\n".utf8))
        count += try await checkAgendaDay(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkAppointmentRelations\n".utf8))
        count += try await checkAppointmentRelations(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkLoadedSearch\n".utf8))
        count += try await checkLoadedSearch(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkLoadedSearchControls\n".utf8))
        count += try await checkLoadedSearchControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientWork\n".utf8))
        count += try await checkClientWork(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientWorkControls\n".utf8))
        count += try await checkClientWorkControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInboxClient\n".utf8))
        count += try await checkInboxClient(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInboxClientControls\n".utf8))
        count += try await checkInboxClientControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkInboxListThreadControls\n".utf8))
        count += try await checkInboxListThreadControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCompletion\n".utf8))
        count += try await checkTaskCompletion(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskSelfAssignment\n".utf8))
        count += try await checkTaskSelfAssignment(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskStart\n".utf8))
        count += try await checkTaskStart(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskReopen\n".utf8))
        count += try await checkTaskReopen(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskFileMetadata\n".utf8))
        count += try await checkTaskFileMetadata(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskWatcher\n".utf8))
        count += try await checkTaskWatcher(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskUndoCancel\n".utf8))
        count += try await checkTaskUndoCancel(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskSnooze\n".utf8))
        count += try await checkTaskSnooze(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskAssign\n".utf8))
        count += try await checkTaskAssign(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskDateEdit\n".utf8))
        count += try await checkTaskDateEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskPriorityEdit\n".utf8))
        count += try await checkTaskPriorityEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskTitleEdit\n".utf8))
        count += try await checkTaskTitleEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskDescriptionEdit\n".utf8))
        count += try await checkTaskDescriptionEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateExactText\n".utf8))
        count += try await checkTaskCreateExactText(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateDue\n".utf8))
        count += try await checkTaskCreateDue(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateReminder\n".utf8))
        count += try await checkTaskCreateReminder(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkReplyDraftExactText\n".utf8))
        count += try await checkReplyDraftExactText(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkInboxReplyReceipt\n".utf8))
        count += try await checkInboxReplyReceipt(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkInboxHandoff\n".utf8))
        count += try await checkInboxHandoff(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkAppointmentReferenceDetails\n".utf8))
        count += try await checkAppointmentReferenceDetails(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkAppointmentSlotRead\n".utf8))
        count += try await checkAppointmentSlotRead(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkAppointmentSlotReview\n".utf8))
        count += try await checkAppointmentSlotReview(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateClient\n".utf8))
        count += try await checkTaskCreateClient(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateAppointment\n".utf8))
        count += try await checkTaskCreateAppointment(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateParent\n".utf8))
        count += try await checkTaskCreateParent(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskAppointmentEdit\n".utf8))
        count += try await checkTaskAppointmentEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkTaskClientEdit\n".utf8))
        count += try await checkTaskClientEdit(directory:directory)
        FileHandle.standardError.write(Data("HOST group checkClientDraft\n".utf8))
        count += try await checkClientDraft(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkReplyDraft\n".utf8))
        count += try await checkReplyDraft(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskDraft\n".utf8))
        count += try await checkTaskDraft(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientServerSearch\n".utf8))
        count += try await checkClientServerSearch(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientSearchWindows\n".utf8))
        count += try await checkClientSearchWindows(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkQuickReplies\n".utf8))
        count += try await checkQuickReplies(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkQuickReplyControls\n".utf8))
        count += try await checkQuickReplyControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientEdit\n".utf8))
        count += try await checkClientEdit(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientEditControls\n".utf8))
        count += try await checkClientEditControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskComment\n".utf8))
        count += try await checkTaskComment(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskQuery\n".utf8))
        count += try await checkTaskQuery(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkHandoffRead\n".utf8))
        count += try await checkHandoffRead(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCancelReason\n".utf8))
        count += try await checkTaskCancelReason(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCommentSubmission\n".utf8))
        count += try await checkTaskCommentSubmission(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCommentControls\n".utf8))
        count += try await checkTaskCommentControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskScheduleRead\n".utf8))
        count += try await checkTaskScheduleRead(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCancellation\n".utf8))
        count += try await checkTaskCancellation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCancelControls\n".utf8))
        count += try await checkTaskCancelControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskPeopleRead\n".utf8))
        count += try await checkTaskPeopleRead(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCommentAuthor\n".utf8))
        count += try await checkTaskCommentAuthor(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateValidation\n".utf8))
        count += try await checkTaskCreateValidation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreation\n".utf8))
        count += try await checkTaskCreation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkTaskCreateControls\n".utf8))
        count += try await checkTaskCreateControls(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientSourceValidation\n".utf8))
        count += try await checkClientSourceValidation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientCreation\n".utf8))
        count += try await checkClientCreation(directory: directory)
        FileHandle.standardError.write(Data("HOST group checkClientCreateControls\n".utf8))
        count += try await checkClientCreateControls(directory: directory)
        func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
            guard condition() else { throw ViewModelCheckFailure(message: message) }
            count += 1
        }
        let startupRepository = ControlledRepository(directory: directory, holdFirstBootstrap: true)
        let startupModel = AgendaViewModel(repository: startupRepository, initialDate: model.date)
        let starting = Task { await startupModel.start() }
        await startupRepository.waitForBootstrapRequest()
        await startupModel.start()
        let startupRequests = await startupRepository.bootstrapRequestCount()
        let remainedPending = startupModel.loading && startupModel.session.businesses.isEmpty
        await startupRepository.releaseBootstrap(); await starting.value
        try expect(startupRequests == 1, "Concurrent start issued duplicate bootstrap requests")
        try expect(remainedPending, "Duplicate start replaced the pending bootstrap state")
        try expect(!startupModel.loading && startupModel.failure == nil && startupModel.session.items.map(\.id) == [501, 502], "Single bootstrap did not complete the list")

        let recoveringRepository = ControlledRepository(directory: directory, failFirstBootstrap: true)
        let recoveringModel = AgendaViewModel(repository: recoveringRepository, initialDate: model.date)
        await recoveringModel.start()
        try expect(!recoveringModel.loading && recoveringModel.failure == .unavailable && recoveringModel.session.businesses.isEmpty, "Bootstrap failure did not expose a retryable state")
        await recoveringModel.start()
        let recoveryRequests = await recoveringRepository.bootstrapRequestCount()
        try expect(recoveryRequests == 2 && !recoveringModel.loading && recoveringModel.failure == nil && recoveringModel.session.items.map(\.id) == [501, 502], "Bootstrap retry did not recover the original fixture context")

        let listRepository = ControlledRepository(directory: directory)
        let listModel = AgendaViewModel(repository: listRepository, initialDate: model.date)
        await listModel.start()
        let listScope = listModel.session.selection!
        let partialEmpty = try JSONDecoder().decode(AppointmentList.self, from: Data(contentsOf: directory.appendingPathComponent("appointments-partial-empty-101.json")))
        let empty = try JSONDecoder().decode(AppointmentList.self, from: Data(contentsOf: directory.appendingPathComponent("appointments-empty-101.json")))
        await listRepository.enqueueList(.success(partialEmpty))
        await listModel.load(business: listScope.business.id)
        try expect(listModel.session.isPartial && listModel.session.items.isEmpty, "Synthetic partial-zero fixture did not load")
        try expect(!listModel.showsEmptyResult, "Partial zero items was labelled as an empty day")
        for problem in [ReadFailure.unavailable, .denied] {
            await listRepository.enqueueList(.failure(problem))
            await listModel.load(business: listScope.business.id)
            try expect(listModel.failure == problem && !listModel.loading && !listModel.showsEmptyResult, "List failure was presented as an empty success")
            try expect(listModel.session.selection?.business == listScope.business && listModel.session.selection?.day == listScope.day, "Error/retry lost Business or day")
        }
        await listRepository.enqueueList(.success(empty))
        await listModel.load(business: listScope.business.id)
        try expect(listModel.showsEmptyResult && !listModel.loading && listModel.failure == nil && !listModel.session.isPartial, "Complete empty retry did not clear the earlier error/partial state")
        try expect(listModel.session.selection?.business == listScope.business && listModel.session.selection?.day == listScope.day && listModel.session.detail == nil, "Empty retry lost context or restored detail")
        let initialModel = AgendaViewModel(repository: listRepository, initialDate: model.date)
        try expect(!initialModel.showsEmptyResult, "Initial unknown state was presented as an empty result")

        await model.start()
        try expect(model.session.items.map(\.id) == [501, 502], "Fixture bootstrap/list did not load")

        let first = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(0)
        let retry = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(1)
        await repository.resolve(1, with: .success(redacted)); await retry.value
        await repository.resolve(0, with: .success(detail)); await first.value
        try expect(model.session.detail?.appointment.id == 501, "Current detail identity changed")
        try expect(model.session.items[0].title == nil, "Older same-ID success restored redacted list text")
        try expect(model.session.detail?.appointment.title == nil, "Older same-ID success replaced current detail")

        let staleError = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(2)
        let current = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(3)
        await repository.resolve(2, with: .failure(.unavailable)); await staleError.value
        try expect(model.detailFailure == nil && model.detailLoading, "Old error changed the newer request state")
        await repository.resolve(3, with: .failure(.denied)); await current.value
        try expect(model.detailFailure == .denied && !model.detailLoading, "Current failure must remain visible and retryable")

        let leaving = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(4); model.closeDetail()
        await repository.resolve(4, with: .failure(.unavailable)); await leaving.value
        try expect(model.session.detail == nil && model.detailFailure == nil && !model.detailLoading, "Back was repopulated by a late error")

        let previousVisit = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(5); model.closeDetail()
        let reopened = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(6)
        await repository.resolve(5, with: .success(detail)); await previousVisit.value
        try expect(model.session.detail == nil && model.detailLoading, "Previous visit populated a reopened same-ID detail")
        await repository.resolve(6, with: .success(redacted)); await reopened.value
        try expect(model.session.detail?.appointment.id == 501 && !model.detailLoading, "Reopened request did not complete")

        let oldBusiness = Task { await model.loadDetail(id: 501) }
        await repository.waitForRequest(7); await model.load(business: 202)
        await repository.resolve(7, with: .success(detail)); await oldBusiness.value
        try expect(model.session.items.map(\.id) == [601] && model.session.detail == nil, "Old Business detail entered the new context")
        try expect(model.detailFailure == nil && !model.detailLoading, "Old Business response changed detail UI state")
        print("PASS: \(count) actual SwiftUI ViewModel checks (headless macOS host, synthetic, no network; not an iOS build)")
    }
}
