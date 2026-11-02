package kz.zani.mobile.data

import android.content.res.AssetManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kz.zani.mobile.core.*

interface ClientEditOriginProvider {suspend fun origin(profile: ClientProfile): ClientEditOrigin?}
// Explicit fixture-only origin verification, never a live EDIT grant.
class FixtureClientEditOriginProvider(private val assets: AssetManager): ClientEditOriginProvider {
    companion object {
        internal fun verified(profile: ClientProfile,reference: ClientProfile): ClientEditOrigin? {
            if(profile.business !in listOf(101,202) || !profile.validFor(profile.business,profile.client.id) || !reference.validFor(profile.business,profile.client.id) || reference.editReadFields!=profile.editReadFields)return null
            return reference.editReadFields?.complete
        }
    }
    override suspend fun origin(profile: ClientProfile): ClientEditOrigin?=withContext(Dispatchers.IO) {
        if(!profile.validFor(profile.business,profile.client.id) || profile.business !in listOf(101,202))return@withContext null
        try {
            val reference=JsonContracts.clientProfile(assets.open("fixtures/client-${profile.business}-${profile.client.id}.json").bufferedReader().use {it.readText()})
            verified(profile,reference)
        } catch(error: Exception) {if(error is kotlinx.coroutines.CancellationException)throw error;null}
    }
}
