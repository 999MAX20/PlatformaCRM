import Foundation
import CRMCore

func runNotificationMarkReadChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    func decode<T:Decodable>(_ value:Any,_ type:T.Type) throws -> T {try JSONDecoder().decode(type,from:JSONSerialization.data(withJSONObject:value))}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("notification-mark-read.json"))) as! [String:Any]
    let context=NotificationMarkReadContext(business:101,notification:2101,epoch:1)
    let grant=SyntheticNotificationMarkReadGrant(business:101,notification:2101,actor:9001,update:true),auth=grant.authorization(for:context)!
    try expect(!NotificationMarkReadContext(business:0,notification:2101,epoch:1).valid,"Invalid scope accepted")
    try expect(SyntheticNotificationMarkReadGrant(business:101,notification:2101,actor:9001,update:false).authorization(for:context)==nil,"GET/VIEW inferred UPDATE")
    try expect(grant.authorization(for:NotificationMarkReadContext(business:202,notification:2101,epoch:1))==nil,"Cross-Business grant")
    try expect(grant.authorization(for:NotificationMarkReadContext(business:101,notification:2102,epoch:1))==nil,"Cross-target grant")
    try expect(SyntheticNotificationMarkReadGrant(business:101,notification:2101,actor:0,update:true).authorization(for:context)==nil,"Missing actor accepted")
    let cases=catalog["validation_cases"] as! [[String:Any]]
    for row in cases {
        let name=row["name"] as! String,n=try decode(row["source"]!,CRMNotification.self)
        let source=NotificationMarkReadSource(context:context,generation:1,notification:n)
        let review=NotificationMarkReadReview(source:source,generation:1)
        var ledger=NotificationMarkReadLedger();let attempt=ledger.begin(review,authorization:auth)!
        try expect(ledger.begin(review,authorization:auth)==nil,"Duplicate pending: \(name)")
        do {
            let reply=try decode(row["reply"]!,NotificationMarkReadReply.self)
            try expect(row["decode"] as! Bool,"Wrong type decoded: \(name)")
            ledger.complete(attempt,outcome:.response(status:row["status"] as! Int,reply:reply))
        } catch is DecodingError {
            try expect(!(row["decode"] as! Bool),"Valid envelope failed decode: \(name)")
            ledger.complete(attempt,outcome:.unknown)
        }
        let confirmed=row["confirmed"] as! Bool
        try expect(ledger.records[0].phase == (confirmed ? .confirmed:.unknown),"Outcome mismatch: \(name)")
        try expect(ledger.records[0].attempt.review.source==source,"Immutable input changed: \(name)")
        try expect(ledger.acknowledge(auth)==confirmed,"Unknown cleared or terminal not acknowledged: \(name)")
        ledger.complete(attempt,outcome:.rejectedWithoutWrite)
        try expect(ledger.records[0].phase == (confirmed ? .confirmed:.unknown),"Late second completion replaced result: \(name)")
    }
    let row=cases[0],n=try decode(row["source"]!,CRMNotification.self),source=NotificationMarkReadSource(context:context,generation:1,notification:n)
    var ledger=NotificationMarkReadLedger();let review=NotificationMarkReadReview(source:source,generation:1),a=ledger.begin(review,authorization:auth)!
    ledger.complete(a,outcome:.unknown)
    let newer=NotificationMarkReadContext(business:101,notification:2101,epoch:2),newAuth=grant.authorization(for:newer)!
    try expect(ledger.blocked(newer) && ledger.visible(newAuth)==nil && !ledger.acknowledge(newAuth),"Epoch revealed/cleared unknown or allowed replay")
    let reread=NotificationMarkReadSource(context:newer,generation:2,notification:n)
    try expect(ledger.begin(NotificationMarkReadReview(source:reread,generation:2),authorization:newAuth)==nil,"Matching reread proved outcome")
    try expect(!ledger.blocked(NotificationMarkReadContext(business:202,notification:2101,epoch:2)) && !ledger.blocked(NotificationMarkReadContext(business:101,notification:2102,epoch:2)),"Unknown blocked independent target")
    var rejected=NotificationMarkReadLedger();let first=rejected.begin(review,authorization:auth)!
    rejected.complete(first,outcome:.rejectedWithoutWrite)
    try expect(rejected.begin(review,authorization:auth)==nil,"No-write implicitly cleared attempt")
    try expect(rejected.acknowledge(auth),"Definitive no-write not acknowledged")
    let next=rejected.begin(NotificationMarkReadReview(source:source,generation:2),authorization:auth)!
    try expect(next.localID != first.localID && rejected.records.count==2,"Fresh attempt overwrote retained history")
    return count
}
