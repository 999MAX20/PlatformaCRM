import Foundation

// Local read context, never a booking grant, reservation, version or reschedule command.
public struct AppointmentSlotIntent:Equatable,Sendable {
    public let business:Int;public let service:Int;public let resource:Int?;public let day:String;public let timezone:String
    public init?(business:Business,service:AppointmentReferenceDetail,resource:AppointmentReferenceDetail?,day:String) {
        guard business.id>0,business.id<=Int(Int32.max),service.valid(for:business.id,id:service.id),service.id<=Int(Int32.max),Self.validDay(day),TimeZone(identifier:business.timezone) != nil else {return nil}
        if let resource {guard resource.valid(for:business.id,id:resource.id),resource.id<=Int(Int32.max) else {return nil}}
        self.business=business.id;self.service=service.id;self.resource=resource?.id;self.day=day;timezone=business.timezone
    }
    public static func validDay(_ raw:String)->Bool {
        let bytes=Array(raw.utf8)
        guard bytes.count==10,bytes[4]==45,bytes[7]==45,bytes.enumerated().allSatisfy({i,b in i==4 || i==7 || (48...57).contains(b)}),!raw.hasPrefix("0000") else {return false}
        return Day.isValid(raw)
    }
    public var request:ReadRequest {
        var query=["business_id":String(business),"service_id":String(service),"date":day]
        if let resource {query["resource_id"]=String(resource)}
        return ReadRequest(path:"/api/appointments/available-slots/",query:query)
    }
}
public struct AppointmentSlotCandidate:Equatable,Sendable {
    public let startAt:String;public let endAt:String
    public static func instant(_ raw:String)->Date? {
        guard raw.range(of:"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$",options:.regularExpression) != nil,
              AppointmentSlotIntent.validDay(String(raw.prefix(10))),!raw.hasSuffix("-00:00") else {return nil}
        let chars=Array(raw);func value(_ start:Int,_ count:Int)->Int {Int(String(chars[start..<start+count])) ?? -1}
        guard value(11,2)<24,value(14,2)<60,value(17,2)<60 else {return nil}
        if !raw.hasSuffix("Z") {let tail=String(raw.suffix(6));let parts=tail.dropFirst().split(separator:":");guard let h=Int(parts[0]),let m=Int(parts[1]),h<=18,m<60,h<18 || m==0 else {return nil}}
        if chars.count>19,chars[19]=="." {
            let suffix=raw.hasSuffix("Z") ? "Z":String(raw.suffix(6));let fraction=String(raw.dropFirst(20).dropLast(suffix.count))
            guard let base=Appointment.instant(String(raw.prefix(19))+suffix),let value=Double("0."+fraction) else {return nil}
            return base.addingTimeInterval(value)
        }
        return Appointment.instant(raw)
    }
}
public struct AppointmentSlotRead:Equatable,Sendable {
    public let intent:AppointmentSlotIntent;public let candidates:[AppointmentSlotCandidate]
    public func valid(for expected:AppointmentSlotIntent)->Bool {
        guard intent==expected,TimeZone(identifier:expected.timezone) != nil else {return false}
        return candidates.allSatisfy {value in guard let a=AppointmentSlotCandidate.instant(value.startAt),let b=AppointmentSlotCandidate.instant(value.endAt) else {return false};return b>a && Day.string(a,timezone:expected.timezone)==expected.day}
    }
    private struct Fields:Decodable {let start_at:String;let end_at:String}
    public static func decode(_ data:Data,intent:AppointmentSlotIntent)->Self? {
        guard TimeZone(identifier:intent.timezone) != nil,let fields=try? JSONDecoder().decode([Fields].self,from:data) else {return nil}
        var values:[AppointmentSlotCandidate]=[]
        for item in fields {
            guard let start=AppointmentSlotCandidate.instant(item.start_at),let end=AppointmentSlotCandidate.instant(item.end_at),end>start,Day.string(start,timezone:intent.timezone)==intent.day else {return nil}
            values.append(AppointmentSlotCandidate(startAt:item.start_at,endAt:item.end_at))
        }
        return Self(intent:intent,candidates:values)
    }
}
public protocol AppointmentSlotRepository:Sendable {func slots(_ intent:AppointmentSlotIntent) async throws -> AppointmentSlotRead}
public struct APIAppointmentSlotRepository:AppointmentSlotRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func slots(_ intent:AppointmentSlotIntent) async throws -> AppointmentSlotRead {
        let response=try await transport.get(intent.request)
        switch response.status {
        case 200:guard let read=AppointmentSlotRead.decode(response.data,intent:intent) else {throw ReadFailure.invalidPayload};return read
        case 403:throw ReadFailure.denied;case 404:throw ReadFailure.notFound;default:throw ReadFailure.unavailable
        }
    }
}
