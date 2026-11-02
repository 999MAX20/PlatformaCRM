import Foundation
import CRMCore

func runTaskPeopleReadChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-people-read.json"))) as! [String:Any]
    for row in catalog["cases"] as! [[String:Any]] {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var fields=json["details"] as! [String:Any]
        for key in ["created_by","assignee"] {fields.removeValue(forKey:key);if let value=row["value"] {fields[key]=value}};json["details"]=fields
        let detail=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
        try expect(detail.valid(for:101,id:1101),"Optional user shape invalidated whole readable Task")
        for user in [detail.details.created_by,detail.details.assignee] {
            let kind: String;switch user {case .notSet:kind="not_set";case .unknown:kind="unknown";case .person:kind="person"}
            try expect(kind==row["expected"] as! String,"Null/missing/identity/type person semantics changed: \(row["name"]!)")
            if case .person(let item)=user {
                let source=row["value"] as! [String:Any]
                try expect(item.id==source["id"] as! Int && item.email==source["email"] as! String && item.full_name==source["full_name"] as! String,"Miniobject person identity/name/email not preserved")
                try expect(item.displayName==(row["display"] as? String),"Person display fallback invented label/changed name")
            }
        }
        try expect(detail.task.status=="open" && detail.task.business==nil && detail.task.updated_at==nil,"Read person inferred Task action/version")
    }
    return count
}
