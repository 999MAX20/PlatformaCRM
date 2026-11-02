package kz.zani.mobile.data

import android.content.res.AssetManager
import kotlinx.coroutines.*
import kz.zani.mobile.core.TaskDetails

interface TaskCommentDraftSource {suspend fun matchesFixture(detail: TaskDetails): Boolean}
class FixtureTaskCommentDraftSource(private val assets: AssetManager): TaskCommentDraftSource {
    // Pure typed fixture-reference identity; GET visibility is not command permission or JSON-byte proof.
    companion object {internal fun verified(detail: TaskDetails,reference: TaskDetails)=detail.business in listOf(101,202) && detail.validFor(detail.business,detail.task.id) && detail==reference}
    override suspend fun matchesFixture(detail: TaskDetails)=withContext(Dispatchers.IO) {
        if(!detail.validFor(detail.business,detail.task.id) || detail.business !in listOf(101,202))return@withContext false
        try {verified(detail,JsonContracts.taskDetails(assets.open("fixtures/task-${detail.business}-${detail.task.id}.json").bufferedReader().use {it.readText()}))}
        catch(error: Exception) {if(error is CancellationException)throw error;false}
    }
}
