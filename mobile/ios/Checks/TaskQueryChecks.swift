import Foundation
import CRMCore

func runTaskQueryChecks(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let record=RecordingTransport(FixtureTransport(directory:directory,taskQueries:true)),repo=APIReadRepository(transport:record)
    for business in [101,202] {
        let all=try await repo.tasks(business:business,filter:TaskQueryFilter())
        try expect(all.summary.total==(business==101 ? 73:71) && all.items.count==50,"Fixture default count/limit changed")
        let overdue=try await repo.tasks(business:business,filter:TaskQueryFilter(due:.overdue))
        try expect(overdue.summary.total==66 && overdue.items.count==50 && overdue.items.allSatisfy {$0.status != "done" && $0.status != "cancelled"},"Overdue lost prelimit count or retained terminal tasks")
        let today=try await repo.tasks(business:business,filter:TaskQueryFilter(due:.today)),start=business==101 ? 3100:4100
        try expect(today.summary.total==(business==101 ? 6:5) && today.items.contains(where:{$0.id==start+66 && $0.status=="done"}) && today.items.contains(where:{$0.id==start+67 && $0.status=="cancelled"}),"Today invented terminal exclusion")
        try expect(!today.items.contains(where:{$0.id==start}) && today.items.contains(where:{$0.id==start+68}),"Fixture today was replaced by Business/device calendar")
        let open=try await repo.tasks(business:business,filter:TaskQueryFilter(status:"open",due:.today))
        try expect(open.summary.total==2 && open.items.allSatisfy {$0.status=="open"},"Status+due were not intersected before count")
        let empty=try await repo.tasks(business:business,filter:TaskQueryFilter(status:"done",due:.overdue))
        try expect(empty.summary.total==0 && empty.items.isEmpty,"Source-confirmed empty response changed")
        let nullDue=try await repo.tasks(business:business,filter:TaskQueryFilter(status:"in_progress"))
        if business==101 {try expect(nullDue.items.last?.due_at==nil && !today.items.contains(where:{$0.id==1102}),"Null due was assigned a synthetic date or wrong NULL order")}
        let selected=overdue.items[0]
        let detail=try await repo.taskDetails(business:business,id:selected.id)
        try expect(detail.valid(for:business,id:selected.id) && detail.task==selected,"Query row was reused as fake independent detail")
    }
    let requests=await record.requests
    try expect(requests[0]==ReadRequest(path:"/api/mobile/v1/tasks/",query:["business":"101","limit":"50"]),"Clear/default query invented filter parameters")
    try expect(requests[3]==ReadRequest(path:"/api/mobile/v1/tasks/",query:["business":"101","limit":"50","status":"open","due":"today"]),"Exact query values or mobile path changed")
    let wire=try NativeRequestBuilder(origin:URL(string:"https://fixtures.invalid")!,timeout:30).request(for:requests[3])
    try expect(wire.httpMethod=="GET" && wire.url?.query=="business=101&due=today&limit=50&status=open","Pure construction changed query/verb")
    let data=try Data(contentsOf:directory.appendingPathComponent("task-query-source-101.json"))
    for alias in ["past","future","none","upcoming"] {
        let response=try FixtureTaskQueries.response(data,business:101,query:["business":"101","limit":"50","due":alias])
        try expect(response.status==400,"Unsupported web due alias silently used all tasks")
    }
    for extra in ["search","cursor"] {
        try expect(try FixtureTaskQueries.response(data,business:101,query:["business":"101","limit":"50",extra:"value"]).status==400,"Fixture accepted invented query")
    }
    let active=try FixtureTaskQueries.response(data,business:101,query:["business":"101","limit":"50","status":"active"])
    try expect(try JSONDecoder().decode(TaskPage.self,from:active.data).summary.total==0,"Web active token was invented as native status union")
    let baseline=FixtureTransport(directory:directory)
    try expect(try await baseline.get(requests[3]).status==400,"Default fixture silently ignored source filters")
    return count
}
