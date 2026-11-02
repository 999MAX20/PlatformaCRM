import Foundation

public struct ClientSearchContext: Equatable, Sendable {
    public let business: Int
    public let epoch: Int
    public init(business: Int,epoch: Int) { self.business=business;self.epoch=epoch }
    public var valid: Bool { business>0 && epoch>0 }
}
public struct ClientSearchSelection: Equatable, Sendable {
    public let context: ClientSearchContext
    public let generation: Int
    public init(context:ClientSearchContext,generation:Int) {self.context=context;self.generation=generation}
}
public struct ClientSearchRequest: Equatable, Sendable {
    public let selection: ClientSearchSelection
    public let revision: Int
    public let query: String
}
public struct ClientSearchProfileSelection: Equatable, Sendable {
    public let selection: ClientSearchSelection
    public let id: Int
    public let generation: Int
    public init(selection:ClientSearchSelection,id:Int,generation:Int) {self.selection=selection;self.id=id;self.generation=generation}
}
// The result window and count belong to a specific server query, never a
// client-side filter of Directory.items. Only manually typed query is retained.
public struct ClientSearchSession: Sendable {
    public private(set) var context: ClientSearchContext?
    public private(set) var selection: ClientSearchSelection?
    public private(set) var query = ""
    public private(set) var submitted: String?
    public private(set) var items: [ClientContact] = []
    public private(set) var total = 0
    public private(set) var loading = false
    public private(set) var loaded = false
    public private(set) var failure: ReadFailure?
    public private(set) var selectedID: Int?
    public private(set) var profileSelection: ClientSearchProfileSelection?
    private var generation = 0
    private var revision = 0
    private var profileGeneration = 0
    private var pending: ClientSearchRequest?
    public init() {}
    public var partial: Bool { loaded && total>items.count }
    public var showsEmpty: Bool { loaded && !loading && failure==nil && !partial && items.isEmpty }
    private mutating func invalidate() {
        revision += 1;pending=nil;submitted=nil;items=[];total=0;loading=false;loaded=false;failure=nil;selectedID=nil;profileSelection=nil
    }
    public mutating func bind(_ next: ClientSearchContext?) {
        let next=next?.valid == true ? next : nil
        guard next != context else { return }
        invalidate();generation += 1;context=next;selection=nil;query=""
    }
    @discardableResult public mutating func open(expected: ClientSearchContext) -> Bool {
        guard expected.valid,context==expected else { return false }
        invalidate();generation += 1;selection=ClientSearchSelection(context:expected,generation:generation);return true
    }
    public mutating func update(_ value: String,expected: ClientSearchSelection) {
        guard selection==expected,!query.utf8.elementsEqual(value.utf8) else { return }
        invalidate();query=value
    }
    public mutating func clear(expected: ClientSearchSelection) {
        guard selection==expected else { return };invalidate();query=""
    }
    public mutating func begin(expected: ClientSearchSelection) -> ClientSearchRequest? {
        guard selection==expected else { return nil }
        invalidate();submitted=SourceTextTrim.pythonStrip(query);loading=true
        let ticket=ClientSearchRequest(selection:expected,revision:revision,query:submitted!);pending=ticket;return ticket
    }
    @discardableResult public mutating func accept(_ page: ClientList,request: ClientSearchRequest) -> Bool {
        guard pending==request,selection==request.selection else { return false }
        guard page.business==request.selection.context.business,page.summary.total>=page.items.count,page.items.count<=50,
              page.items.allSatisfy({$0.id>0}),Set(page.items.map(\.id)).count==page.items.count else { fail(.invalidPayload,request:request);return false }
        pending=nil;items=page.items;total=page.summary.total;loading=false;loaded=true;failure=nil;return true
    }
    public mutating func fail(_ error: ReadFailure,request: ClientSearchRequest) {
        guard pending==request,selection==request.selection else { return }
        pending=nil;loading=false;loaded=false;items=[];total=0;selectedID=nil;profileSelection=nil;failure=error
    }
    public mutating func cancel(request: ClientSearchRequest) {
        guard pending==request,selection==request.selection else { return };invalidate()
    }
    @discardableResult public mutating func select(id: Int,expected: ClientSearchSelection) -> Bool {
        guard selection==expected,loaded,!loading,failure==nil,items.contains(where:{$0.id==id}) else { return false }
        profileGeneration += 1;selectedID=id
        profileSelection=ClientSearchProfileSelection(selection:expected,id:id,generation:profileGeneration);return true
    }
    public mutating func backProfile(expected: ClientSearchSelection) {
        guard selection==expected else { return };selectedID=nil;profileSelection=nil
    }
    public mutating func backProfile(expected: ClientSearchSelection,profile: ClientSearchProfileSelection) {
        guard profileSelection==profile else {return};backProfile(expected:expected)
    }
    public mutating func close(expected: ClientSearchSelection) {
        guard selection==expected else { return };invalidate();generation += 1;selection=nil
    }
}
