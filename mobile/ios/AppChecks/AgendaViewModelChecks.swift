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
    static let suiteNames:[String] = ["checkAppointmentDate", "checkAgendaControls", "checkAppointmentLifecycle", "checkAppointmentReschedule", "checkAppointmentTerminal", "checkAppointmentBooking", "checkAppointmentBookingCandidate", "checkServiceDirectory", "checkResourceDirectory", "checkAppointmentBookingDirectory", "checkAppointmentBookingClient", "checkAppointmentRelationControls", "checkClientDirectory", "checkClientDirectoryControls", "checkInboxMessageStates", "checkInboxControls", "checkInboxConversationFiles", "checkInboxMessageFiles", "checkInboxMessageObservation", "checkInboxRetryMessage", "checkInboxSelfAssignment", "checkInboxReadMarkers", "checkInboxPriority", "checkInboxLifecycle", "checkInboxLinkClient", "checkLeadReference", "checkInboxLinkLead", "checkDealReference", "checkInboxLinkDeal", "checkMemberReference", "checkInboxTargetAssignment", "checkInboxTaskSource", "checkInboxCreateTask", "checkInboxExistingClient", "checkInboxExistingLead", "checkInboxExistingDeal", "checkInboxInspectorPresentation", "checkInbox", "checkTaskList", "checkTaskListControls", "checkNotificationCenter", "checkNotificationOwnerControls", "checkNotificationRoute", "checkNotificationMarkRead", "checkNotificationMarkUnread", "checkClientProfile", "checkHomeToday", "checkHomeOwnerControls", "checkAttentionQueue", "checkAttentionOwnerControls", "checkAgendaDay", "checkAppointmentRelations", "checkLoadedSearch", "checkLoadedSearchControls", "checkClientWork", "checkClientWorkControls", "checkInboxClient", "checkInboxClientControls", "checkInboxListThreadControls", "checkTaskCompletion", "checkTaskSelfAssignment", "checkTaskStart", "checkTaskReopen", "checkTaskFileMetadata", "checkTaskWatcher", "checkTaskUndoCancel", "checkTaskSnooze", "checkTaskAssign", "checkTaskDateEdit", "checkTaskPriorityEdit", "checkTaskTitleEdit", "checkTaskDescriptionEdit", "checkTaskCreateExactText", "checkTaskCreateDue", "checkTaskCreateReminder", "checkReplyDraftExactText", "checkInboxReplyReceipt", "checkInboxHandoff", "checkAppointmentReferenceDetails", "checkAppointmentSlotRead", "checkAppointmentSlotReview", "checkTaskCreateClient", "checkTaskCreateAppointment", "checkTaskCreateParent", "checkTaskAppointmentEdit", "checkTaskClientEdit", "checkClientDraft", "checkReplyDraft", "checkTaskDraft", "checkClientServerSearch", "checkClientSearchWindows", "checkQuickReplies", "checkQuickReplyControls", "checkClientEdit", "checkClientEditControls", "checkTaskComment", "checkTaskQuery", "checkHandoffRead", "checkTaskCancelReason", "checkTaskCommentSubmission", "checkTaskCommentControls", "checkTaskScheduleRead", "checkTaskCancellation", "checkTaskCancelControls", "checkTaskPeopleRead", "checkTaskCommentAuthor", "checkTaskCreateValidation", "checkTaskCreation", "checkTaskCreateControls", "checkClientSourceValidation", "checkClientCreation", "checkClientCreateControls", "inlineAgenda"]
    @MainActor static func main() async {
        do {
            if CommandLine.arguments.contains("--list") {
                let data=try JSONSerialization.data(withJSONObject:suiteNames)
                print("SUITES "+String(decoding:data,as:UTF8.self));return
            }
            let directory=URL(fileURLWithPath:CommandLine.arguments.dropFirst().first ?? "../contracts/fixtures")
            let selected:[String]
            if let index=CommandLine.arguments.firstIndex(of:"--suite") {
                guard CommandLine.arguments.indices.contains(index+1),suiteNames.contains(CommandLine.arguments[index+1]) else {throw ViewModelCheckFailure(message:"Unknown or missing suite")}
                selected=[CommandLine.arguments[index+1]]
            } else {selected=suiteNames}
            var count=0
            for name in selected {
                FileHandle.standardError.write(Data(("HOST suite START "+name+"\n").utf8))
                let result=try await runSuite(name,directory:directory);count += result
                let data=try JSONSerialization.data(withJSONObject:["suite":name,"status":"PASS","checks":result] as [String:Any],options:.sortedKeys)
                print("SUITE_RESULT "+String(decoding:data,as:UTF8.self))
            }
            print("PASS: \(count) actual SwiftUI ViewModel checks (headless macOS host, synthetic, no network; not an iOS build)")
        } catch {FileHandle.standardError.write(Data("FAIL: \(error)\n".utf8));exit(1)}
    }
    @MainActor static func runSuite(_ name:String,directory:URL) async throws -> Int {
        switch name {
        case "checkAppointmentDate": return try checkAppointmentDate(directory:directory)
        case "checkAgendaControls": return try await checkAgendaControls(directory:directory)
        case "checkAppointmentLifecycle": return try await checkAppointmentLifecycle(directory:directory)
        case "checkAppointmentReschedule": return try await checkAppointmentReschedule(directory:directory)
        case "checkAppointmentTerminal": return try await checkAppointmentTerminal(directory:directory)
        case "checkAppointmentBooking": return try await checkAppointmentBooking(directory:directory)
        case "checkAppointmentBookingCandidate": return try await checkAppointmentBookingCandidate(directory:directory)
        case "checkServiceDirectory": return try await checkServiceDirectory(directory:directory)
        case "checkResourceDirectory": return try await checkResourceDirectory(directory:directory)
        case "checkAppointmentBookingDirectory": return try await checkAppointmentBookingDirectory(directory:directory)
        case "checkAppointmentBookingClient": return try await checkAppointmentBookingClient(directory:directory)
        case "checkAppointmentRelationControls": return try await checkAppointmentRelationControls(directory:directory)
        case "checkClientDirectory": return try await checkClientDirectory(directory:directory)
        case "checkClientDirectoryControls": return try await checkClientDirectoryControls(directory:directory)
        case "checkInboxMessageStates": return try await checkInboxMessageStates(directory:directory)
        case "checkInboxControls": return try await checkInboxControls(directory:directory)
        case "checkInboxConversationFiles": return try await checkInboxConversationFiles(directory:directory)
        case "checkInboxMessageFiles": return try await checkInboxMessageFiles(directory:directory)
        case "checkInboxMessageObservation": return try await checkInboxMessageObservation(directory:directory)
        case "checkInboxRetryMessage": return try await checkInboxRetryMessage(directory:directory)
        case "checkInboxSelfAssignment": return try await checkInboxSelfAssignment(directory:directory)
        case "checkInboxReadMarkers": return try await checkInboxReadMarkers(directory:directory)
        case "checkInboxPriority": return try await checkInboxPriority(directory:directory)
        case "checkInboxLifecycle": return try await checkInboxLifecycle(directory:directory)
        case "checkInboxLinkClient": return try await checkInboxLinkClient(directory:directory)
        case "checkLeadReference": return try await checkLeadReference(directory:directory)
        case "checkInboxLinkLead": return try await checkInboxLinkLead(directory:directory)
        case "checkDealReference": return try await checkDealReference(directory:directory)
        case "checkInboxLinkDeal": return try await checkInboxLinkDeal(directory:directory)
        case "checkMemberReference": return try await checkMemberReference(directory:directory)
        case "checkInboxTargetAssignment": return try await checkInboxTargetAssignment(directory:directory)
        case "checkInboxTaskSource": return try await checkInboxTaskSource(directory:directory)
        case "checkInboxCreateTask": return try await checkInboxCreateTask(directory:directory)
        case "checkInboxExistingClient": return try await checkInboxExistingClient(directory:directory)
        case "checkInboxExistingLead": return try await checkInboxExistingLead(directory:directory)
        case "checkInboxExistingDeal": return try await checkInboxExistingDeal(directory:directory)
        case "checkInboxInspectorPresentation": return try await checkInboxInspectorPresentation(directory:directory)
        case "checkInbox": return try await checkInbox(directory:directory)
        case "checkTaskList": return try await checkTaskList(directory:directory)
        case "checkTaskListControls": return try await checkTaskListControls(directory:directory)
        case "checkNotificationCenter": return try await checkNotificationCenter(directory:directory)
        case "checkNotificationOwnerControls": return try await checkNotificationOwnerControls(directory:directory)
        case "checkNotificationRoute": return try await checkNotificationRoute(directory:directory)
        case "checkNotificationMarkRead": return try await checkNotificationMarkRead(directory:directory)
        case "checkNotificationMarkUnread": return try await checkNotificationMarkUnread(directory:directory)
        case "checkClientProfile": return try await checkClientProfile(directory:directory)
        case "checkHomeToday": return try await checkHomeToday(directory:directory)
        case "checkHomeOwnerControls": return try await checkHomeOwnerControls(directory:directory)
        case "checkAttentionQueue": return try await checkAttentionQueue(directory:directory)
        case "checkAttentionOwnerControls": return try await checkAttentionOwnerControls(directory:directory)
        case "checkAgendaDay": return try await checkAgendaDay(directory:directory)
        case "checkAppointmentRelations": return try await checkAppointmentRelations(directory:directory)
        case "checkLoadedSearch": return try await checkLoadedSearch(directory:directory)
        case "checkLoadedSearchControls": return try await checkLoadedSearchControls(directory:directory)
        case "checkClientWork": return try await checkClientWork(directory:directory)
        case "checkClientWorkControls": return try await checkClientWorkControls(directory:directory)
        case "checkInboxClient": return try await checkInboxClient(directory:directory)
        case "checkInboxClientControls": return try await checkInboxClientControls(directory:directory)
        case "checkInboxListThreadControls": return try await checkInboxListThreadControls(directory:directory)
        case "checkTaskCompletion": return try await checkTaskCompletion(directory:directory)
        case "checkTaskSelfAssignment": return try await checkTaskSelfAssignment(directory:directory)
        case "checkTaskStart": return try await checkTaskStart(directory:directory)
        case "checkTaskReopen": return try await checkTaskReopen(directory:directory)
        case "checkTaskFileMetadata": return try await checkTaskFileMetadata(directory:directory)
        case "checkTaskWatcher": return try await checkTaskWatcher(directory:directory)
        case "checkTaskUndoCancel": return try await checkTaskUndoCancel(directory:directory)
        case "checkTaskSnooze": return try await checkTaskSnooze(directory:directory)
        case "checkTaskAssign": return try await checkTaskAssign(directory:directory)
        case "checkTaskDateEdit": return try await checkTaskDateEdit(directory:directory)
        case "checkTaskPriorityEdit": return try await checkTaskPriorityEdit(directory:directory)
        case "checkTaskTitleEdit": return try await checkTaskTitleEdit(directory:directory)
        case "checkTaskDescriptionEdit": return try await checkTaskDescriptionEdit(directory:directory)
        case "checkTaskCreateExactText": return try await checkTaskCreateExactText(directory:directory)
        case "checkTaskCreateDue": return try await checkTaskCreateDue(directory:directory)
        case "checkTaskCreateReminder": return try await checkTaskCreateReminder(directory:directory)
        case "checkReplyDraftExactText": return try await checkReplyDraftExactText(directory:directory)
        case "checkInboxReplyReceipt": return try await checkInboxReplyReceipt(directory:directory)
        case "checkInboxHandoff": return try await checkInboxHandoff(directory:directory)
        case "checkAppointmentReferenceDetails": return try await checkAppointmentReferenceDetails(directory:directory)
        case "checkAppointmentSlotRead": return try await checkAppointmentSlotRead(directory:directory)
        case "checkAppointmentSlotReview": return try await checkAppointmentSlotReview(directory:directory)
        case "checkTaskCreateClient": return try await checkTaskCreateClient(directory:directory)
        case "checkTaskCreateAppointment": return try await checkTaskCreateAppointment(directory:directory)
        case "checkTaskCreateParent": return try await checkTaskCreateParent(directory:directory)
        case "checkTaskAppointmentEdit": return try await checkTaskAppointmentEdit(directory:directory)
        case "checkTaskClientEdit": return try await checkTaskClientEdit(directory:directory)
        case "checkClientDraft": return try await checkClientDraft(directory:directory)
        case "checkReplyDraft": return try await checkReplyDraft(directory:directory)
        case "checkTaskDraft": return try await checkTaskDraft(directory:directory)
        case "checkClientServerSearch": return try await checkClientServerSearch(directory:directory)
        case "checkClientSearchWindows": return try await checkClientSearchWindows(directory:directory)
        case "checkQuickReplies": return try await checkQuickReplies(directory:directory)
        case "checkQuickReplyControls": return try await checkQuickReplyControls(directory:directory)
        case "checkClientEdit": return try await checkClientEdit(directory:directory)
        case "checkClientEditControls": return try await checkClientEditControls(directory:directory)
        case "checkTaskComment": return try await checkTaskComment(directory:directory)
        case "checkTaskQuery": return try await checkTaskQuery(directory:directory)
        case "checkHandoffRead": return try await checkHandoffRead(directory:directory)
        case "checkTaskCancelReason": return try await checkTaskCancelReason(directory:directory)
        case "checkTaskCommentSubmission": return try await checkTaskCommentSubmission(directory:directory)
        case "checkTaskCommentControls": return try await checkTaskCommentControls(directory:directory)
        case "checkTaskScheduleRead": return try await checkTaskScheduleRead(directory:directory)
        case "checkTaskCancellation": return try await checkTaskCancellation(directory:directory)
        case "checkTaskCancelControls": return try await checkTaskCancelControls(directory:directory)
        case "checkTaskPeopleRead": return try await checkTaskPeopleRead(directory:directory)
        case "checkTaskCommentAuthor": return try await checkTaskCommentAuthor(directory:directory)
        case "checkTaskCreateValidation": return try await checkTaskCreateValidation(directory:directory)
        case "checkTaskCreation": return try await checkTaskCreation(directory:directory)
        case "checkTaskCreateControls": return try await checkTaskCreateControls(directory:directory)
        case "checkClientSourceValidation": return try await checkClientSourceValidation(directory:directory)
        case "checkClientCreation": return try await checkClientCreation(directory:directory)
        case "checkClientCreateControls": return try await checkClientCreateControls(directory:directory)
        case "inlineAgenda": return try await inlineAgenda(directory:directory)
        default: throw ViewModelCheckFailure(message:"Unregistered suite")
        }
    }
    @MainActor static func inlineAgenda(directory:URL) async throws -> Int {
        let data = try Data(contentsOf: directory.appendingPathComponent("appointment-101-501.json"))
        let detail = try JSONDecoder().decode(AppointmentDetail.self, from: data)
        var redactedJSON = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        var item = redactedJSON["appointment"] as! [String: Any]
        item["title"] = NSNull(); redactedJSON["appointment"] = item
        let redacted = try JSONDecoder().decode(AppointmentDetail.self, from: JSONSerialization.data(withJSONObject: redactedJSON))
        let repository = ControlledRepository(directory: directory)
        let model = AgendaViewModel(repository: repository, initialDate: Appointment.instant("2026-10-28T07:00:00Z")!)
        var count = 0
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
        return count
    }
}
