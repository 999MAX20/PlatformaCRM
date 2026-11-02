package kz.zani.mobile.data

import kz.zani.mobile.core.*
import org.json.JSONObject
import org.json.JSONArray

object JsonContracts {
    private fun JSONObject.text(key: String): String = get(key) as? String ?: throw IllegalArgumentException("Expected string")
    private fun JSONObject.integer(key: String): Int {
        val value = get(key)
        require(value is Number)
        return value.toString().toBigDecimal().intValueExact()
    }
    private fun JSONObject.nullInteger(key: String): Int? = if (isNull(key)) null else integer(key)
    private fun JSONObject.nullText(key: String): String? = if (isNull(key)) null else text(key)
    private fun JSONObject.nullObject(key: String): JSONObject? = if (isNull(key)) null else getJSONObject(key)
    private fun business(o: JSONObject) = Business(o.integer("id"), o.text("name"), o.text("timezone"))
    private fun item(o: JSONObject) = Appointment(o.integer("id"), o.nullText("title"), o.text("status"), o.nullText("start_at"), o.nullText("end_at"), o.nullInteger("client_id"))
    private fun namedID(o: JSONObject): Int? {
        if (o.isNull("id")) return null
        val raw = o.get("id"); require(raw is Number)
        val value = raw.toString().toBigDecimal().toBigIntegerExact()
        if (value < java.math.BigInteger.valueOf(Int.MIN_VALUE.toLong()) || value > java.math.BigInteger.valueOf(Int.MAX_VALUE.toLong())) return null
        return value.toInt()
    }
    private fun named(o: JSONObject?): Named? = o?.let { Named(namedID(it), it.nullText("name")) }
    fun quickReplies(json: String): QuickReplyPage = parse {
        val parsed=org.json.JSONTokener(json).nextValue()
        val envelope=parsed as? JSONObject
        val rows=if(parsed is JSONArray)parsed else envelope!!.getJSONArray("results")
        QuickReplyPage((0 until rows.length()).map {index->val row=rows.getJSONObject(index)
            QuickReplyTemplate(row.integer("id"),row.integer("business"),row.text("title"),row.text("text"),row.text("category"),row.text("channel"),row.integer("sort_order"),row.get("is_active") as? Boolean ?: throw IllegalArgumentException("Expected boolean"))
        },envelope?.nullInteger("count"),envelope?.nullText("next")!=null,envelope!=null && !envelope.isNull("count") && envelope.has("next"))
    }
    fun bootstrap(json: String): Bootstrap = parse {
        val o = JSONObject(json); val all = o.getJSONArray("businesses")
        Bootstrap(business(o.getJSONObject("active_business")), (0 until all.length()).map { business(all.getJSONObject(it)) })
    }
    fun appointments(json: String): AppointmentList = parse {
        val o = JSONObject(json); val items = o.getJSONArray("items")
        AppointmentList(o.integer("business"), o.text("date"), (0 until items.length()).map { item(items.getJSONObject(it)) }, o.getJSONObject("summary").integer("total"))
    }
    fun detail(json: String): AppointmentDetail = parse {
        val o = JSONObject(json); val fields = o.getJSONObject("details")
        val related = o.nullObject("related")
        val tasks = related?.let { if (it.isNull("tasks")) null else it.getJSONArray("tasks") }
        AppointmentDetail(o.integer("business"), item(o.getJSONObject("appointment")), fields.nullText("notes"), named(fields.nullObject("service")), named(fields.nullObject("resource")),
            fields.nullObject("client")?.nullInteger("id"), tasks?.let { rows -> (0 until rows.length()).map { task(rows.getJSONObject(it)) } }, o.nullObject("payload_budget")?.nullInteger("max_related_per_section"))
    }
    fun clients(json: String): ClientList = parse {
        val o = JSONObject(json); val items = o.getJSONArray("items")
        ClientList(o.integer("business"), (0 until items.length()).map { index ->
            val client = items.getJSONObject(index)
            ClientContact(client.integer("id"), client.nullText("title"), client.nullText("phone"), client.nullText("email"))
        }, o.getJSONObject("summary").integer("total"))
    }
    // Existing full ClientSerializer creation response; bounded _client_item stays four-field read.
    fun clientCreateAction(json:String):ClientContact = parse {
        val o=JSONObject(json)
        ClientContact(o.integer("id"),null,o.text("phone"),o.text("email"),o.integer("business"),o.text("full_name"),o.text("source"),o.text("notes"),o.text("created_at"),o.text("updated_at"))
    }
    private fun conversation(o: JSONObject) = InboxConversation(o.integer("id"), o.nullText("title"), o.nullText("channel"), o.integer("unread_count"), o.nullObject("last_message_preview")?.let { InboxPreview(it.nullText("text")) },o.opt("handoff_required") as? Boolean)
    fun inbox(json: String): InboxList = parse {
        val o = JSONObject(json); val items = o.getJSONArray("items")
        InboxList(o.integer("business"), (0 until items.length()).map { conversation(items.getJSONObject(it)) }, o.getJSONObject("summary").integer("open"))
    }
    fun thread(json: String): InboxThread = parse {
        val o = JSONObject(json); val messages = o.getJSONArray("messages")
        InboxThread(o.integer("business"), conversation(o.getJSONObject("conversation")), (0 until messages.length()).map { index ->
            val message = messages.getJSONObject(index)
            InboxMessage(message.integer("id"), message.integer("conversation_id"), message.nullText("direction"), message.nullText("sender_type"), message.nullText("text"), message.nullText("created_at"),InboxMessageState.from(message.opt("status")))
        }, o.getJSONObject("payload_budget").integer("max_messages"), o.nullObject("details")?.nullObject("client")?.nullInteger("id"), o.nullObject("details")?.nullText("status"))
    }
    private fun task(o: JSONObject) = WorkTask(o.integer("id"), o.nullText("title"), o.text("status"), o.nullText("priority"), o.nullText("due_at"), o.nullInteger("client_id"))
    fun tasks(json: String): TaskPage = parse {
        val o = JSONObject(json); val items = o.getJSONArray("items")
        TaskPage(o.integer("business"), (0 until items.length()).map { task(items.getJSONObject(it)) }, o.getJSONObject("summary").integer("total"))
    }
    // Existing TaskCommentSerializer action shape, not the bounded detail author miniobject.
    fun taskCommentAction(json: String): TaskComment = parse {
        val o=JSONObject(json)
        TaskComment(o.integer("id"),o.text("text"),o.text("created_at"),o.integer("task"),o.integer("author"),o.text("author_name"),o.text("author_email"))
    }
    private fun schedule(o: JSONObject,key: String): TaskScheduleValue {
        if(!o.has(key))return TaskScheduleValue.Unknown
        if(o.isNull(key))return TaskScheduleValue.NotSet
        val raw=o.opt(key) as? String ?: return TaskScheduleValue.Unknown
        return if(runCatching {java.time.Instant.parse(raw)}.isSuccess)TaskScheduleValue.At(raw) else TaskScheduleValue.Unknown
    }
    // Existing TaskSerializer cancellation response fields. No full-original/version claim.
    fun taskCancelAction(json: String): WorkTask = parse {
        val o=JSONObject(json)
        WorkTask(o.integer("id"),o.nullText("title"),o.text("status"),o.nullText("priority"),o.nullText("due_at"),business=o.integer("business"),cancelledAt=o.text("cancelled_at"),cancelledBy=o.integer("cancelled_by"),cancelReason=o.text("cancel_reason"),updatedAt=o.text("updated_at"))
    }
    private fun userRead(o: JSONObject,key: String): MobileUserRead {
        if(!o.has(key))return MobileUserRead.Unknown
        if(o.isNull(key))return MobileUserRead.NotSet
        val user=o.opt(key) as? JSONObject ?: return MobileUserRead.Unknown
        return try {val item=MobileUserItem(user.integer("id"),user.text("email"),user.text("full_name"));if(item.valid)MobileUserRead.Person(item) else MobileUserRead.Unknown} catch(_: Exception) {MobileUserRead.Unknown}
    }
    // Existing TaskSerializer manual-create response subset; not a complete editable original.
    fun taskCreateAction(json: String): WorkTask = parse {
        val o=JSONObject(json)
        WorkTask(o.integer("id"),o.text("title"),o.text("status"),o.text("priority"),o.nullText("due_at"),business=o.integer("business"),updatedAt=o.text("updated_at"),description=o.text("description"),createdBy=o.integer("created_by"),createdAt=o.text("created_at"))
    }
    fun taskDetails(json: String): TaskDetails = parse {
        val o = JSONObject(json); val comments = o.getJSONArray("comments")
        TaskDetails(o.integer("business"), task(o.getJSONObject("task")), o.getJSONObject("details").nullText("description"), (0 until comments.length()).map { index ->
            val comment = comments.getJSONObject(index)
            TaskComment(comment.integer("id"), comment.nullText("text"), comment.nullText("created_at"),authorRead=userRead(comment,"author"))
        }, o.getJSONObject("payload_budget").integer("max_comments"), o.getJSONObject("details").nullInteger("appointment_id"),schedule(o.getJSONObject("details"),"reminder_at"),schedule(o.getJSONObject("details"),"snoozed_until"),userRead(o.getJSONObject("details"),"created_by"),userRead(o.getJSONObject("details"),"assignee"),TaskAppointmentOriginal.decode(json),TaskClientOriginal.decode(json))
    }
    private fun notification(n:JSONObject)=CRMNotification(n.integer("id"),n.nullText("text"),n.nullText("category"),n.nullText("priority"),n.nullText("status"),n.nullText("channel"),n.nullText("send_at"),n.nullText("read_at"),n.has("read_at"),n.nullText("action_url"),if(n.isNull("appointment_id"))null else n.integer("appointment_id"))
    fun notifications(json: String): NotificationPage = parse {
        val o=JSONObject(json);val items=o.getJSONArray("items")
        NotificationPage(o.integer("business"),(0 until items.length()).map {notification(items.getJSONObject(it))},o.getJSONObject("summary").integer("total"))
    }
    fun notificationMarkUnreadReply(json:String):NotificationMarkUnreadReply = parse {
        val o=JSONObject(json)
        require(o.has("read_at") && o.isNull("read_at") && o.has("appointment") && o.get("is_read") is Boolean && o.get("is_read")==false)
        NotificationMarkUnreadReply(o.integer("id"),o.integer("business"),o.get("text") as String,o.get("category") as String,o.get("priority") as String,o.get("status") as String,o.get("channel") as String,o.get("send_at") as String,o.get("action_url") as String,if(o.isNull("appointment"))null else o.integer("appointment"),o.get("updated_at") as String)
    }
    fun notificationMarkReadReply(json:String):NotificationMarkReadReply = parse {
        val o=JSONObject(json)
        NotificationMarkReadReply(o.get("ok") as? Boolean ?: throw IllegalArgumentException("Expected boolean"),notification(o.getJSONObject("notification")),o.get("replayed") as? Boolean ?: throw IllegalArgumentException("Expected boolean"))
    }
    fun clientProfile(json: String): ClientProfile = parse {
        val o = JSONObject(json); val client = o.getJSONObject("client"); val fields = o.getJSONObject("related"); val related = fields.getJSONArray("appointments")
        val tasks = if (fields.isNull("tasks")) null else fields.getJSONArray("tasks")
        val conversations = if (fields.isNull("conversations")) null else fields.getJSONArray("conversations")
        ClientProfile(o.integer("business"), ClientContact(client.integer("id"), client.nullText("title"), client.nullText("phone"), client.nullText("email")), o.getJSONObject("details").nullText("notes"),
            (0 until related.length()).map { index -> val visit = related.getJSONObject(index); ClientVisit(item(visit), visit.integer("client_id")) }, o.getJSONObject("payload_budget").integer("max_related_per_section"),
            tasks?.let { rows -> (0 until rows.length()).map { task(rows.getJSONObject(it)) } },
            conversations?.let { rows -> (0 until rows.length()).map { conversation(rows.getJSONObject(it)) } },
            ClientEditReadFields(client.opt("title") as? String,client.opt("phone") as? String,client.opt("email") as? String,client.opt("source") as? String,client.opt("updated_at") as? String))
    }
    fun home(json: String): HomeSummary = parse {
        val o = JSONObject(json); val sections = o.getJSONObject("sections")
        HomeSummary(o.integer("business"), sections.nullObject("appointments")?.let { HomeAppointments(it.integer("today")) },
            sections.nullObject("tasks")?.let { HomeTasks(it.integer("open")) }, sections.nullObject("conversations")?.let { HomeConversations(it.integer("open"), it.integer("unread")) })
    }
    fun today(json: String): TodaySummary = parse {
        val o = JSONObject(json); val sections = o.getJSONObject("sections")
        TodaySummary(o.integer("business"), o.text("date"), o.integer("limit"), o.getJSONObject("payload_budget").integer("max_items_per_section"),
            sections.nullObject("appointments")?.let { section -> val rows = section.getJSONArray("items"); TodayAppointments(section.text("date"), section.integer("total"), (0 until rows.length()).map { item(rows.getJSONObject(it)) }) },
            sections.nullObject("tasks")?.let { section -> val rows = section.getJSONArray("items"); TodayTasks(section.text("date"), section.integer("total"), section.integer("overdue"), (0 until rows.length()).map { task(rows.getJSONObject(it)) }) })
    }
    fun actions(json: String): AttentionPage = parse {
        val o = JSONObject(json); val rows = o.getJSONArray("items")
        AttentionPage(o.integer("business"), o.integer("limit"), o.integer("total"), (0 until rows.length()).map { index ->
            val row = rows.getJSONObject(index); val entity = row.getJSONObject("entity")
            AttentionItem(row.text("key"), row.text("type"), row.integer("priority"), AttentionEntity(entity.integer("id"), entity.nullText("title"), entity.nullText("href")))
        }, o.getJSONObject("payload_budget").integer("max_items"))
    }
    private fun <T> parse(block: () -> T): T = try { block() } catch (_: Exception) { throw ReadException(ReadProblem.INVALID_PAYLOAD) }
}
