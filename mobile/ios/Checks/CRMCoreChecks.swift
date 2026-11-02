import Foundation
import CRMCore
import Darwin

struct CheckFailure: Error { let message: String }
struct FixedTransport: ReadTransport {
    let response: ReadResponse
    func get(_ request: ReadRequest) async throws -> ReadResponse { response }
}
actor RecordingTransport: ReadTransport {
    let fixture: FixtureTransport
    var requests: [ReadRequest] = []
    init(_ fixture: FixtureTransport) { self.fixture = fixture }
    func get(_ request: ReadRequest) async throws -> ReadResponse {
        requests.append(request); return try await fixture.get(request)
    }
}
@main struct CRMCoreChecks {
    static func main() async {
        do { try await runChecks() }
        catch {
            FileHandle.standardError.write(Data("FAIL: \(error)\n".utf8))
            exit(1)
        }
    }
    static func runChecks() async throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments.dropFirst().first ?? "../contracts/fixtures")
        var count = 0
        func expect(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
            guard try condition() else { throw CheckFailure(message: message) }
            count += 1
        }
        func failure(_ expected: ReadFailure, _ operation: () async throws -> Void) async throws {
            do { try await operation(); throw CheckFailure(message: "Expected \(expected)") }
            catch let value as ReadFailure { try expect(value == expected, "Wrong failure: \(value)") }
        }
        let recording = RecordingTransport(FixtureTransport(directory: directory))
        let repository = APIReadRepository(transport: recording)
        let bootstrap = try await repository.bootstrap()
        try expect(bootstrap.businesses.map(\.id) == [101, 202], "Bootstrap membership projection")
        var session = AgendaSession(); try session.install(bootstrap)
        let scopeA = try session.begin(businessID: 101, day: "2026-10-28")
        let list = try await repository.appointments(business: 101, day: scopeA.day)
        try expect(try session.receive(list, for: scopeA), "Current list not accepted")
        try expect(session.items.map(\.id) == [501, 502], "List/calendar share one ordered identity set")
        let detail = try await repository.appointment(business: 101, id: 501)
        let initialDetail = try session.beginDetail(id: 501)
        try expect(try session.receive(detail, for: initialDetail), "Detail should be scoped to list identity")
        try expect(session.detail?.appointment.id == session.items.first?.id, "Detail identity changed")
        var changed = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("appointment-101-501.json"))) as! [String: Any]
        var changedItem = changed["appointment"] as! [String: Any]
        changedItem["status"] = "future_status"; changedItem["title"] = NSNull()
        changed["appointment"] = changedItem
        let fresh = try JSONDecoder().decode(AppointmentDetail.self, from: JSONSerialization.data(withJSONObject: changed))
        let refreshedDetail = try session.beginDetail(id: 501)
        _ = try session.receive(fresh, for: refreshedDetail)
        try expect(session.items[0].status == "future_status", "Detail refresh updates same calendar/list record")
        try expect(session.items[0].title == nil, "New redaction must replace old readable title")
        try expect(try session.receive(detail, for: initialDetail) == false, "Older same-ID detail must not replace a newer response")
        try expect(session.items[0].title == nil, "Late detail must not restore redacted text")
        session.clearDetail()
        try expect(try session.receive(detail, for: refreshedDetail) == false, "Back must invalidate pending detail")
        try expect(session.detail == nil && session.detailSelection == nil, "Back must keep detail empty")
        let reopenedDetail = try session.beginDetail(id: 501)
        try expect(reopenedDetail != refreshedDetail, "Reopening same ID requires a new request identity")
        try expect(try session.receive(detail, for: refreshedDetail) == false, "Previous visit cannot populate reopened detail")
        try expect(try session.receive(fresh, for: reopenedDetail), "Reopened detail accepts its own response")
        try await failure(.invalidContext) { _ = try session.beginDetail(id: 999) }
        let nullable = try await repository.appointment(business: 101, id: 502)
        try expect(nullable.details.resource?.id == nil, "Null resource must stay unknown")
        let scopeB = try session.begin(businessID: 202, day: scopeA.day)
        try expect(session.items.isEmpty && session.detail == nil, "Context switch must clear previous data")
        try expect(try session.receive(list, for: scopeA) == false, "Late response must not enter new context")
        try expect(try session.receive(detail, for: reopenedDetail) == false, "Business switch invalidates detail request")
        try await failure(.invalidPayload) { _ = try session.receive(list, for: scopeB) }
        let other = try await repository.appointments(business: 202, day: scopeB.day)
        _ = try session.receive(other, for: scopeB)
        try expect(session.items.map(\.id) == [601], "Business B data only")
        let otherDetail = try session.beginDetail(id: 601)
        try await failure(.invalidPayload) { _ = try session.receive(detail, for: otherDetail) }
        try await failure(.invalidContext) { _ = try session.begin(businessID: 303, day: "2026-10-28") }
        try await failure(.invalidContext) { _ = try session.begin(businessID: 101, day: "2026-02-30") }
        let scope = try session.begin(businessID: 101, day: scopeA.day)
        var duplicate = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("appointments-101.json"))) as! [String: Any]
        let originalItems = duplicate["items"] as! [[String: Any]]
        duplicate["items"] = [originalItems[0], originalItems[0]]
        let duplicated = try JSONDecoder().decode(AppointmentList.self, from: JSONSerialization.data(withJSONObject: duplicate))
        try await failure(.invalidPayload) { _ = try session.receive(duplicated, for: scope) }
        var badItems = originalItems
        badItems[0]["end_at"] = badItems[0]["start_at"]
        duplicate["items"] = badItems
        let badTime = try JSONDecoder().decode(AppointmentList.self, from: JSONSerialization.data(withJSONObject: duplicate))
        _ = try session.receive(badTime, for: scope)
        try expect(session.items.count == 2 && AgendaDayDisplay(items: session.items, day: scope.day, responseDay: session.responseDay, timezone: scope.business.timezone).uncertain.count == 1, "Invalid interval must remain a separate same-ID read row")

        let partial = try JSONDecoder().decode(AppointmentList.self, from: Data(contentsOf: directory.appendingPathComponent("appointments-partial.json")))
        _ = try session.receive(partial, for: scope)
        try expect(session.isPartial && session.items.count == 1, "Server cap cannot look complete")
        let empty = try await repository.appointments(business: 101, day: "2026-10-30")
        let emptyScope = try session.begin(businessID: 101, day: empty.date)
        _ = try session.receive(empty, for: emptyScope)
        try expect(session.items.isEmpty, "Successful empty is not a request error")
        for (status, error) in [(403, ReadFailure.denied), (404, .notFound), (503, .unavailable)] {
            let repo = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: status, data: Data())))
            try await failure(error) { _ = try await repo.bootstrap() }
        }
        let malformed = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 200, data: Data("{}".utf8))))
        try await failure(.invalidPayload) { _ = try await malformed.bootstrap() }
        try await failure(.notFound) { _ = try await repository.appointment(business: 202, id: 501) }
        let requests = await recording.requests
        try expect(requests[0] == ReadRequest(path: "/api/mobile/v1/bootstrap/"), "Bootstrap contract")
        try expect(requests[1] == ReadRequest(path: "/api/mobile/v1/appointments/", query: ["business":"101", "date":"2026-10-28", "limit":"50"]), "List contract")
        try expect(requests[2] == ReadRequest(path: "/api/mobile/v1/appointments/501/", query: ["business":"101"]), "Detail contract")
        let boundary = Appointment.instant("2026-10-27T20:00:00.000Z")!
        try expect(Day.string(boundary, timezone: "Asia/Almaty") == "2026-10-28", "Business timezone day boundary")
        let copyData = try Data(contentsOf: directory.deletingLastPathComponent().appendingPathComponent("ui-copy.json"))
        for (tag, expected) in [("ru-KZ", "ru"), ("KK_kz", "kk"), ("en-US", "en"), ("de-DE", "en"), ("", "en")] {
            let copy = try UICopy(data: copyData, preferredLanguage: tag)
            try expect(copy.language == expected, "UI locale normalization/fallback")
            try expect(!copy.text("appointments").isEmpty, "Missing appointment label")
        }
        try expect(try UICopy(data: copyData, preferredLanguage: "ru").text("resource") == "Специалист", "Current generic CRM term")
        try expect(try UICopy(data: copyData, preferredLanguage: "kk").text("resource") == "Маман", "Current KK term")
        var brokenCopy = try JSONSerialization.jsonObject(with: copyData) as! [String: [String: String]]
        brokenCopy["kk"]?.removeValue(forKey: "resource")
        let brokenData = try JSONSerialization.data(withJSONObject: brokenCopy)
        try await failure(.invalidPayload) { _ = try UICopy(data: brokenData, preferredLanguage: "kk") }
        count += try runNativeRequestChecks()
        count += try runAppointmentLifecycleChecks(directory:directory)
        count += try runAppointmentRescheduleChecks(directory:directory)
        count += try runAppointmentTerminalChecks(directory:directory)
        count += try await runAppointmentBookingChecks(directory:directory)
        count += try runAppointmentBookingCandidateChecks(directory:directory)
        count += try await runServiceDirectoryChecks(directory:directory)
        count += try await runResourceDirectoryChecks(directory:directory)
        count += try await runAppointmentBookingDirectoryChecks(directory:directory)
        count += try await runAppointmentBookingClientChecks(directory:directory)
        count += try runMobileAuthContractChecks(directory:directory)
        count += try await runBackendReadTransportChecks(directory:directory)
        count += try await runReadContractChecks(directory: directory)
        count += try await runClientReadChecks(directory: directory)
        count += try runBootstrapChecks(directory: directory)
        count += try await runInboxReadChecks(directory: directory)
        count += try await runInboxConversationFilesChecks(directory:directory)
        count += try await runInboxMessageFilesChecks(directory:directory)
        count += try runInboxMessageObservationChecks(directory:directory)
        count += try await runInboxRetryMessageChecks(directory:directory)
        count += try await runInboxSelfAssignmentChecks(directory:directory)
        count += try await runInboxReadMarkerChecks(directory:directory)
        count += try await runInboxPriorityChecks(directory:directory)
        count += try await runInboxLifecycleChecks(directory:directory)
        count += try await runInboxLinkClientChecks(directory:directory)
        count += try await runLeadReadChecks(directory:directory)
        count += try await runInboxLinkLeadChecks(directory:directory)
        count += try await runDealReferenceChecks(directory:directory)
        count += try await runInboxLinkDealChecks(directory:directory)
        count += try await runMemberReferenceChecks(directory:directory)
        count += try await runInboxTargetAssignmentChecks(directory:directory)
        count += try await runInboxTaskSourceChecks(directory:directory)
        count += try await runInboxCreateTaskChecks(directory:directory)
        count += try await runInboxExistingClientChecks(directory:directory)
        count += try await runInboxExistingLeadChecks(directory:directory)
        count += try await runInboxExistingDealChecks(directory:directory)
        count += try await runTaskReadChecks(directory: directory)
        count += try await runNotificationReadChecks(directory: directory)
        count += try runNotificationMarkReadChecks(directory: directory)
        count += try await runClientProfileChecks(directory: directory)
        count += try await runHomeTodayChecks(directory: directory)
        count += try await runAttentionQueueChecks(directory: directory)
        count += try await runAgendaDayChecks(directory: directory)
        count += try await runAppointmentRelationsChecks(directory: directory)
        count += try runLoadedSearchChecks(directory:directory)
        count += try await runClientWorkChecks(directory: directory)
        count += try runInboxClientReadChecks(directory: directory)
        count += try runAppointmentStatusChecks(directory: directory)
        count += try runCommunicationTextChecks(directory: directory)
        count += try runClientDraftChecks(directory: directory)
        count += try runReplyDraftChecks(directory: directory)
        count += try runTaskDraftChecks(directory: directory)
        count += try await runClientServerSearchChecks(directory: directory)
        count += try await runQuickReplyChecks(directory: directory)
        count += try await runClientEditChecks(directory: directory)
        count += try await runTaskCommentChecks(directory: directory)
        count += try await runTaskQueryChecks(directory: directory)
        count += try runHandoffReadChecks(directory: directory)
        count += try runTaskCancelReasonChecks(directory: directory)
        count += try runTaskCommentSubmissionChecks(directory: directory)
        count += try runTaskScheduleReadChecks(directory: directory)
        count += try runTaskCancellationChecks(directory: directory)
        count += try runTaskPeopleReadChecks(directory: directory)
        count += try runTaskCommentAuthorChecks(directory: directory)
        count += try runTaskCreateValidationChecks(directory: directory)
        count += try runTaskCreationChecks(directory: directory)
        count += try runClientSourceValidationChecks(directory: directory)
        count += try runClientCreationChecks(directory: directory)
        count += try runInboxMessageStateChecks(directory: directory)
        count += try runRelativeAppointmentCandidateChecks(directory:directory)
        count += try runNotificationMarkUnreadChecks(directory:directory)
        count += try runTaskSnoozeChecks(directory:directory)
        count += try runTaskAssignChecks(directory:directory)
        count += try runTaskDateEditChecks(directory:directory)
        count += try runTaskPriorityEditChecks(directory:directory)
        count += try runTaskTitleEditChecks(directory:directory)
        count += try runTaskDescriptionEditChecks(directory:directory)
        count += try runTaskCreateExactTextChecks(directory:directory)
        count += try runTaskCreateDueChecks(directory:directory)
        count += try runTaskCreateReminderChecks(directory:directory)
        count += try runReplyDraftExactTextChecks(directory:directory)
        count += try runInboxReplyReceiptChecks(directory:directory)
        count += try runInboxHandoffChecks(directory:directory)
        count += try await runAppointmentReferenceChecks(directory:directory)
        count += try await runAppointmentSlotChecks(directory:directory)
        count += try await runAppointmentSlotReviewChecks(directory:directory)
        count += try await runTaskCreateClientChecks(directory:directory)
        count += try await runTaskCreateAppointmentChecks(directory:directory)
        count += try await runTaskCreateParentChecks(directory:directory)
        count += try await runTaskAppointmentEditChecks(directory:directory)
        count += try await runTaskClientEditChecks(directory:directory)
        print("PASS: \(count) Swift native core checks (synthetic fixtures, no network)")
    }
}
