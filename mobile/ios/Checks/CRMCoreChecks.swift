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
    static let suiteNames:[String] = ["runAppointmentLifecycleChecks", "runAppointmentRescheduleChecks", "runAppointmentTerminalChecks", "runAppointmentBookingChecks", "runAppointmentBookingCandidateChecks", "runServiceDirectoryChecks", "runResourceDirectoryChecks", "runAppointmentBookingDirectoryChecks", "runAppointmentBookingClientChecks", "runMobileAuthContractChecks", "runBackendReadTransportChecks", "runReadContractChecks", "runClientReadChecks", "runBootstrapChecks", "runInboxReadChecks", "runInboxConversationFilesChecks", "runInboxMessageFilesChecks", "runInboxMessageObservationChecks", "runInboxRetryMessageChecks", "runInboxSelfAssignmentChecks", "runInboxReadMarkerChecks", "runInboxPriorityChecks", "runInboxLifecycleChecks", "runInboxLinkClientChecks", "runLeadReadChecks", "runInboxLinkLeadChecks", "runDealReferenceChecks", "runInboxLinkDealChecks", "runMemberReferenceChecks", "runInboxTargetAssignmentChecks", "runInboxTaskSourceChecks", "runInboxCreateTaskChecks", "runInboxExistingClientChecks", "runInboxExistingLeadChecks", "runInboxExistingDealChecks", "runTaskReadChecks", "runNotificationReadChecks", "runNotificationMarkReadChecks", "runClientProfileChecks", "runHomeTodayChecks", "runAttentionQueueChecks", "runAgendaDayChecks", "runAppointmentRelationsChecks", "runLoadedSearchChecks", "runClientWorkChecks", "runInboxClientReadChecks", "runAppointmentStatusChecks", "runCommunicationTextChecks", "runClientDraftChecks", "runReplyDraftChecks", "runTaskDraftChecks", "runClientServerSearchChecks", "runQuickReplyChecks", "runClientEditChecks", "runTaskCommentChecks", "runTaskQueryChecks", "runHandoffReadChecks", "runTaskCancelReasonChecks", "runTaskCommentSubmissionChecks", "runTaskScheduleReadChecks", "runTaskCancellationChecks", "runTaskPeopleReadChecks", "runTaskCommentAuthorChecks", "runTaskCreateValidationChecks", "runTaskCreationChecks", "runClientSourceValidationChecks", "runClientCreationChecks", "runInboxMessageStateChecks", "runRelativeAppointmentCandidateChecks", "runNotificationMarkUnreadChecks", "runTaskSnoozeChecks", "runTaskAssignChecks", "runTaskDateEditChecks", "runTaskPriorityEditChecks", "runTaskTitleEditChecks", "runTaskDescriptionEditChecks", "runTaskCreateExactTextChecks", "runTaskCreateDueChecks", "runTaskCreateReminderChecks", "runReplyDraftExactTextChecks", "runInboxReplyReceiptChecks", "runInboxHandoffChecks", "runAppointmentReferenceChecks", "runAppointmentSlotChecks", "runAppointmentSlotReviewChecks", "runTaskCreateClientChecks", "runTaskCreateAppointmentChecks", "runTaskCreateParentChecks", "runTaskAppointmentEditChecks", "runTaskClientEditChecks", "inlineCore"]
    static func main() async {
        do {
            if CommandLine.arguments.contains("--list") {
                let data=try JSONSerialization.data(withJSONObject:suiteNames)
                print("SUITES "+String(decoding:data,as:UTF8.self));return
            }
            let directory=URL(fileURLWithPath:CommandLine.arguments.dropFirst().first ?? "../contracts/fixtures")
            let selected:[String]
            if let index=CommandLine.arguments.firstIndex(of:"--suite") {
                guard CommandLine.arguments.indices.contains(index+1),suiteNames.contains(CommandLine.arguments[index+1]) else {throw CheckFailure(message:"Unknown or missing suite")}
                selected=[CommandLine.arguments[index+1]]
            } else {selected=suiteNames}
            var count=0
            for name in selected {
                FileHandle.standardError.write(Data(("HOST suite START "+name+"\n").utf8))
                let result=try await runSuite(name,directory:directory);count += result
                let data=try JSONSerialization.data(withJSONObject:["suite":name,"status":"PASS","checks":result] as [String:Any],options:.sortedKeys)
                print("SUITE_RESULT "+String(decoding:data,as:UTF8.self))
            }
            print("PASS: \(count) Swift native core checks (synthetic fixtures, no network)")
        } catch {FileHandle.standardError.write(Data("FAIL: \(error)\n".utf8));exit(1)}
    }
    static func runSuite(_ name:String,directory:URL) async throws -> Int {
        switch name {
        case "runAppointmentLifecycleChecks": return try runAppointmentLifecycleChecks(directory:directory)
        case "runAppointmentRescheduleChecks": return try runAppointmentRescheduleChecks(directory:directory)
        case "runAppointmentTerminalChecks": return try runAppointmentTerminalChecks(directory:directory)
        case "runAppointmentBookingChecks": return try await runAppointmentBookingChecks(directory:directory)
        case "runAppointmentBookingCandidateChecks": return try runAppointmentBookingCandidateChecks(directory:directory)
        case "runServiceDirectoryChecks": return try await runServiceDirectoryChecks(directory:directory)
        case "runResourceDirectoryChecks": return try await runResourceDirectoryChecks(directory:directory)
        case "runAppointmentBookingDirectoryChecks": return try await runAppointmentBookingDirectoryChecks(directory:directory)
        case "runAppointmentBookingClientChecks": return try await runAppointmentBookingClientChecks(directory:directory)
        case "runMobileAuthContractChecks": return try runMobileAuthContractChecks(directory:directory)
        case "runBackendReadTransportChecks": return try await runBackendReadTransportChecks(directory:directory)
        case "runReadContractChecks": return try await runReadContractChecks(directory:directory)
        case "runClientReadChecks": return try await runClientReadChecks(directory:directory)
        case "runBootstrapChecks": return try runBootstrapChecks(directory:directory)
        case "runInboxReadChecks": return try await runInboxReadChecks(directory:directory)
        case "runInboxConversationFilesChecks": return try await runInboxConversationFilesChecks(directory:directory)
        case "runInboxMessageFilesChecks": return try await runInboxMessageFilesChecks(directory:directory)
        case "runInboxMessageObservationChecks": return try runInboxMessageObservationChecks(directory:directory)
        case "runInboxRetryMessageChecks": return try await runInboxRetryMessageChecks(directory:directory)
        case "runInboxSelfAssignmentChecks": return try await runInboxSelfAssignmentChecks(directory:directory)
        case "runInboxReadMarkerChecks": return try await runInboxReadMarkerChecks(directory:directory)
        case "runInboxPriorityChecks": return try await runInboxPriorityChecks(directory:directory)
        case "runInboxLifecycleChecks": return try await runInboxLifecycleChecks(directory:directory)
        case "runInboxLinkClientChecks": return try await runInboxLinkClientChecks(directory:directory)
        case "runLeadReadChecks": return try await runLeadReadChecks(directory:directory)
        case "runInboxLinkLeadChecks": return try await runInboxLinkLeadChecks(directory:directory)
        case "runDealReferenceChecks": return try await runDealReferenceChecks(directory:directory)
        case "runInboxLinkDealChecks": return try await runInboxLinkDealChecks(directory:directory)
        case "runMemberReferenceChecks": return try await runMemberReferenceChecks(directory:directory)
        case "runInboxTargetAssignmentChecks": return try await runInboxTargetAssignmentChecks(directory:directory)
        case "runInboxTaskSourceChecks": return try await runInboxTaskSourceChecks(directory:directory)
        case "runInboxCreateTaskChecks": return try await runInboxCreateTaskChecks(directory:directory)
        case "runInboxExistingClientChecks": return try await runInboxExistingClientChecks(directory:directory)
        case "runInboxExistingLeadChecks": return try await runInboxExistingLeadChecks(directory:directory)
        case "runInboxExistingDealChecks": return try await runInboxExistingDealChecks(directory:directory)
        case "runTaskReadChecks": return try await runTaskReadChecks(directory:directory)
        case "runNotificationReadChecks": return try await runNotificationReadChecks(directory:directory)
        case "runNotificationMarkReadChecks": return try runNotificationMarkReadChecks(directory:directory)
        case "runClientProfileChecks": return try await runClientProfileChecks(directory:directory)
        case "runHomeTodayChecks": return try await runHomeTodayChecks(directory:directory)
        case "runAttentionQueueChecks": return try await runAttentionQueueChecks(directory:directory)
        case "runAgendaDayChecks": return try await runAgendaDayChecks(directory:directory)
        case "runAppointmentRelationsChecks": return try await runAppointmentRelationsChecks(directory:directory)
        case "runLoadedSearchChecks": return try runLoadedSearchChecks(directory:directory)
        case "runClientWorkChecks": return try await runClientWorkChecks(directory:directory)
        case "runInboxClientReadChecks": return try runInboxClientReadChecks(directory:directory)
        case "runAppointmentStatusChecks": return try runAppointmentStatusChecks(directory:directory)
        case "runCommunicationTextChecks": return try runCommunicationTextChecks(directory:directory)
        case "runClientDraftChecks": return try runClientDraftChecks(directory:directory)
        case "runReplyDraftChecks": return try runReplyDraftChecks(directory:directory)
        case "runTaskDraftChecks": return try runTaskDraftChecks(directory:directory)
        case "runClientServerSearchChecks": return try await runClientServerSearchChecks(directory:directory)
        case "runQuickReplyChecks": return try await runQuickReplyChecks(directory:directory)
        case "runClientEditChecks": return try await runClientEditChecks(directory:directory)
        case "runTaskCommentChecks": return try await runTaskCommentChecks(directory:directory)
        case "runTaskQueryChecks": return try await runTaskQueryChecks(directory:directory)
        case "runHandoffReadChecks": return try runHandoffReadChecks(directory:directory)
        case "runTaskCancelReasonChecks": return try runTaskCancelReasonChecks(directory:directory)
        case "runTaskCommentSubmissionChecks": return try runTaskCommentSubmissionChecks(directory:directory)
        case "runTaskScheduleReadChecks": return try runTaskScheduleReadChecks(directory:directory)
        case "runTaskCancellationChecks": return try runTaskCancellationChecks(directory:directory)
        case "runTaskPeopleReadChecks": return try runTaskPeopleReadChecks(directory:directory)
        case "runTaskCommentAuthorChecks": return try runTaskCommentAuthorChecks(directory:directory)
        case "runTaskCreateValidationChecks": return try runTaskCreateValidationChecks(directory:directory)
        case "runTaskCreationChecks": return try runTaskCreationChecks(directory:directory)
        case "runClientSourceValidationChecks": return try runClientSourceValidationChecks(directory:directory)
        case "runClientCreationChecks": return try runClientCreationChecks(directory:directory)
        case "runInboxMessageStateChecks": return try runInboxMessageStateChecks(directory:directory)
        case "runRelativeAppointmentCandidateChecks": return try runRelativeAppointmentCandidateChecks(directory:directory)
        case "runNotificationMarkUnreadChecks": return try runNotificationMarkUnreadChecks(directory:directory)
        case "runTaskSnoozeChecks": return try runTaskSnoozeChecks(directory:directory)
        case "runTaskAssignChecks": return try runTaskAssignChecks(directory:directory)
        case "runTaskDateEditChecks": return try runTaskDateEditChecks(directory:directory)
        case "runTaskPriorityEditChecks": return try runTaskPriorityEditChecks(directory:directory)
        case "runTaskTitleEditChecks": return try runTaskTitleEditChecks(directory:directory)
        case "runTaskDescriptionEditChecks": return try runTaskDescriptionEditChecks(directory:directory)
        case "runTaskCreateExactTextChecks": return try runTaskCreateExactTextChecks(directory:directory)
        case "runTaskCreateDueChecks": return try runTaskCreateDueChecks(directory:directory)
        case "runTaskCreateReminderChecks": return try runTaskCreateReminderChecks(directory:directory)
        case "runReplyDraftExactTextChecks": return try runReplyDraftExactTextChecks(directory:directory)
        case "runInboxReplyReceiptChecks": return try runInboxReplyReceiptChecks(directory:directory)
        case "runInboxHandoffChecks": return try runInboxHandoffChecks(directory:directory)
        case "runAppointmentReferenceChecks": return try await runAppointmentReferenceChecks(directory:directory)
        case "runAppointmentSlotChecks": return try await runAppointmentSlotChecks(directory:directory)
        case "runAppointmentSlotReviewChecks": return try await runAppointmentSlotReviewChecks(directory:directory)
        case "runTaskCreateClientChecks": return try await runTaskCreateClientChecks(directory:directory)
        case "runTaskCreateAppointmentChecks": return try await runTaskCreateAppointmentChecks(directory:directory)
        case "runTaskCreateParentChecks": return try await runTaskCreateParentChecks(directory:directory)
        case "runTaskAppointmentEditChecks": return try await runTaskAppointmentEditChecks(directory:directory)
        case "runTaskClientEditChecks": return try await runTaskClientEditChecks(directory:directory)
        case "inlineCore": return try await inlineCore(directory:directory)
        default: throw CheckFailure(message:"Unregistered suite")
        }
    }
    static func inlineCore(directory:URL) async throws -> Int {
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
        return count
    }
}
