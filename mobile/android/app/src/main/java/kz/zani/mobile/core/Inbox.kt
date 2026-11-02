package kz.zani.mobile.core

data class InboxPreview(val text: String?)
enum class HandoffReadState(val copyKey: String) {REQUIRED("handoffReadYes"),NOT_REQUIRED("handoffReadNo"),UNKNOWN("handoffReadUnknown");companion object {fun from(flag: Boolean?)=when(flag){true->REQUIRED;false->NOT_REQUIRED;null->UNKNOWN}}}
data class InboxConversation(val id: Int, val title: String?, val channel: String?, val unreadCount: Int, val preview: InboxPreview?,val handoffRequired: Boolean?=null) {val handoffState get()=HandoffReadState.from(handoffRequired)}
data class InboxList(val business: Int, val items: List<InboxConversation>, val total: Int) {
    fun validFor(scope: Int) = business == scope && total >= items.size &&
        items.map { it.id }.distinct().size == items.size && items.all { it.id > 0 && it.unreadCount >= 0 }
}
// Existing source status only; sent never implies delivery/read or own command recovery.
enum class InboxMessageState(val copyKey:String) {RECEIVED("messageStateReceived"),QUEUED("messageStateQueued"),SENT("messageStateSent"),FAILED("messageStateFailed"),UNKNOWN("messageStateUnknown");companion object {fun from(raw:Any?):InboxMessageState=when(raw){"received"->RECEIVED;"queued"->QUEUED;"sent"->SENT;"failed"->FAILED;else->UNKNOWN}}}
data class InboxMessage(val id: Int, val conversationID: Int, val direction: String?, val senderType: String?, val text: String?, val createdAt: String?,val sourceState:InboxMessageState=InboxMessageState.UNKNOWN)
data class InboxThread(val business: Int, val conversation: InboxConversation, val messages: List<InboxMessage>, val maxMessages: Int, val clientRefID: Int? = null, val sourceStatus: String? = null) {
    val clientReferenceID: Int? get() = clientRefID?.takeIf { it > 0 }
    val windowCapped: Boolean get() = messages.size == maxMessages
    fun validFor(scope: Int, id: Int) = business == scope && conversation.id == id && conversation.unreadCount >= 0 &&
        maxMessages > 0 && messages.size <= maxMessages && messages.map { it.id }.distinct().size == messages.size &&
        messages.all { it.id > 0 && it.conversationID == id }
}
