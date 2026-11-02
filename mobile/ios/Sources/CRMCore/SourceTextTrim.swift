import Foundation

// Matches MobileInboxReplyView's Python str.strip; no provider/body mutation.
public enum SourceTextTrim {
    public static func pythonStrip(_ raw: String) -> String {
        let whitespace = "\u{0009}\u{000A}\u{000B}\u{000C}\u{000D}\u{001C}\u{001D}\u{001E}\u{001F}\u{0020}\u{0085}\u{00A0}\u{1680}\u{2000}\u{2001}\u{2002}\u{2003}\u{2004}\u{2005}\u{2006}\u{2007}\u{2008}\u{2009}\u{200A}\u{2028}\u{2029}\u{202F}\u{205F}\u{3000}"
        return scalarTrim(raw,in:CharacterSet(charactersIn:whitespace))
    }
    private static let javascriptWhitespace=CharacterSet(charactersIn:"\u{0009}\u{000A}\u{000B}\u{000C}\u{000D}\u{0020}\u{00A0}\u{1680}\u{2000}\u{2001}\u{2002}\u{2003}\u{2004}\u{2005}\u{2006}\u{2007}\u{2008}\u{2009}\u{200A}\u{2028}\u{2029}\u{202F}\u{205F}\u{3000}\u{FEFF}")
    private static func scalarTrim(_ raw:String,in whitespace:CharacterSet)->String {
        var scalars=raw.unicodeScalars
        while let first=scalars.first,whitespace.contains(first) {scalars.removeFirst()}
        while let last=scalars.last,whitespace.contains(last) {scalars.removeLast()}
        return String(scalars)
    }
    public static func javascriptTrim(_ raw: String) -> String {scalarTrim(raw,in:javascriptWhitespace)}
    public static func javascriptTrimEnd(_ raw: String) -> String {
        var scalars=raw.unicodeScalars
        while let last=scalars.last,javascriptWhitespace.contains(last) {scalars.removeLast()}
        return String(scalars)
    }
}

// Typed optional text identity only; independent from source strip/query collation or JSON ordering.
public enum SourceTextIdentity {
    public static func same(_ lhs:String?,_ rhs:String?)->Bool {
        switch (lhs,rhs) {case (nil,nil):true;case let (left?,right?):left.utf8.elementsEqual(right.utf8);default:false}
    }
}
