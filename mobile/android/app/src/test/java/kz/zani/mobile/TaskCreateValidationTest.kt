package kz.zani.mobile

import kz.zani.mobile.core.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class TaskCreateValidationTest {
    private fun fixture()=javaClass.classLoader!!.getResourceAsStream("fixtures/task-create-validation.json")!!.bufferedReader().use {it.readText()}
    private val context=TaskDraftContext(101,1)
    private fun field(value: String)=when(value){"title"->TaskDraftField.TITLE;"description"->TaskDraftField.DESCRIPTION;else->TaskDraftField.PRIORITY}
    private fun problem(value: String)=when(value){"required"->TaskDraftProblem.REQUIRED;"titleLength"->TaskDraftProblem.TITLE_LENGTH;"characters"->TaskDraftProblem.CHARACTERS;else->TaskDraftProblem.PRIORITY}
    @Test fun sourceExecutedTitleJSAndDescriptionPythonOnlyTrimValidationVectors() {
        val cases=JSONObject(fixture()).getJSONArray("cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val value=TaskDraftValues(row.getString("title"),row.getString("description"),row.getString("priority"));val p=row.getJSONObject("preview");val issues=row.getJSONArray("issues")
            assertEquals(row.getString("name"),TaskDraftPreview(p.getString("title"),p.getString("description"),p.getString("priority")),value.preview)
            assertEquals((0 until issues.length()).map {i->val e=issues.getJSONObject(i);TaskDraftIssue(field(e.getString("field")),problem(e.getString("problem")))},value.issues)
            assertEquals(row.getString("title"),value.title);assertEquals(row.getString("description"),value.description)
        }
    }
    @Test fun unicodeCodepoint255AndInvalidUnpairedUTF16BothFieldsNotDescriptionReadOrReasonCap() {
        val cases=JSONObject(fixture()).getJSONArray("kotlin_utf16_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val units=row.getJSONArray("units");val raw=CharArray(units.length()) {units.getInt(it).toChar()}.concatToString();val f=field(row.getString("field"));val value=if(f==TaskDraftField.TITLE)TaskDraftValues(title=raw) else TaskDraftValues(title="A",description=raw)
            assertTrue(value.issues.contains(TaskDraftIssue(f,TaskDraftProblem.CHARACTERS)))
        }
        assertTrue(TaskDraftValues(title="😀".repeat(255),description="D".repeat(9000)).issues.isEmpty());assertTrue(TaskDraftValues(title="😀".repeat(256)).issues.any {it.problem==TaskDraftProblem.TITLE_LENGTH})
        assertTrue(TaskDraftValues(title="A").issues.isEmpty())
    }
    @Test fun immutableNormalizedPreviewAndBackKeepRawAndDescriptionErrorIsFieldOwned() {
        val m=TaskDraftModel();m.bind(context);m.open(context);val s=m.state.selection!!
        m.update(TaskDraftField.TITLE," \uFEFF Title \uFEFF ",s);m.update(TaskDraftField.DESCRIPTION," \uFEFF Description \uFEFF ",s);val raw=m.state.values;m.prepare(s);val review=m.state.review!!
        assertEquals("Title",review.preview.title);assertEquals("\uFEFF Description \uFEFF",review.preview.description);assertEquals(raw,review.values)
        m.update(TaskDraftField.TITLE,"late",s);assertEquals(review,m.state.review);m.back(s);assertEquals(raw,m.state.values)
        m.update(TaskDraftField.DESCRIPTION,"Bad\u0000description",s);m.prepare(s);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertTrue(m.state.issues.contains(TaskDraftIssue(TaskDraftField.DESCRIPTION,TaskDraftProblem.CHARACTERS)));assertEquals(raw.title,m.state.values.title)
        m.update(TaskDraftField.DESCRIPTION,"Good",s);assertFalse(m.state.issues.any {it.field==TaskDraftField.DESCRIPTION})
    }
    @Test fun oldModalAndNewEpochCannotMutateOrExposeSourcePreview() {
        val m=TaskDraftModel();m.bind(context);m.open(context);val old=m.state.selection!!;m.update(TaskDraftField.TITLE," Title ",old);m.prepare(old);m.close(old);m.open(context);val fresh=m.state.selection!!
        m.discard(old);m.update(TaskDraftField.TITLE,"old callback",old);assertEquals(fresh,m.state.selection);assertEquals(" Title ",m.state.values.title)
        m.bind(context.copy(epoch=2));assertEquals(TaskDraftValues(),m.state.values);assertNull(m.state.review);assertNull(m.state.selection)
    }
}
