import Foundation

// Local evidence for one returned READ, not a booking DTO, grant or server version.
public struct AppointmentSlotReadContext:Equatable,Sendable {
    public let business:Business;public let service:AppointmentReferenceDetail;public let resource:AppointmentReferenceDetail?;public let read:AppointmentSlotRead
    public init?(business:Business,service:AppointmentReferenceDetail,resource:AppointmentReferenceDetail?,read:AppointmentSlotRead) {
        guard let intent=AppointmentSlotIntent(business:business,service:service,resource:resource,day:read.intent.day),read.valid(for:intent) else {return nil}
        self.business=business;self.service=service;self.resource=resource;self.read=read
    }
    public func review(index:Int)->AppointmentSlotCandidateReview? {AppointmentSlotCandidateReview(context:self,index:index)}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.business.id==rhs.business.id && lhs.business.name.utf8.elementsEqual(rhs.business.name.utf8) && lhs.business.timezone.utf8.elementsEqual(rhs.business.timezone.utf8) && lhs.service==rhs.service && lhs.resource==rhs.resource && lhs.read==rhs.read}
}
public struct AppointmentSlotCandidateReview:Equatable,Sendable {
    public let context:AppointmentSlotReadContext;public let index:Int
    public init?(context:AppointmentSlotReadContext,index:Int) {
        guard context.read.candidates.indices.contains(index) else {return nil}
        self.context=context;self.index=index
    }
    public var candidate:AppointmentSlotCandidate {context.read.candidates[index]}
    public func valid(for context:AppointmentSlotReadContext)->Bool {self.context==context && context.read.candidates.indices.contains(index)}
}
