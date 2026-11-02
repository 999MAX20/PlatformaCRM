package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import java.net.URI
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class BackendReadTransportTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().use {it.readText()}
    @Test fun publicConfigExactMillisecondsAndHTTPStatusesFeedExistingRepositoryWithoutFallback()=runTest {
        val catalog=JSONObject(fixture("backend-read-transport.json"));val cases=catalog.getJSONArray("config_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val values=row.getJSONObject("values");val map=values.keys().asSequence().associateWith {values.getString(it)};val expected=row.getString("expected")
            try {val config=NativeConnectionConfiguration(map);assertEquals("configured",expected);assertEquals(row.getLong("milliseconds"),config.timeoutMillis)}
            catch(error:NativeConnectionConfigurationException) {assertEquals(if(error.problem==NativeConnectionConfigurationProblem.UNCONFIGURED)"unconfigured" else "unexpectedKey",expected)}
            catch(error:RequestConfigurationException) {assertEquals(if(error.problem==RequestConfigurationProblem.INVALID_ORIGIN)"invalidOrigin" else "invalidTimeout",expected)}
        }
        val config=NativeConnectionConfiguration(mapOf("CRM_API_ORIGIN" to catalog.getString("origin"),"CRM_READ_TIMEOUT_SECONDS" to "1.25"));val statuses=catalog.getJSONArray("status_cases")
        for(n in 0 until statuses.length()) {
            val row=statuses.getJSONObject(n);val status=row.getInt("status");val expected=row.getString("expected");val body=if(status==200)fixture(row.getString("response_fixture")) else "not a success DTO";val descriptors=mutableListOf<NativeReadDescriptor>()
            val transport=BackendReadTransport(config.requestBuilder(),NativeReadHTTPExchange {r->descriptors+=r;ReadResponse(status,body)})
            assertEquals(status,transport.get(ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "101"))).status)
            try {val list=APIReadRepository(transport).clients(101);assertEquals("loaded",expected);assertEquals(listOf(701,702),list.items.map {it.id})}
            catch(error:ReadException) {assertEquals(when(error.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"},expected)}
            assertEquals(2,descriptors.size);assertTrue(descriptors.all {it.method=="GET" && it.uri.host=="fixture-api.example.invalid" && it.timeoutMillis==1250L && it.headers==mapOf("Accept" to "application/json")})
            try {transport.get(ReadRequest("/api/mobile/v1/../outside/"));fail("Invalid path entered exchange")}catch(error:RequestConfigurationException){assertEquals(RequestConfigurationProblem.INVALID_PATH,error.problem);assertEquals(2,descriptors.size)}
        }
        val broken=BackendReadTransport(config.requestBuilder(),NativeReadHTTPExchange {ReadResponse(200,"{")})
        try {APIReadRepository(broken).clients(101);fail("Malformed200 became fixture success")}catch(error:ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,error.problem)}
    }
    @Test fun configuredActualViewModelPreservesOwnerInputAndCancellationWithoutNetwork()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val pending=mutableListOf<CompletableDeferred<ReadResponse>>();val descriptors=mutableListOf<NativeReadDescriptor>()
        val config=NativeConnectionConfiguration(mapOf("CRM_API_ORIGIN" to "https://fixture-api.example.invalid","CRM_READ_TIMEOUT_SECONDS" to "7"))
        val transport=BackendReadTransport(config.requestBuilder(),NativeReadHTTPExchange {r->descriptors+=r;CompletableDeferred<ReadResponse>().also {pending+=it}.await()});val model=ClientDirectoryViewModel(APIReadRepository(transport))
        try {
            model.load(101,12);runCurrent();model.load(202,13);runCurrent();pending[1].complete(ReadResponse(200,fixture("clients-202.json")));runCurrent();pending[0].complete(ReadResponse(200,fixture("clients-101.json")));runCurrent()
            assertEquals(202,model.state.business);assertEquals(listOf(801),model.state.items.map {it.id});assertNull(model.state.problem)
            model.draft.open(ClientDraftContext(202,13));val selection=model.draft.state.selection!!;model.draft.update(ClientDraftField.FULL_NAME,"Unsent configured draft",selection)
            model.load(202,13);runCurrent();pending[2].complete(ReadResponse(503,""));runCurrent();assertEquals(ReadProblem.UNAVAILABLE,model.state.problem);assertTrue(model.state.items.isEmpty());assertEquals("Unsent configured draft",model.draft.state.values.fullName)
            model.load(202,13);runCurrent();pending[3].complete(ReadResponse(403,"bad body"));runCurrent();assertEquals(ReadProblem.DENIED,model.state.problem);assertTrue(model.state.items.isEmpty());assertEquals("Unsent configured draft",model.draft.state.values.fullName)
            assertEquals(4,descriptors.size);assertTrue(descriptors.all {it.uri.path=="/api/mobile/v1/clients/" && it.timeoutMillis==7000L && it.method=="GET"})
            val held=CompletableDeferred<ReadResponse>();val cancellable=BackendReadTransport(config.requestBuilder(),NativeReadHTTPExchange {held.await()});val task=async {cancellable.get(ReadRequest("/api/mobile/v1/clients/"))};runCurrent();task.cancel();held.complete(ReadResponse(200,"{}"));assertTrue(task.isCancelled)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
