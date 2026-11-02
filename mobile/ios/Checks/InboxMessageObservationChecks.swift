import Foundation
import CRMCore

func runInboxMessageObservationChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-message-observations.json"))) as! [String:Any]
    func context(_ c:[String:Int])->InboxMessageFilesContext {InboxMessageFilesContext(business:c["business"]!,conversation:c["conversation"]!,message:c["message"]!,epoch:c["epoch"]!,revision:c["revision"]!,limit:c["limit"]!)}
    func verify(_ o:InboxMessageObservation,_ row:[String:Any]) throws {
        let wanted=row["observed"] as! [String:[String:String]]
        for (key,value) in [("status",o.status),("sent_at",o.sentAt),("delivered_at",o.deliveredAt),("read_at",o.readAt)] {
            let w=wanted[key]!
            switch value {case .missing:try expect(w["kind"]=="missing","Missing field defaulted");case .null:try expect(w["kind"]=="null","Null field collapsed");case .value(let raw):try expect(w["kind"]=="value" && raw.utf8.elementsEqual(w["raw"]!.utf8),"Provided observation raw bytes changed")}
        }
        let state=row["state"] as! String;try expect(o.state.copyKey==["received":"messageStateReceived","queued":"messageStateQueued","sent":"messageStateSent","failed":"messageStateFailed","unknown":"messageStateUnknown"][state],"Timestamp/raw status inferred a delivery/read or known state")
    }
    for row in catalog["cases"] as! [[String:Any]] {
        let c=context(row["context"] as! [String:Int]),o=InboxMessageObservation.decode(Data((row["response_json"] as! String).utf8),context:c)
        try expect((o != nil)==(row["valid"] as! Bool),"Observation strict schema/scope: \(row["name"]!)")
        if let o {try expect(o.valid(for:c),"Observation lost context");try verify(o,row)}
    }
    for row in catalog["window_cases"] as! [[String:Any]] {
        let c=context(row["context"] as! [String:Int]);var result="valid"
        do {let window=try InboxMessageFileWindow.decode(Data((row["response_json"] as! String).utf8),context:c);try expect(window.valid(for:c),"Combined observation/metadata failed its context");try verify(window.observation,row);try expect(window.items.allSatisfy {Mirror(reflecting:$0).children.count==9},"Observation enlarged file projection")}
        catch let e as ReadFailure {result=e == .unavailable ? "unavailable":"invalidPayload"}
        try expect(result==row["expected"] as! String,"Other-row observation/all-row precedence failed: \(row["name"]!)")
    }
    let c=InboxMessageFilesContext(business:101,conversation:901,message:9011,epoch:1,revision:1,limit:30)
    for row in catalog["identity_pairs"] as! [[String:Any]] {
        let a=InboxMessageObservation.decode(try JSONSerialization.data(withJSONObject:row["left"]!),context:c)!,b=InboxMessageObservation.decode(try JSONSerialization.data(withJSONObject:row["right"]!),context:c)!
        try expect((a==b)==row["same"] as! Bool,"Raw presence/Unicode/equivalent-instant observation identity changed")
    }
    return count
}
