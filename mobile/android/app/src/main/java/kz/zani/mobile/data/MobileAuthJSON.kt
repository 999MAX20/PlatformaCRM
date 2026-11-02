package kz.zani.mobile.data

import org.json.JSONObject
import kz.zani.mobile.core.*

// Pure serialization/decoding. No HTTP/session/credential provider or operation port.
object MobileAuthJSON {
    fun loginBody(input:MobileLoginInput):String=JSONObject().apply {
        put("device_id",input.device.deviceID);put("platform",input.device.platform.wire);put("email",input.email);put("password",input.password)
        input.business?.let {put("business",it)};input.device.appVersion?.let {put("app_version",it)};input.device.buildNumber?.let {put("build_number",it)}
        input.device.osVersion?.let {put("os_version",it)};input.device.deviceModel?.let {put("device_model",it)}
    }.toString()
    fun refreshBody(input:MobileRefreshInput):String=JSONObject().put("refresh",input.refresh).toString()
    fun logoutBody(input:MobileLogoutInput):String=JSONObject().apply {input.refresh?.let {put("refresh",it)}}.toString()
    private fun JSONObject.text(key:String)=get(key) as? String ?: throw MobileAuthContractException(MobileAuthContractProblem.INVALID_PAYLOAD)
    private fun JSONObject.integer(key:String):Int {val value=get(key);require(value is Number);return value.toString().toBigDecimal().intValueExact()}
    private fun JSONObject.nullText(key:String):String? {require(has(key));return if(isNull(key))null else text(key)}
    private fun platform(value:String)=MobileDevicePlatform.entries.first {it.wire==value}
    private fun tokens(o:JSONObject):MobileTokenReply {
        val access=o.text("access");val refresh=o.text("refresh");val kind=o.text("token_type")
        require(access.isNotEmpty() && refresh.isNotEmpty() && kind=="Bearer")
        return MobileTokenReply(access,refresh,kind)
    }
    private inline fun <T> parse(block:()->T):T=try {block()} catch(_:Exception) {throw MobileAuthContractException(MobileAuthContractProblem.INVALID_PAYLOAD)}
    fun loginResponse(json:String,input:MobileLoginInput):MobileLoginReply {
        val reply=parse {
            val o=JSONObject(json);val b=o.getJSONObject("business");val d=o.getJSONObject("device");val permissions=b.getJSONArray("permissions")
            val business=MobileAuthBusiness(b.integer("id"),b.text("name"),b.text("slug"),b.text("business_type"),b.text("city"),b.text("timezone"),b.text("language"),b.text("currency"),b.text("status"),(0 until permissions.length()).map {i->val p=permissions.getJSONObject(i);MobilePermissionDescriptor(p.text("resource"),p.text("action"),p.text("scope"))})
            val device=MobileAuthDeviceReply(d.integer("id"),d.integer("business"),platform(d.text("platform")),d.text("app_version"),d.text("build_number"),d.text("os_version"),d.text("device_model"),d.nullText("last_seen_at"),d.nullText("revoked_at"),d.text("created_at"),d.text("updated_at"))
            require(business.id>0 && device.id>0 && device.business==business.id)
            MobileLoginReply(tokens(o),business,device)
        }
        if(reply.device.platform!=input.device.platform || (input.business!=null && input.business!=reply.business.id))throw MobileAuthContractException(MobileAuthContractProblem.CONTEXT_MISMATCH)
        return reply
    }
    fun refreshResponse(json:String):MobileTokenReply=parse {tokens(JSONObject(json))}
    fun logoutResponse(json:String):MobileLogoutReply=parse {val ok=JSONObject(json).get("ok") as? Boolean ?: throw IllegalArgumentException();require(ok);MobileLogoutReply(ok)}
}
