import Foundation
import CRMCore

func runInboxReadChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws {
        guard value else { throw CheckFailure(message: message) }; count += 1
    }
    func changed(_ change: (inout [String: Any]) -> Void) throws -> InboxThread {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("inbox-101-901.json"))) as! [String: Any]
        change(&json)
        return try JSONDecoder().decode(InboxThread.self, from: JSONSerialization.data(withJSONObject: json))
    }
    let source = RecordingTransport(FixtureTransport(directory: directory))
    let repository = APIReadRepository(transport: source)
    let page = try await repository.inbox(business: 101)
    let detail = try await repository.thread(business: 101, id: 901)
    try expect(page.valid(for: 101) && page.items.map(\.id) == [901, 902], "Inbox projection or scope changed")
    try expect(detail.valid(for: 101, id: 901) && detail.messages.map(\.id) == [9011, 9012], "Message identity/order changed")
    let requests = await source.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/inbox/", query: ["business":"101", "limit":"50"]), ReadRequest(path: "/api/mobile/v1/inbox/901/", query: ["business":"101", "limit":"30"])], "Inbox read invented a route/query")
    let empty = try await repository.thread(business: 101, id: 902)
    try expect(empty.valid(for: 101, id: 902) && empty.messages.isEmpty && !empty.windowCapped, "Successful empty thread changed")
    do { _ = try await repository.thread(business: 101, id: 0); throw CheckFailure(message: "Invalid thread ID reached transport") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong thread context error") }
    let afterInvalid = await source.requests
    try expect(afterInvalid.count == 3, "Invalid thread ID issued a request")
    let foreign = try changed { json in
        var messages = json["messages"] as! [[String: Any]]; messages[0]["conversation_id"] = 902; json["messages"] = messages
    }
    try expect(!foreign.valid(for: 101, id: 901), "Foreign conversation message accepted")
    let duplicates = try changed { json in
        let messages = json["messages"] as! [[String: Any]]; json["messages"] = [messages[0], messages[0]]
    }
    try expect(!duplicates.valid(for: 101, id: 901), "Duplicate message identities accepted")
    let capped = try changed { $0["payload_budget"] = ["max_messages": 2] }
    try expect(capped.valid(for: 101, id: 901) && capped.windowCapped, "Capped thread looked like full history")
    let withheld = try changed { json in
        var conversation = json["conversation"] as! [String: Any]; conversation["title"] = NSNull(); json["conversation"] = conversation
        var messages = json["messages"] as! [[String: Any]]; messages[0]["text"] = NSNull(); messages[0]["sender_type"] = "future_actor"; json["messages"] = messages
    }
    try expect(withheld.conversation.title == nil && withheld.messages[0].text == nil && withheld.messages[0].sender_type == "future_actor", "Null or unknown sender was reinterpreted")
    let malformed = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 200, data: Data("{\"business\":\"101\",\"items\":[],\"summary\":{\"open\":0}}".utf8))))
    do { _ = try await malformed.inbox(business: 101); throw CheckFailure(message: "String Business ID coerced") }
    catch let error as ReadFailure { try expect(error == .invalidPayload, "Wrong Inbox type error") }
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 403, data: Data())))
    do { _ = try await denied.thread(business: 101, id: 901); throw CheckFailure(message: "Denied thread was accepted") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong thread denied error") }
    return count
}
