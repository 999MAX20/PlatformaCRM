package kz.zani.mobile.data
import kz.zani.mobile.core.*
import org.json.JSONObject

interface LeadReadRepository {suspend fun leads(business:Int,search:String):LeadReadPage;suspend fun lead(business:Int,id:Int):LeadReadDetail}
object LeadReadJSON {
    private fun JSONObject.int(k:String):Int {val v=get(k);require(v is Number);return v.toString().toBigDecimal().intValueExact()}
    private fun JSONObject.text(k:String)=get(k) as? String ?: throw IllegalArgumentException()
    private fun item(o:JSONObject):LeadReadItem {val c=o.getJSONObject("client");return LeadReadItem(o.int("id"),o.int("client_id"),o.text("title"),LeadReadClient(c.int("id"),c.text("name"),c.text("phone"),c.text("email")),o.text("status"),o.text("source"),o.text("message"),o.text("created_at"))}
    fun page(raw:String):LeadReadPage=try {val o=JSONObject(raw);val rows=o.getJSONArray("items");LeadReadPage(o.int("business"),o.int("limit"),o.getJSONObject("summary").int("total"),(0 until rows.length()).map {item(rows.getJSONObject(it))})}catch(_:Exception){throw ReadException(ReadProblem.INVALID_PAYLOAD)}
    fun detail(raw:String):LeadReadDetail=try {val o=JSONObject(raw);LeadReadDetail(o.int("business"),item(o.getJSONObject("lead")),o.getJSONObject("details").text("message"))}catch(_:Exception){throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class APILeadReadRepository(private val transport:ReadTransport):LeadReadRepository {
    private suspend fun body(request:ReadRequest):String {val r=transport.get(request);return when(r.status){200->r.body;403->throw ReadException(ReadProblem.DENIED);404->throw ReadException(ReadProblem.NOT_FOUND);else->throw ReadException(ReadProblem.UNAVAILABLE)}}
    override suspend fun leads(business:Int,search:String):LeadReadPage {if(business<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);val p=LeadReadJSON.page(body(ReadRequest("/api/mobile/v1/leads/",mapOf("business" to "$business","limit" to "50","search" to SourceTextTrim.pythonStrip(search)))));if(!p.validFor(business))throw ReadException(ReadProblem.INVALID_PAYLOAD);return p}
    override suspend fun lead(business:Int,id:Int):LeadReadDetail {if(business<=0 || id<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);val p=LeadReadJSON.detail(body(ReadRequest("/api/mobile/v1/leads/$id/",mapOf("business" to "$business"))));if(!p.validFor(business,id))throw ReadException(ReadProblem.INVALID_PAYLOAD);return p}
}
