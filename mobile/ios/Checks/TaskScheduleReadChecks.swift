import Foundation
import CRMCore

func runTaskScheduleReadChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let template=try Data(contentsOf:directory.appendingPathComponent("task-101-1101.json"))
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-schedule-read.json"))) as! [String:Any]
    func kind(_ value: TaskScheduleValue) -> String {switch value {case .notSet:"not_set";case .unknown:"unknown";case .instant:"instant"}}
    var valid: [TaskDetails]=[]
    for row in catalog["cases"] as! [[String:Any]] {
        var json=try JSONSerialization.jsonObject(with:template) as! [String:Any];var fields=json["details"] as! [String:Any]
        fields.removeValue(forKey:"reminder_at");fields.removeValue(forKey:"snoozed_until")
        for (k,v) in row["fields"] as! [String:Any] {fields[k]=v};json["details"]=fields
        let detail=try JSONDecoder().decode(TaskDetails.self,from:JSONSerialization.data(withJSONObject:json))
        try expect(detail.valid(for:101,id:1101),"Optional schedule problem hid otherwise readable Task")
        try expect(kind(detail.details.reminder_at)==row["reminder"] as! String && kind(detail.details.snoozed_until)==row["snoozed"] as! String,"Schedule null/missing/type/naive semantics changed: \(row["name"]!)")
        if case .instant(let raw)=detail.details.reminder_at {
            try expect(raw==(row["fields"] as! [String:Any])["reminder_at"] as! String,"Schedule raw instant normalized or substituted")
        }
        if ["valid_UTC","offset"].contains(row["name"] as! String) {valid.append(detail)}
    }
    guard case .instant(let first)=valid[0].details.reminder_at,case .instant(let other)=valid[1].details.reminder_at else {throw CheckFailure(message:"Valid schedule instants unavailable")}
    try expect(Appointment.instant(first)==Appointment.instant(other),"Offset value changed source instant")
    var calendar=Calendar(identifier:.gregorian);calendar.timeZone=TimeZone(identifier:"Asia/Almaty")!
    let instant=Appointment.instant(first)!
    try expect(calendar.component(.day,from:instant)==30,"Business day incorrectly used UTC/device date")
    // The existing Task status and due fields are never derived from these source fields.
    try expect(valid.allSatisfy {$0.task.status=="open" && $0.task.due_at==valid[0].task.due_at},"Schedule read changed Task lifecycle/deadline")
    return count
}
