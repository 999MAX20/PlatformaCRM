import Foundation
import CRMCore

actor ControlledTaskFileMetadataPort:TaskFileMetadataPort {
    private var calls:[TaskFileMetadataContext]=[]
    private var pending:[Int:CheckedContinuation<Data,any Error>]=[:],waiters:[Int:CheckedContinuation<Void,Never>]=[:]
    func read(_ context:TaskFileMetadataContext) async throws -> Data {let i=calls.count;calls.append(context);return try await withCheckedThrowingContinuation {pending[i]=$0;waiters.removeValue(forKey:i)?.resume()}}
    func wait(_ i:Int) async {if pending[i]==nil {await withCheckedContinuation {waiters[i]=$0}}}
    func resolve(_ i:Int,_ data:Data) {pending.removeValue(forKey:i)!.resume(returning:data)}
    func fail(_ i:Int) {pending.removeValue(forKey:i)!.resume(throwing:CancellationError())}
    func recorded()->[TaskFileMetadataContext] {calls}
}
@MainActor func checkTaskFileMetadata(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("task-file-metadata.json")),catalog=try JSONSerialization.jsonObject(with:data) as! [String:Any],cases=catalog["validation_cases"] as! [[String:Any]],fixture=FixtureTaskFileMetadataPort(directory:directory)
    let context=TaskFileMetadataContext(business:101,task:1101,epoch:180,revision:1),body=try await fixture.read(context)
    let rows=try TaskFileMetadata.window(body,context:context);try expect(rows.count==2 && rows[0].size==4294967296 && rows[1].content_type=="" && rows[1].size==0,"Metadata truncated64bit size or invented content type")
    let encoded=String(decoding:try JSONEncoder().encode(rows),as:UTF8.self)
    try expect(!encoded.contains("download_url") && !encoded.contains("https:") && !encoded.contains("uploaded_by") && !encoded.contains("scan_status"),"Metadata retained URL/uploader/AV authority")
    for row in cases {
        let payload=try JSONSerialization.data(withJSONObject:row["body"]!),decoded=try? TaskFileMetadata.window(payload,context:context)
        try expect((decoded != nil)==(row["valid"] as! Bool),"Metadata scope/shape/window mismatch: \(row["name"]!)")
        if let decoded {let text=String(decoding:try JSONEncoder().encode(decoded),as:UTF8.self);try expect(!text.contains("download_url") && !text.contains("scan_status") && !text.contains("lease") && !text.contains("https:"),"Extra metadata granted URL/scan authority")}
    }
    let held=ControlledTaskFileMetadataPort(),model=TaskFileMetadataViewModel(port:held);model.bind(context);let stale=model.control!,job=Task {await model.load(expected:stale)};await held.wait(0)
    await model.load(expected:model.control);try expect(await held.recorded().count==1 && model.loading && model.items.isEmpty,"Pending metadata read duplicated or retained stale rows")
    let other=TaskFileMetadataContext(business:202,task:1201,epoch:181,revision:2);model.bind(other);let replacement=model.control!
    await held.resolve(0,body);await job.value;try expect(model.control==replacement && !model.loaded && model.items.isEmpty && !model.failed,"Late metadata response changed replacement Business")
    model.bind(context);let failJob=Task {await model.load(expected:model.control)};await held.wait(1);await held.fail(1);await failJob.value
    try expect(model.failed && !model.loading && !model.loaded && model.items.isEmpty && model.selected==nil,"Failed read exposed old metadata")
    model.bind(context);let oldFailure=model.control!;let retry=Task {await model.load(expected:oldFailure)};await held.wait(2);await held.resolve(2,body);await retry.value
    let loaded=model.control!;model.select(rows[0],expected:oldFailure);try expect(model.selected==nil,"Old error/control selected new metadata")
    model.select(rows[0],expected:loaded);let back=model.control!;await model.load(expected:back);try expect(await held.recorded().count==3,"Selected metadata unexpectedly loaded another window")
    model.back(expected:back);model.select(rows[0],expected:model.control);let selected=model.control;model.back(expected:back);try expect(model.control==selected && model.selected==rows[0],"Old identical-row Back cleared a new selection")
    model.back(expected:model.control);let oldWindow=model.control!;let reload=Task {await model.load(expected:oldWindow)};await held.wait(3);await held.resolve(3,body);await reload.value;model.select(rows[0],expected:oldWindow)
    try expect(model.selected==nil && model.items==rows,"Old identical window row control revived after refresh")
    let closing=Task {await model.load(expected:model.control)};await held.wait(4);model.bind(nil);await held.fail(4);await closing.value;try expect(model.control==nil && model.items.isEmpty && !model.failed,"Late error reopened closed metadata")
    let empty=TaskFileMetadataViewModel(port:fixture);empty.bind(TaskFileMetadataContext(business:101,task:1401,epoch:182,revision:1));await empty.load(expected:empty.control);try expect(empty.loaded && empty.items.isEmpty && !empty.failed,"Empty fixture window became failure or full-count assertion")
    let transport=SearchTransport(directory),repo=APIReadRepository(transport:transport),plain=TaskListViewModel(repository:repo),readOnly=TaskListViewModel(repository:repo,fileMetadataPort:fixture)
    await readOnly.load(business:101,epoch:183);await readOnly.open(id:1101);try expect(plain.fileMetadata==nil && readOnly.fileMetadata?.context==nil,"GET/default composition granted file metadata reader")
    let list=TaskListViewModel(repository:repo,commentSource:FixtureTaskCommentDraftSource(directory:directory),startSubmission:FixtureTaskStartPort(directory:directory),fileMetadataPort:fixture)
    await list.load(business:101,epoch:184);await list.open(id:1101);let files=list.fileMetadata!,before=list.detail!,items=list.items,reads=await transport.recorded().count
    await files.load(expected:files.control);files.select(files.items[0],expected:files.control);try expect(files.selected?.id==8101 && list.detail==before && list.items==items,"Metadata flow changed Task/list/status/comments")
    let readsAfter=await transport.recorded().count;try expect(readsAfter==reads,"Metadata fixture issued another repository read or file request")
    list.prepareStart(list.startAction?.control,parent:list.control);let action=list.startAction!;await action.submit(expected:action.control);let result=action.submission!
    files.back(expected:files.control);await files.load(expected:files.control);try expect(action.submission==result && action.retainedAttemptCount==1 && list.detail==before,"Metadata navigation erased/replayed Task attempt or changed GET")
    let previousRead=files.context!
    list.back();try expect(files.control==nil && files.items.isEmpty && action.retainedAttemptCount==1,"Task Back exposed metadata or erased action attempt")
    await list.open(id:1101);try expect(files.context?.revision != previousRead.revision && !files.loaded && files.items.isEmpty,"Reopened Task retained old metadata window")
    return count
}
