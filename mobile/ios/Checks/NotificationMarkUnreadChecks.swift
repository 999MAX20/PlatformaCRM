import Foundation
import CRMCore

func runNotificationMarkUnreadChecks(directory:URL) throws -> Int {
    let data=try Data(contentsOf:directory.appendingPathComponent("notification-mark-unread.json")),catalog=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    let rows=catalog["validation_cases"] as! [[String:Any]]
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    for row in rows {
        let n=try JSONDecoder().decode(CRMNotification.self,from:JSONSerialization.data(withJSONObject:row["source"]!))
        let s=NotificationMarkUnreadSource(context:NotificationMarkUnreadContext(business:101,notification:2102,epoch:1),generation:1,notification:n),grant=SyntheticNotificationMarkUnreadGrant(business:101,notification:2102,actor:9001,update:true)
        let auth=grant.authorization(for:s.context)!,review=NotificationMarkUnreadReview(source:s,generation:1)
        var ledger=NotificationMarkUnreadLedger();let a=ledger.begin(review,authorization:auth)!
        let result=Result {try JSONDecoder().decode(NotificationMarkUnreadReply.self,from:JSONSerialization.data(withJSONObject:row["reply"]!))}
        let decodes:Bool;if case .success=result {decodes=true}else {decodes=false}
        try expect(decodes==(row["decode"] as! Bool),"Unread decoder \(row["name"]!)")
        switch result {case .success(let reply):ledger.complete(a,outcome:.response(status:row["status"] as! Int,reply:reply));case .failure:ledger.complete(a,outcome:.unknown)}
        let confirmed=row["confirmed"] as! Bool
        try expect(ledger.records[0].phase == (confirmed ? .confirmed:.unknown),"Unread outcome \(row["name"]!)")
        try expect(ledger.records[0].attempt.review.source==s,"Unread lost original source")
        try expect(ledger.acknowledge(auth)==confirmed,"Unread unknown acknowledged")
    }
    let page=try JSONDecoder().decode(NotificationPage.self,from:Data(contentsOf:directory.appendingPathComponent("notifications-101.json"))),n=page.items.first {$0.id==2102}!
    let context=NotificationMarkUnreadContext(business:101,notification:2102,epoch:1),source=NotificationMarkUnreadSource(context:context,generation:1,notification:n)
    let grant=SyntheticNotificationMarkUnreadGrant(business:101,notification:2102,actor:9001,update:true),auth=grant.authorization(for:context)!
    try expect(SyntheticNotificationMarkUnreadGrant(business:101,notification:2102,actor:9001,update:false).authorization(for:context)==nil,"Unread VIEW granted UPDATE")
    try expect(grant.authorization(for:NotificationMarkUnreadContext(business:202,notification:2102,epoch:1))==nil,"Unread grant crossed Business")
    var ledger=NotificationMarkUnreadLedger();let a=ledger.begin(NotificationMarkUnreadReview(source:source,generation:1),authorization:auth)!
    try expect(ledger.begin(a.review,authorization:auth)==nil,"Pending unread repeated")
    ledger.complete(a,outcome:.unknown)
    let fresh=NotificationMarkUnreadContext(business:101,notification:2102,epoch:2),freshAuth=grant.authorization(for:fresh)!
    try expect(ledger.blocked(fresh) && ledger.visible(freshAuth)==nil && !ledger.acknowledge(freshAuth),"Unread new epoch proved outcome")
    ledger.complete(a,outcome:.rejectedWithoutWrite);try expect(ledger.records[0].phase == .unknown,"Terminal unread overwritten")
    try expect(!ledger.blocked(NotificationMarkUnreadContext(business:101,notification:2101,epoch:1)),"Unread blocked independent identity")
    return count
}
