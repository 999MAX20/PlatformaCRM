package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Current selected message/provided limit and local visits only; not a version or grant.
data class InboxMessageFilesContext(val business:Int,val conversation:Int,val message:Int,val epoch:Int,val revision:Int,val limit:Int) {val valid get()=business>0 && conversation>0 && message>0 && epoch>0 && revision>0 && limit in 1..300}
data class InboxFilesConversationAnchor private constructor(val business:Int,val conversation:Int) {
    fun matches(c:InboxMessageFilesContext)=c.valid && business==c.business && conversation==c.conversation
    companion object {fun decode(body:String,c:InboxMessageFilesContext):InboxFilesConversationAnchor?=runCatching {require(c.valid);val t=JSONTokener(body);val o=t.nextValue();require(t.nextClean()=='\u0000' && o is JSONObject && inboxFileAnchor(o,c.business,c.conversation));InboxFilesConversationAnchor(c.business,c.conversation)}.getOrNull()}
}
data class InboxMessageFileWindow private constructor(val context:InboxMessageFilesContext,val items:List<InboxMessageFileMetadata>,val observation:InboxMessageObservation,val retrySource:InboxRetryMessageSource?,val count:Long,val providedMessages:Int,val hasMore:Boolean,val next:DirectoryReadLinkPresence,val previous:DirectoryReadLinkPresence,val nextBefore:DirectoryReadLinkPresence) {
    val limited get()=hasMore || count>providedMessages.toLong()
    fun validFor(c:InboxMessageFilesContext)=context==c && c.valid && observation.validFor(c) && (retrySource==null || (retrySource.valid && retrySource.context==c)) && providedMessages in 1..c.limit && count>=providedMessages && (!hasMore || providedMessages==c.limit) && previous==DirectoryReadLinkPresence.NULL && next==(if(hasMore)DirectoryReadLinkPresence.PRESENT else DirectoryReadLinkPresence.NULL) && nextBefore==next && items.all {it.validFor(c)} && items.map {it.id}.distinct().size==items.size
    companion object {fun decode(body:String,c:InboxMessageFilesContext):InboxMessageFileWindow {
        try {
            require(c.valid);val t=JSONTokener(body);val o=t.nextValue();require(t.nextClean()=='\u0000' && o is JSONObject);val rows=o.getJSONArray("results");require(rows.length()<=c.limit)
            val count=directoryReadInteger(o.get("count"));require(count!=null && count>=rows.length());val more=o.get("has_more");require(more is Boolean)
            fun presence(key:String):DirectoryReadLinkPresence {val value=o.get(key);if(value==JSONObject.NULL)return DirectoryReadLinkPresence.NULL;require(value is String && value.isNotEmpty());return DirectoryReadLinkPresence.PRESENT}
            val next=presence("next");val previous=presence("previous");require(previous==DirectoryReadLinkPresence.NULL)
            val raw=o.get("next_before_id");val cursor=if(raw==JSONObject.NULL)DirectoryReadLinkPresence.NULL else {val id=directoryReadInteger(raw);require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && o.get("next")==id.toString());DirectoryReadLinkPresence.PRESENT}
            require(next==(if(more)DirectoryReadLinkPresence.PRESENT else DirectoryReadLinkPresence.NULL) && cursor==next && (!more || rows.length()==c.limit))
            val ids=mutableSetOf<Int>();val fileIDs=mutableSetOf<Int>();var selected:List<InboxMessageFileMetadata>?=null;var observation:InboxMessageObservation?=null;var retrySource:InboxRetryMessageSource?=null
            for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val id=directoryReadInteger(row.get("id"));require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && ids.add(id.toInt()) && directoryReadInteger(row.get("conversation"))==c.conversation.toLong());val files=InboxFileMetadata.rows(row.getJSONArray("attachments"),c.business,"bot_message",id.toString());require(files.all {fileIDs.add(it.id)});val observed=InboxMessageObservation.decode(row,c.copy(message=id.toInt()));if(id.toInt()==c.message){selected=files;observation=observed;retrySource=InboxRetryMessageSource.decode(row,c)}}
            val items=selected ?: throw ReadException(ReadProblem.UNAVAILABLE)
            return InboxMessageFileWindow(c,items,observation ?: throw ReadException(ReadProblem.INVALID_PAYLOAD),retrySource,count,rows.length(),more,next,previous,cursor)
        } catch(error:ReadException) {throw error} catch(_:Exception) {throw ReadException(ReadProblem.INVALID_PAYLOAD)}
    }}
}
object InboxMessageFileSourceIdentity {fun same(a:InboxMessage,b:InboxMessage)=a==b}
