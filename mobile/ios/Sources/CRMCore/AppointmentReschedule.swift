import Foundation

// Explicit supported input; no default/current clock, future-only rule or implicit timezone.
public enum AppointmentRescheduleResource:Equatable,Sendable {case clear,linked(AppointmentReferenceDetail)
    public var id:Int? {if case .linked(let detail)=self {return detail.id};return nil}
}
public struct AppointmentRescheduleInput:Equatable,Sendable {
    public let start:TaskSnoozeValue
    public let rawReason:String
    public let resource:AppointmentRescheduleResource
    public var reason:String {SourceTextTrim.pythonStrip(rawReason)}
    public init?(source:AppointmentLifecycleSource,startAt:String,reason:String,resource:AppointmentRescheduleResource) {
        guard source.valid,source.canReschedule,let start=TaskSnoozeValue.parse(startAt),start.microseconds%1000==0 else {return nil}
        if case .linked(let detail)=resource {guard let id=source.linkedResourceID,detail.valid(for:source.read.scope.business.id,id:id) else {return nil}}
        self.start=start;rawReason=reason;self.resource=resource
    }
    public func valid(for source:AppointmentLifecycleSource)->Bool {Self(source:source,startAt:start.raw,reason:rawReason,resource:resource)==self}
    public static func ==(a:Self,b:Self)->Bool {SourceTextIdentity.same(a.start.raw,b.start.raw) && a.start.microseconds==b.start.microseconds && SourceTextIdentity.same(a.rawReason,b.rawReason) && a.resource==b.resource}
}
public extension AppointmentLifecycleSource {
    var canReschedule:Bool {valid && !["cancelled","completed","no_show"].contains(appointment.status)}
}
