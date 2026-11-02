package kz.zani.mobile.core

object SourceTextTrim {
    // Source MobileInboxReplyView uses Python str.strip, not a new trim policy.
    fun pythonStrip(raw: String)=raw.trim { c -> c in '\u0009'..'\u000D' || c in '\u001C'..'\u0020' || c=='\u0085' || c=='\u00A0' || c=='\u1680' || c in '\u2000'..'\u200A' || c=='\u2028' || c=='\u2029' || c=='\u202F' || c=='\u205F' || c=='\u3000' }
    private fun javascriptWhitespace(c: Char)=c in '\u0009'..'\u000D' || c=='\u0020' || c=='\u00A0' || c=='\u1680' || c in '\u2000'..'\u200A' || c=='\u2028' || c=='\u2029' || c=='\u202F' || c=='\u205F' || c=='\u3000' || c=='\uFEFF'
    fun javascriptTrim(raw: String)=raw.trim(::javascriptWhitespace)
    fun javascriptTrimEnd(raw: String)=raw.trimEnd(::javascriptWhitespace)
}
