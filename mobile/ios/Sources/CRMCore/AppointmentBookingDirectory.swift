import Foundation

// Retained local independently read field observations. No permission, server version or availability proof.
public struct AppointmentBookingDirectorySelection:Equatable,Sendable {
    public let source:AppointmentBookingSource
    public let service:ServiceDirectoryItem?
    public let resource:ResourceDirectoryItem?
    public init?(source:AppointmentBookingSource,service:ServiceDirectoryItem?,resource:ResourceDirectoryItem?) {
        guard source.valid,service != nil || resource != nil else {return nil}
        if let service {guard service.business==source.read.scope.business.id,service.id>0,service.id<=Int(Int32.max) else {return nil}}
        if let resource {guard resource.business==source.read.scope.business.id,resource.id>0,resource.id<=Int(Int32.max) else {return nil}}
        self.source=source;self.service=service;self.resource=resource
    }
    public func matches(source:AppointmentBookingSource,service:AppointmentReferenceDetail,resource:AppointmentRescheduleResource)->Bool {
        guard self.source==source else {return false}
        if let selected=self.service {guard selected.reference==service else {return false}}
        if let selected=self.resource {guard resource == .linked(selected.reference) else {return false}}
        return true
    }
}
