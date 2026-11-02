import Foundation

// Explicit read-to-draft time choice only. No grant, reservation or copied end/resource fields.
public struct AppointmentBookingCandidateTime:Equatable,Sendable {
    public let source:AppointmentBookingSource;public let review:AppointmentSlotCandidateReview;public let rawStart:String
    public init?(source:AppointmentBookingSource,review:AppointmentSlotCandidateReview) {
        let c=review.context
        guard source.valid,review.valid(for:c),AppointmentSlotReadContext(business:c.business,service:c.service,resource:c.resource,read:c.read)==c,c.business.id==source.read.scope.business.id,SourceTextIdentity.same(c.business.timezone,source.read.scope.business.timezone),c.service.valid(for:source.read.scope.business.id,id:source.serviceID),c.read.intent.service==source.serviceID else {return nil}
        if let resource=c.resource {guard source.resourceID==resource.id,resource.valid(for:source.read.scope.business.id,id:resource.id) else {return nil}}
        let raw=review.candidate.startAt;guard let value=TaskSnoozeValue.parse(raw),value.microseconds%1000==0 else {return nil}
        self.source=source;self.review=review;rawStart=raw
    }
    public func valid(for source:AppointmentBookingSource)->Bool {self.source==source && Self(source:source,review:review)==self}
}
