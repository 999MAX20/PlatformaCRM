import Foundation
import CRMCore

@MainActor func checkTaskCreateValidation(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let transport=SearchTransport(directory),owner=TaskListViewModel(repository:APIReadRepository(transport:transport)),context=TaskDraftContext(business:101,epoch:1)
    await owner.load(business:101,epoch:1);let rows=owner.items,reads=await transport.recorded();owner.draft.open(context);let model=owner.draft,selection=model.session.selection!
    model.update(.title," \u{FEFF} Title \u{FEFF} ",selection);model.update(.description," \u{FEFF} Description \u{FEFF} ",selection);model.prepare(selection)
    let raw=model.session.values,review=model.session.review!
    try expect(review.preview.title=="Title" && review.preview.description=="\u{FEFF} Description \u{FEFF}" && review.values==raw,"Description was JS-trimmed or source preview did not differ from raw")
    try expect(await transport.recorded()==reads && owner.items==rows,"Validation/preview created Task or issued a request")
    model.back(selection);model.update(.description,"Bad\u{0000}description",selection);model.prepare(selection)
    try expect(model.session.phase == .editing && model.session.issues.contains(where:{$0.field == .description && $0.problem == .characters}) && model.session.values.title==raw.title,"Description invalid characters not field-owned or raw title lost")
    model.update(.description,"Description",selection);try expect(!model.session.issues.contains(where:{$0.field == .description}),"Editing invalid field retained stale issue")
    model.update(.title,String(repeating:"😀",count:255),selection);model.prepare(selection)
    try expect(model.session.review?.preview.title.unicodeScalars.count==255,"Native preview imposed UTF16 rather than source codepoint255 max")
    model.close(selection);model.open(context);let fresh=model.session.selection!;model.update(.title,"Old",selection);model.discard(selection)
    try expect(model.session.selection==fresh && model.session.values.title==String(repeating:"😀",count:255),"Old UI callback changed reopened source-valid input")
    await owner.load(business:101,epoch:2);try expect(model.session.values==TaskDraftValues() && model.session.review==nil,"New epoch retained old normalized/raw snapshot")
    return count
}
