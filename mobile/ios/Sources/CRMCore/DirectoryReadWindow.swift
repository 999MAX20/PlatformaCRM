import Foundation

enum DirectoryReadJSON {
    static func integer(_ value:Any?)->Int64? {guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)) else {return nil};return Int64(n.stringValue)}
    static func link(_ o:[String:Any],_ key:String)->DirectoryReadLinkPresence? {
        guard let value=o[key] else {return .absent};if value is NSNull {return .null}
        guard let raw=value as? String,!raw.isEmpty else {return nil};return .present
    }
}
// Presence only: no URL retention/following, paging policy, selected-Business total or end proof.
public enum DirectoryReadLinkPresence:Equatable,Sendable {case absent,null,present}
public enum DirectoryReadShape:Equatable,Sendable {case array,results}
// Ephemeral source rows only. Consumers validate every row before projecting their Business.
struct DirectoryReadEnvelope {
    let rows:[Any];let shape:DirectoryReadShape;let count:Int64?;let next:DirectoryReadLinkPresence;let previous:DirectoryReadLinkPresence
    static func decode(_ data:Data)->Self? {
        guard let value=try? JSONSerialization.jsonObject(with:data) else {return nil}
        let rows:[Any],shape:DirectoryReadShape,count:Int64?,next:DirectoryReadLinkPresence,previous:DirectoryReadLinkPresence
        if let array=value as? [Any] {rows=array;shape = .array;count=nil;next = .absent;previous = .absent}
        else if let o=value as? [String:Any],let results=o["results"] as? [Any] {
            rows=results;shape = .results
            if let raw=o["count"] {guard let n=DirectoryReadJSON.integer(raw),n>=0,n>=Int64(rows.count) else {return nil};count=n} else {count=nil}
            guard let n=DirectoryReadJSON.link(o,"next"),let p=DirectoryReadJSON.link(o,"previous") else {return nil};next=n;previous=p
        } else {return nil}
        return Self(rows:rows,shape:shape,count:count,next:next,previous:previous)
    }
}
