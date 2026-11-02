package kz.zani.mobile

import org.json.JSONObject
import kz.zani.mobile.core.*
import kz.zani.mobile.data.MobileAuthJSON
import org.junit.Assert.*
import org.junit.Test

class MobileAuthContractsTest {
    private fun catalog()=JSONObject(javaClass.classLoader!!.getResourceAsStream("fixtures/mobile-auth-contracts.json")!!.bufferedReader().use {it.readText()})
    private fun input(o:JSONObject):MobileLoginInput {
        fun optional(k:String)=if(!o.has(k) || o.isNull(k))null else o.getString(k)
        val d=MobileAuthDeviceInput(o.getString("device_id"),MobileDevicePlatform.entries.first {it.wire==o.getString("platform")},optional("app_version"),optional("build_number"),optional("os_version"),optional("device_model"))
        return MobileLoginInput(d,o.getString("email"),o.getString("password"),if(o.has("business"))o.getInt("business")else null)
    }
    @Test fun exactOptionalPresenceAndRawTextWithoutDefaultsOrSensitiveDebugOutput() {
        val catalog=catalog();assertTrue(catalog.getBoolean("fixture_only"));val cases=catalog.getJSONArray("request_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val v=row.getJSONObject("values");val expected=row.getJSONObject("expected_body");val body:String;val descriptions:List<String>
            when(row.getString("operation")) {
                "login"->{val x=input(v);body=MobileAuthJSON.loginBody(x);descriptions=listOf(x.toString(),x.device.toString())}
                "refresh"->{val x=MobileRefreshInput(v.getString("refresh"));body=MobileAuthJSON.refreshBody(x);descriptions=listOf(x.toString())}
                else->{val x=MobileLogoutInput(if(v.has("refresh"))v.getString("refresh")else null);body=MobileAuthJSON.logoutBody(x);descriptions=listOf(x.toString())}
            }
            val encoded=JSONObject(body);assertEquals(expected.keys().asSequence().toSet(),encoded.keys().asSequence().toSet())
            expected.keys().forEach {key->assertEquals(expected.get(key),encoded.get(key))}
            assertTrue(descriptions.all {it.contains("redacted") && !it.contains("synthetic-") && !it.contains("Example.invalid")})
        }
    }
    @Test fun exactResponseSchemasRejectMissingTypePolicyAndContextWithoutCreatingSession() {
        val catalog=catalog();val inputs=catalog.getJSONObject("login_inputs");val rows=catalog.getJSONArray("response_cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val body=row.getJSONObject("body");val expected=row.getString("expected")
            try {
                when(row.getString("operation")) {
                    "login"->{val reply=MobileAuthJSON.loginResponse(body.toString(),input(inputs.getJSONObject(row.getString("input"))));assertEquals(body.getString("access"),reply.tokens.access);assertEquals(body.getString("refresh"),reply.tokens.refresh);assertEquals(body.getJSONObject("business").getInt("id"),reply.business.id);assertEquals(reply.business.id,reply.device.business);assertEquals(body.getJSONObject("device").getInt("id"),reply.device.id);assertEquals(body.getJSONObject("business").getJSONArray("permissions").length(),reply.business.permissions.size);assertEquals(body.getJSONObject("business").getString("name"),reply.business.name);assertEquals("MobileLoginReply(redacted)",reply.toString());assertEquals("MobileTokenReply(redacted)",reply.tokens.toString())}
                    "refresh"->{val reply=MobileAuthJSON.refreshResponse(body.toString());assertEquals(body.getString("access"),reply.access);assertEquals(body.getString("refresh"),reply.refresh)}
                    else->assertTrue(MobileAuthJSON.logoutResponse(body.toString()).ok)
                }
                assertEquals("loaded",expected)
            } catch(error:MobileAuthContractException) {assertEquals(if(error.problem==MobileAuthContractProblem.CONTEXT_MISMATCH)"contextMismatch" else "invalidPayload",expected)}
        }
    }
    @Test fun suppliedPermissionCollectionsAreSnapshotsAndNeverCreateDefaults() {
        val source=mutableListOf(MobilePermissionDescriptor("clients","read","BUSINESS"));val value=MobileAuthBusiness(101,"Synthetic","synthetic","service","","Asia/Almaty","kk","KZT","active",source);source.clear();assertEquals(1,value.permissions.size);assertEquals("clients",value.permissions[0].resource)
        val empty=MobileAuthBusiness(101,"Synthetic","synthetic","service","","Asia/Almaty","kk","KZT","active",emptyList());assertTrue(empty.permissions.isEmpty())
    }
}
