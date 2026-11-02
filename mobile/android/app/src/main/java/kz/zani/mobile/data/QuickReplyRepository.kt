package kz.zani.mobile.data

import android.content.res.AssetManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kz.zani.mobile.core.*

interface QuickReplyRepository {suspend fun quickReplies(business: Int,channel: String): QuickReplyPage}
// DEBUG fixture source only; no web/native route or authorization mapping added.
class FixtureQuickReplyRepository(private val assets: AssetManager): QuickReplyRepository {
    override suspend fun quickReplies(business: Int,channel: String): QuickReplyPage=withContext(Dispatchers.IO) {
        if(business !in listOf(101,202) || channel !in QuickReplyContext.channels)throw ReadException(ReadProblem.INVALID_CONTEXT)
        try {JsonContracts.quickReplies(assets.open("fixtures/quick-replies-$business-$channel.json").bufferedReader().use {it.readText()})}
        catch(error: ReadException) {throw error}
        catch(error: Exception) {throw ReadException(ReadProblem.UNAVAILABLE)}
    }
}
