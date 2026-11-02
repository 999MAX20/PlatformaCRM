package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskFileMetadataTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun port()=FixtureTaskFileMetadataPort(fixture("task-file-metadata"))
    private val context=TaskFileMetadataContext(101,1101,180,1)
    private class Controlled:TaskFileMetadataPort {val calls=mutableListOf<TaskFileMetadataContext>();val pending=mutableListOf<CompletableDeferred<String>>()
        override suspend fun read(context:TaskFileMetadataContext):String {calls+=context;return CompletableDeferred<String>().also {pending+=it}.await()}
    }
    @Test fun metadataUsesExactStringID64bitSizeAndNoBlankTypeDefault()=runTest {
        val rows=TaskFileMetadata.window(port().read(context),context);assertEquals(2,rows.size);assertEquals(4294967296L,rows[0].size);assertEquals("",rows[1].contentType);assertEquals(0L,rows[1].size)
        assertFalse(rows.toString().contains("download_url"));assertFalse(rows.toString().contains("https:"));assertFalse(rows.toString().contains("scan_status"))
    }
    @Test fun shared37CasesRejectForeignMalformedDuplicateAndMissingRows()=runTest {
        val cases=JSONObject(fixture("task-file-metadata")).getJSONArray("validation_cases");assertEquals(37,cases.length())
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val decoded=runCatching {TaskFileMetadata.window(row.get("body").toString(),context)}.getOrNull();assertEquals(row.getString("name"),row.getBoolean("valid"),decoded!=null)
            if(decoded!=null) {val text=decoded.toString();assertFalse(text.contains("download_url"));assertFalse(text.contains("scan_status"));assertFalse(text.contains("https:"));assertFalse(text.contains("lease"))}
        }
    }
    @Test fun fixtureFlagCannotBeStringAndInvalidContextNeverReads()=runTest {
        val raw=JSONObject(fixture("task-file-metadata")).put("fixture_only","true");assertTrue(runCatching {FixtureTaskFileMetadataPort(raw.toString()).read(context)}.isFailure);assertTrue(runCatching {port().read(context.copy(epoch=0))}.isFailure)
    }
    @Test fun pendingReadCannotDuplicateAndLateResponseCannotChangeOwner()=runTest {
        val p=Controlled();val m=TaskFileMetadataModel(p,backgroundScope);m.bind(context);val job=async {m.load(m.control)};runCurrent();m.load(m.control);assertEquals(1,p.calls.size);assertTrue(m.loading);assertTrue(m.items.isEmpty())
        m.bind(TaskFileMetadataContext(202,1201,181,2));val replacement=m.control;p.pending[0].complete(port().read(context));job.await();assertEquals(replacement,m.control);assertFalse(m.loaded);assertFalse(m.failed);assertTrue(m.items.isEmpty())
    }
    @Test fun failedReadHidesPreviousWindowAndRequiresFreshExplicitControl()=runTest {
        val p=Controlled();val m=TaskFileMetadataModel(p,backgroundScope);m.bind(context);val old=m.control;val job=async {m.load(old)};runCurrent();p.pending[0].completeExceptionally(CancellationException("fixture"));job.await();assertTrue(m.failed);assertFalse(m.loaded);assertTrue(m.items.isEmpty());assertNull(m.selected)
        val retry=async {m.load(m.control)};runCurrent();p.pending[1].complete(port().read(context));retry.await();m.select(m.items[0],old);assertNull(m.selected)
    }
    @Test fun capturedBackCannotClearNewIdenticalSelection()=runTest {
        val m=TaskFileMetadataModel(port(),backgroundScope);m.bind(context);m.load(m.control);val row=m.items[0];m.select(row,m.control);val old=m.control;m.load(old);assertEquals(row,m.selected);m.back(old);m.select(row,m.control);val current=m.control;m.back(old);assertEquals(current,m.control);assertEquals(row,m.selected)
    }
    @Test fun oldIdenticalWindowControlCannotSelectAfterRefresh()=runTest {
        val m=TaskFileMetadataModel(port(),backgroundScope);m.bind(context);m.load(m.control);val old=m.control;val row=m.items[0];m.load(m.control);m.select(row,old);assertNull(m.selected);assertEquals(row,m.items[0])
    }
    @Test fun closedContextIgnoresLateReadErrorAndEmptyIsOnlyWindow()=runTest {
        val p=Controlled();val m=TaskFileMetadataModel(p,backgroundScope);m.bind(context);val job=async {m.load(m.control)};runCurrent();m.bind(null);p.pending[0].completeExceptionally(CancellationException("fixture"));job.await();assertNull(m.control);assertFalse(m.failed);assertTrue(m.items.isEmpty())
        val empty=TaskFileMetadataModel(port(),backgroundScope);empty.bind(context.copy(task=1401));empty.load(empty.control);assertTrue(empty.loaded);assertTrue(empty.items.isEmpty());assertFalse(empty.failed)
    }
    private inner class Repo:TaskReadRepository {var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return JsonContracts.taskDetails(fixture("task-$business-$id"))}
    }
    @Test fun defaultAndGetWithoutExactFixtureOriginDoNotOfferMetadata()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val plain=TaskListViewModel(repo);val m=TaskListViewModel(repo,fileMetadataPort=port())
        try {m.load(101,183);runCurrent();m.open(1101);runCurrent();assertNull(plain.fileMetadata);assertNull(m.fileMetadata!!.context)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pairedTaskMetadataSelectionDoesNotChangeTaskRowsOrIssueReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val original=JsonContracts.taskDetails(fixture("task-101-1101"));val origin=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==original};val m=TaskListViewModel(repo,commentSource=origin,fileMetadataPort=port())
        try {m.load(101,184);runCurrent();m.open(1101);runCurrent();val files=m.fileMetadata!!;val before=m.state.detail;val items=m.state.items;val reads=repo.reads;files.load(files.control);files.select(files.items[0],files.control);assertEquals(8101,files.selected!!.id);assertEquals(before,m.state.detail);assertEquals(items,m.state.items);assertEquals(reads,repo.reads);val previous=files.context!!;m.back();assertNull(files.control);assertTrue(files.items.isEmpty());m.open(1101);runCurrent();assertNotEquals(previous.revision,files.context!!.revision);assertFalse(files.loaded)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun metadataNavigationPreservesTaskActionRecordAndSource()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val original=JsonContracts.taskDetails(fixture("task-101-1101"));val origin=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==original}
        val m=TaskListViewModel(repo,commentSource=origin,startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),fileMetadataPort=port())
        try {m.load(101,185);runCurrent();m.open(1101);runCurrent();val before=m.state.detail;val a=m.startAction!!;m.prepareStart(a.control,m.control);a.submit(a.control);val record=a.submission;val files=m.fileMetadata!!;files.load(files.control);files.select(files.items[0],files.control);files.back(files.control);files.load(files.control);assertEquals(record,a.submission);assertEquals(1,a.retainedAttemptCount);assertEquals(before,m.state.detail);m.back();assertEquals(1,a.retainedAttemptCount);assertNull(files.control)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
