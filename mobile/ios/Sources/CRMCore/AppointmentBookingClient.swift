import Foundation

// Unsent profile relation observation tied to this form source, not CREATE or availability evidence.
public struct AppointmentBookingClientSelection:Equatable,Sendable {
    public let source:AppointmentBookingSource
    public let selected:ClientSearchProfileSelection
    public let read:ClientReadSelection
    public let rawQuery:String
    public let choice:TaskDraftClientChoice
    public init?(source:AppointmentBookingSource,selected:ClientSearchProfileSelection,read:ClientReadSelection,rawQuery:String,profile:ClientProfile) {
        guard source.valid,selected.selection.context==ClientSearchContext(business:source.read.scope.business.id,epoch:source.epoch),selected.selection.generation>0,selected.generation>0,
              read.business==source.read.scope.business.id,read.id==selected.id,read.revision>0,
              let choice=TaskDraftClientChoice(profile:profile,business:read.business,id:read.id) else {return nil}
        self.source=source;self.selected=selected;self.read=read;self.rawQuery=rawQuery;self.choice=choice
    }
    public func matches(source:AppointmentBookingSource,client:TaskDraftClientChoice)->Bool {self.source==source && choice==client}
    public static func ==(a:Self,b:Self)->Bool {a.source==b.source && a.selected==b.selected && a.read==b.read && SourceTextIdentity.same(a.rawQuery,b.rawQuery) && a.choice==b.choice}
}
