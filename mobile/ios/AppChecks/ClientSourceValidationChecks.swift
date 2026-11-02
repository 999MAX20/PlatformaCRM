import Foundation
import CRMCore

@MainActor func checkClientSourceValidation(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let m=ClientDraftViewModel(),a=ClientDraftContext(business:101,epoch:1);m.bind(a);m.open(a);let s=m.session.selection!
    m.update(.fullName,"\u{001C} A \u{001F}",s);m.update(.phone," \u{FEFF}123\u{FEFF} ",s);m.update(.notes," \u{FEFF}Notes\u{FEFF} ",s);m.prepare(s)
    let raw=m.session.values,review=m.session.review!
    try expect(review.preview.fullName=="A" && review.preview.phone=="\u{FEFF}123\u{FEFF}" && review.preview.notes=="\u{FEFF}Notes\u{FEFF}" && review.values==raw,"Client preview used JS/default whitespace or lost raw")
    m.back(s);m.update(.notes,"Bad\u{0000}notes",s);m.prepare(s)
    try expect(m.session.phase == .editing && m.session.issues.contains(where:{$0.field == .notes && $0.problem == .characters}) && m.session.values.fullName==raw.fullName,"Notes source error not field-owned or raw name lost")
    m.update(.notes,"Good",s);try expect(!m.session.issues.contains(where:{$0.field == .notes}),"Editing notes retained old field issue")
    m.update(.email,"a@domain-.com",s);m.prepare(s);try expect(m.session.values.webIssues.isEmpty && m.session.issues.contains(where:{$0.field == .email}),"Django ASCII domain constraint omitted after valid Zod stage")
    m.update(.email,String(repeating:"x",count:243)+"@example.com",s);m.prepare(s);try expect(m.session.issues.contains(where:{$0.problem == .emailLength}),"EmailField254 length omitted")
    m.update(.email,"alpha@example.invalid",s);m.prepare(s);try expect(m.session.phase == .review,"Corrected Client source input unavailable")
    m.close(s);m.open(a);let fresh=m.session.selection!;m.discard(s);m.update(.fullName,"old",s);try expect(m.session.selection==fresh && m.session.values.fullName==raw.fullName,"Old Client modal event changed reopened form")
    m.bind(ClientDraftContext(business:101,epoch:2));try expect(m.session.values==ClientDraftValues() && m.session.review==nil,"Client epoch retained normalized/raw snapshot")
    return count
}
