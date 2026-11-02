import Foundation

public enum TaskDueFilter: String,CaseIterable,Sendable {case all="",today,overdue}
public struct TaskQuerySelection: Equatable,Sendable {
    public let business: Int;public let epoch: Int;public let revision: Int
    public init(business: Int,epoch: Int,revision: Int) {self.business=business;self.epoch=epoch;self.revision=revision}
}
public struct TaskDetailSelection: Equatable,Sendable {
    public let business: Int;public let task: Int;public let epoch: Int?;public let listRevision: Int;public let revision: Int
    public init(business: Int,task: Int,epoch: Int?,listRevision: Int,revision: Int) {self.business=business;self.task=task;self.epoch=epoch;self.listRevision=listRevision;self.revision=revision}
}
public struct TaskQueryFilter: Equatable,Sendable {
    public let status: String?;public let due: TaskDueFilter
    public init(status: String?=nil,due: TaskDueFilter = .all) {self.status=status?.isEmpty==false ? status:nil;self.due=due}
    public func request(business: Int) -> ReadRequest {
        var query=["business":String(business),"limit":"50"]
        if let status {query["status"]=status};if due != .all {query["due"]=due.rawValue}
        return ReadRequest(path:"/api/mobile/v1/tasks/",query:query)
    }
}
public protocol TaskQueryRepository: TaskReadRepository {func tasks(business: Int,filter: TaskQueryFilter) async throws -> TaskPage}

// Precomputed source responses from an explicitly clocked offline producer.
// No local date/status filtering or runtime clock/Business-timezone inference.
public enum FixtureTaskQueries {
    public static func response(_ data: Data,business: Int,query: [String:String],id: Int?=nil) throws -> ReadResponse {
        guard let object=try JSONSerialization.jsonObject(with:data) as? [String:Any],object["fixture_only"] as? Bool==true,object["business"] as? Int==business else {throw ReadFailure.invalidPayload}
        var payload: Any?
        if let id {payload=(object["profiles"] as? [String:Any])?[String(id)]}
        else {
            guard Set(query.keys).isSubset(of:["business","limit","status","due"]),query["limit"]=="50",let due=TaskDueFilter(rawValue:query["due"] ?? "") else {return ReadResponse(status:400,data:Data())}
            payload=(object["queries"] as? [String:Any])?[(query["status"] ?? "")+"|"+due.rawValue]
            if payload==nil,query["status"]?.isEmpty==false,var empty=(object["queries"] as? [String:Any])?["|"+due.rawValue] as? [String:Any] {
                empty["items"]=[] as [Any];empty["summary"]=["total":0,"open":0,"today":0,"overdue":0];payload=empty
            }
        }
        guard let payload else {return ReadResponse(status:404,data:Data())}
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:payload))
    }
}
