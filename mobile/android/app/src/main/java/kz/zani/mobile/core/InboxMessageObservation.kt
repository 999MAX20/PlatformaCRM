package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Presence/raw text only; no local dates, chronology or own command outcome.
sealed interface InboxObservedText {
    data object Missing:InboxObservedText
    data object Null:InboxObservedText
    data class Value(val raw:String):InboxObservedText
    val rawText:String? get()=(this as? Value)?.raw
    companion object {
        internal fun decode(row:JSONObject,key:String):InboxObservedText {
            if(!row.has(key))return Missing;val value=row.get(key);if(value==JSONObject.NULL)return Null;require(value is String);return Value(value)
        }
    }
}
data class InboxMessageObservation private constructor(val context:InboxMessageFilesContext,val status:InboxObservedText,val sentAt:InboxObservedText,val deliveredAt:InboxObservedText,val readAt:InboxObservedText) {
    val state get()=InboxMessageState.from(status.rawText)
    fun validFor(c:InboxMessageFilesContext)=c.valid && context==c
    companion object {
        fun decode(body:String,c:InboxMessageFilesContext):InboxMessageObservation?=runCatching {val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject);decode(row,c)}.getOrNull()
        internal fun decode(row:JSONObject,c:InboxMessageFilesContext):InboxMessageObservation {
            require(c.valid && directoryReadInteger(row.get("id"))==c.message.toLong() && directoryReadInteger(row.get("conversation"))==c.conversation.toLong())
            return InboxMessageObservation(c,InboxObservedText.decode(row,"status"),InboxObservedText.decode(row,"sent_at"),InboxObservedText.decode(row,"delivered_at"),InboxObservedText.decode(row,"read_at"))
        }
    }
}
