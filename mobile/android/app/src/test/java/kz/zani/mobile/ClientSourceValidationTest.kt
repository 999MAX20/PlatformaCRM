package kz.zani.mobile

import kz.zani.mobile.core.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ClientSourceValidationTest {
    private fun fixture()=javaClass.classLoader!!.getResourceAsStream("fixtures/client-create-validation.json")!!.bufferedReader().use {it.readText()}
    private fun field(raw:String)=when(raw){"fullName"->ClientDraftField.FULL_NAME;"phone"->ClientDraftField.PHONE;"email"->ClientDraftField.EMAIL;"source"->ClientDraftField.SOURCE;else->ClientDraftField.NOTES}
    private fun problem(raw:String)=when(raw){"name"->ClientDraftProblem.NAME;"nameLength"->ClientDraftProblem.NAME_LENGTH;"phoneLength"->ClientDraftProblem.PHONE_LENGTH;"emailLength"->ClientDraftProblem.EMAIL_LENGTH;"characters"->ClientDraftProblem.CHARACTERS;"email"->ClientDraftProblem.EMAIL;else->ClientDraftProblem.SOURCE}
    private fun issues(row:JSONObject,key:String):List<ClientDraftIssue> {val a=row.getJSONArray(key);return (0 until a.length()).map {i->val x=a.getJSONObject(i);ClientDraftIssue(field(x.getString("field")),problem(x.getString("problem")))}}
    @Test fun executedRawZodAndPythonSourceStagesAndPreviewAreSeparate() {
        val rows=JSONObject(fixture()).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val v=row.getJSONObject("values");val p=row.getJSONObject("preview");val value=ClientDraftValues(v.getString("fullName"),v.getString("phone"),v.getString("email"),v.getString("source"),v.getString("notes"))
            assertEquals(row.getString("name"),ClientDraftPreview(p.getString("fullName"),p.getString("phone"),p.getString("email"),p.getString("source"),p.getString("notes")),value.preview)
            assertEquals(issues(row,"webIssues"),value.webIssues);assertEquals(issues(row,"sourceIssues"),value.sourceIssues);assertEquals(issues(row,"issues"),value.issues)
            val edit=ClientEditValues(value.fullName,value.phone,value.email,value.source);assertEquals(value.issues.filter {it.field!=ClientDraftField.NOTES},edit.issues)
            assertEquals(listOf(ClientDraftField.FULL_NAME,ClientDraftField.PHONE,ClientDraftField.EMAIL,ClientDraftField.SOURCE),ClientEditValues.fields)
        }
    }
    @Test fun invalidUTF16AllStringFieldsAndValidNonBMPDoNotInventMinOrCap() {
        val rows=JSONObject(fixture()).getJSONArray("kotlin_utf16_cases")
        for(n in 0 until rows.length()) {val row=rows.getJSONObject(n);val f=field(row.getString("field"));val u=row.getJSONArray("units");val raw=CharArray(u.length()) {u.getInt(it).toChar()}.concatToString();var v=ClientDraftValues(fullName="Client")
            v=when(f){ClientDraftField.FULL_NAME->v.copy(fullName=raw);ClientDraftField.PHONE->v.copy(phone=raw);ClientDraftField.EMAIL->v.copy(email=raw);else->v.copy(notes=raw)};assertTrue(v.sourceIssues.contains(ClientDraftIssue(f,ClientDraftProblem.CHARACTERS)))
        }
        assertTrue(ClientDraftValues(fullName="😀",notes="N".repeat(10000)).issues.isEmpty());assertTrue(ClientDraftValues(fullName="Client",email="x".repeat(100)+"@example.com").issues.isEmpty())
    }
    @Test fun immutablePreviewBackFieldErrorsAndOldModalPreserveRaw() {
        val a=ClientDraftContext(101,1);val m=ClientDraftModel();m.bind(a);m.open(a);val s=m.state.selection!!;m.update(ClientDraftField.FULL_NAME,"\u001C A \u001F",s);m.update(ClientDraftField.NOTES," \uFEFFNotes\uFEFF ",s);val raw=m.state.values;m.prepare(s);val review=m.state.review!!
        assertEquals("A",review.preview.fullName);assertEquals("\uFEFFNotes\uFEFF",review.preview.notes);assertEquals(raw,review.values);m.update(ClientDraftField.FULL_NAME,"late",s);assertEquals(review,m.state.review);m.back(s);assertEquals(raw,m.state.values)
        m.update(ClientDraftField.NOTES,"Bad\u0000notes",s);m.prepare(s);assertEquals(ClientDraftPhase.EDITING,m.state.phase);assertTrue(m.state.issues.contains(ClientDraftIssue(ClientDraftField.NOTES,ClientDraftProblem.CHARACTERS)))
        m.update(ClientDraftField.NOTES,"Good",s);m.prepare(s);m.close(s);m.open(a);val fresh=m.state.selection!!;m.discard(s);assertEquals(fresh,m.state.selection);assertEquals(raw.fullName,m.state.values.fullName);m.bind(a.copy(epoch=2));assertEquals(ClientDraftValues(),m.state.values);assertNull(m.state.review)
    }
}
