package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Explicit DEBUG fixture dependency only. No HTTP implementation or POST transport.
class FixtureTaskCreatePort private constructor(private val catalog: JSONObject): SyntheticTaskCreatePort {
    constructor(assets: AssetManager):this(JSONObject(assets.open("fixtures/task-create-outcome.json").bufferedReader().use {it.readText()}))
    init {require(catalog.getBoolean("fixture_only"))}
    private val rows=catalog.getJSONArray("scenarios")
    override val grants=(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskCreateGrant(g.getInt("business"),g.getInt("actor"),g.getBoolean("create"))}
    override suspend fun execute(attempt: TaskCreateAttempt): SyntheticTaskCreateOutcome {
        val index=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization}
        if(index<0)return SyntheticTaskCreateOutcome.Unknown
        val row=rows.getJSONObject(index)
        return when(row.getString("outcome")) {
            "rejected_without_write"->SyntheticTaskCreateOutcome.RejectedWithoutWrite
            "response"->{val v=attempt.review.preview;val original=JsonContracts.taskCreateAction(row.getJSONObject("response").toString());SyntheticTaskCreateOutcome.Response(201,original.copy(title=v.title,description=v.description,priority=v.priority,dueAt=v.dueAt ?: original.dueAt),reminderAt=v.reminderAt,clientRead=v.clientID?.let {TaskCreateClientRead.Client(it)} ?: TaskCreateClientRead.NotSet,appointmentRead=v.appointmentID?.let {TaskCreateAppointmentRead.Appointment(it)} ?: TaskCreateAppointmentRead.NotSet,parentRead=v.parentTaskID?.let {TaskCreateParentRead.Parent(it)} ?: TaskCreateParentRead.NotSet)}
            else->SyntheticTaskCreateOutcome.Unknown
        }
    }
}
