package kz.zani.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import kz.zani.mobile.data.APIReadRepository
import kz.zani.mobile.data.APILeadReadRepository
import kz.zani.mobile.data.APIInboxLinkLeadRepository
import kz.zani.mobile.data.APIDealReadRepository
import kz.zani.mobile.data.APIInboxLinkDealRepository
import kz.zani.mobile.data.APITeamMemberReadRepository
import kz.zani.mobile.data.FixtureTeamMemberReadTransport
import kz.zani.mobile.data.APIInboxTaskSourceRepository
import kz.zani.mobile.data.FixtureInboxTaskSourceTransport
import kz.zani.mobile.data.FixtureInboxCreateTaskPort
import kz.zani.mobile.data.APIInboxExistingClientRepository
import kz.zani.mobile.data.FixtureInboxExistingClientReadTransport
import kz.zani.mobile.data.FixtureInboxExistingClientPort
import kz.zani.mobile.data.APIInboxExistingLeadRepository
import kz.zani.mobile.data.FixtureInboxExistingLeadReadTransport
import kz.zani.mobile.data.FixtureInboxExistingLeadPort
import kz.zani.mobile.data.APIInboxExistingDealRepository
import kz.zani.mobile.data.FixtureInboxExistingDealReadTransport
import kz.zani.mobile.data.FixtureInboxExistingDealPort
import kz.zani.mobile.data.APIInboxTargetAssignmentRepository
import kz.zani.mobile.data.FixtureInboxTargetAssignmentReadTransport
import kz.zani.mobile.data.FixtureInboxTargetAssignmentPort
import kz.zani.mobile.data.FixtureInboxLinkDealReadTransport
import kz.zani.mobile.data.FixtureInboxLinkDealPort
import kz.zani.mobile.data.FixtureDealReadTransport
import kz.zani.mobile.data.FixtureInboxLinkLeadReadTransport
import kz.zani.mobile.data.FixtureInboxLinkLeadPort
import kz.zani.mobile.data.FixtureLeadReadTransport
import kz.zani.mobile.data.FixtureTransport
import kz.zani.mobile.data.FixtureQuickReplyRepository
import kz.zani.mobile.data.FixtureClientMergePreviewSource
import kz.zani.mobile.data.FixtureClientEditOriginProvider
import kz.zani.mobile.data.FixtureNotificationMarkReadPort
import kz.zani.mobile.data.FixtureNotificationMarkUnreadPort
import kz.zani.mobile.data.FixtureClientDuplicatePreviewSource
import kz.zani.mobile.data.FixtureClientCreatePort
import kz.zani.mobile.data.FixtureTaskCreatePort
import kz.zani.mobile.data.APIInboxLinkClientRepository
import kz.zani.mobile.data.FixtureInboxLinkClientPort
import kz.zani.mobile.data.FixtureInboxLinkClientReadTransport
import kz.zani.mobile.data.APIInboxLifecycleRepository
import kz.zani.mobile.data.FixtureInboxLifecyclePort
import kz.zani.mobile.data.FixtureInboxLifecycleReadTransport
import kz.zani.mobile.data.APIInboxPriorityRepository
import kz.zani.mobile.data.FixtureInboxPriorityPort
import kz.zani.mobile.data.FixtureInboxPriorityReadTransport
import kz.zani.mobile.data.APIInboxReadMarkerRepository
import kz.zani.mobile.data.FixtureInboxReadMarkerPort
import kz.zani.mobile.data.FixtureInboxReadMarkerReadTransport
import kz.zani.mobile.data.APIInboxSelfAssignmentRepository
import kz.zani.mobile.data.FixtureInboxSelfAssignmentPort
import kz.zani.mobile.data.FixtureInboxSelfAssignmentReadTransport
import kz.zani.mobile.data.FixtureInboxRetryPort
import kz.zani.mobile.data.FixtureInboxRetryReadTransport
import kz.zani.mobile.data.FixtureInboxReplyPort
import kz.zani.mobile.data.FixtureHandoffPort
import kz.zani.mobile.data.APIAppointmentReferenceRepository
import kz.zani.mobile.data.APIAppointmentSlotRepository
import kz.zani.mobile.data.FixtureAppointmentSlotTransport
import kz.zani.mobile.data.APIServiceDirectoryRepository
import kz.zani.mobile.data.FixtureServiceDirectoryTransport
import kz.zani.mobile.data.APIResourceDirectoryRepository
import kz.zani.mobile.data.FixtureResourceDirectoryTransport
import kz.zani.mobile.data.FixtureAppointmentTerminalPort
import kz.zani.mobile.data.FixtureAppointmentBookingPort
import kz.zani.mobile.data.FixtureTaskUndoCancelPort
import kz.zani.mobile.data.FixtureTaskWatcherPort
import kz.zani.mobile.data.FixtureTaskFileMetadataPort
import kz.zani.mobile.data.FixtureTaskReopenPort
import kz.zani.mobile.data.FixtureTaskStartPort
import kz.zani.mobile.data.FixtureTaskSnoozePort
import kz.zani.mobile.data.FixtureTaskAssignPort
import kz.zani.mobile.data.FixtureTaskDescriptionEditPort
import kz.zani.mobile.data.FixtureTaskTitleEditPort
import kz.zani.mobile.data.FixtureTaskPriorityEditPort
import kz.zani.mobile.data.FixtureTaskDateEditPort
import kz.zani.mobile.data.FixtureTaskSelfAssignPort
import kz.zani.mobile.data.FixtureTaskCompletePort
import kz.zani.mobile.data.FixtureTaskCancelPort
import kz.zani.mobile.data.FixtureTaskCommentSubmitPort
import kz.zani.mobile.data.FixtureTaskCommentDraftSource
import kz.zani.mobile.ui.AttentionQueueViewModel
import kz.zani.mobile.ui.HomeTodayViewModel
import kz.zani.mobile.ui.LoadedSearchViewModel
import kz.zani.mobile.ui.NativeHomeScreen
import kz.zani.mobile.ui.ClientDirectoryViewModel
import kz.zani.mobile.ui.InboxViewModel
import kz.zani.mobile.ui.TaskListViewModel
import kz.zani.mobile.ui.NotificationCenterViewModel
import kz.zani.mobile.ui.ClientProfileViewModel
import kz.zani.mobile.ui.AgendaViewModel
import kz.zani.mobile.ui.AppointmentRelationsViewModel
import kz.zani.mobile.data.UiCopy
import java.util.Locale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val localized = UiCopy(assets.open("ui-copy.json").bufferedReader().use { it.readText() }, Locale.getDefault().toLanguageTag())
        val copy = localized.values
        setContent {
            val accent = Color(0xFFD96718)
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme(primary = accent) else lightColorScheme(primary = accent)) {
                if (BuildConfig.DEBUG) {
                    val factory = remember { object : ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : ViewModel> create(modelClass: Class<T>): T {
                            val repository = APIReadRepository(FixtureTransport(assets))
                            return when (modelClass) {
                                AttentionQueueViewModel::class.java -> AttentionQueueViewModel(repository)
                                HomeTodayViewModel::class.java -> HomeTodayViewModel(repository, currentDay = { "2026-10-28" })
                                AgendaViewModel::class.java -> AgendaViewModel(repository, initialDay = { "2026-10-28" }, relations = AppointmentRelationsViewModel(repository,APIAppointmentReferenceRepository(FixtureTransport(assets)),APIAppointmentSlotRepository(FixtureAppointmentSlotTransport(assets))),lifecyclePort=FixtureAppointmentTerminalPort(assets),lifecycleReferences=APIAppointmentReferenceRepository(FixtureTransport(assets)),bookingPort=FixtureAppointmentBookingPort(assets),bookingClients=repository,bookingReferences=APIAppointmentReferenceRepository(FixtureTransport(assets)),serviceRepository=APIServiceDirectoryRepository(FixtureServiceDirectoryTransport(assets)),resourceRepository=APIResourceDirectoryRepository(FixtureResourceDirectoryTransport(assets)),bookingServices=APIServiceDirectoryRepository(FixtureServiceDirectoryTransport(assets)),bookingResources=APIResourceDirectoryRepository(FixtureResourceDirectoryTransport(assets)),bookingClientSearch=repository)
                                ClientDirectoryViewModel::class.java -> ClientDirectoryViewModel(repository,createSubmission=FixtureClientCreatePort(assets),duplicateSource=FixtureClientDuplicatePreviewSource(assets))
                                ClientProfileViewModel::class.java -> ClientProfileViewModel(repository,editOriginSource=FixtureClientEditOriginProvider(assets),mergeSource=FixtureClientMergePreviewSource(assets))
                                InboxViewModel::class.java -> InboxViewModel(repository,FixtureQuickReplyRepository(assets),FixtureInboxReplyPort(assets),FixtureHandoffPort(assets),APIInboxConversationFilesRepository(FixtureInboxConversationFilesTransport(assets)),APIInboxMessageFilesRepository(FixtureInboxRetryReadTransport(assets)),FixtureInboxRetryPort(assets),APIInboxSelfAssignmentRepository(FixtureInboxSelfAssignmentReadTransport(assets)),FixtureInboxSelfAssignmentPort(assets),APIInboxReadMarkerRepository(FixtureInboxReadMarkerReadTransport(assets)),FixtureInboxReadMarkerPort(assets),APIInboxPriorityRepository(FixtureInboxPriorityReadTransport(assets)),FixtureInboxPriorityPort(assets),APIInboxLifecycleRepository(FixtureInboxLifecycleReadTransport(assets)),FixtureInboxLifecyclePort(assets),APIInboxLinkClientRepository(FixtureInboxLinkClientReadTransport(assets)),repository,FixtureInboxLinkClientPort(assets),APILeadReadRepository(FixtureLeadReadTransport(assets)),APIInboxLinkLeadRepository(FixtureInboxLinkLeadReadTransport(assets)),FixtureInboxLinkLeadPort(assets),APIDealReadRepository(FixtureDealReadTransport(assets)),APIInboxLinkDealRepository(FixtureInboxLinkDealReadTransport(assets)),FixtureInboxLinkDealPort(assets),APITeamMemberReadRepository(FixtureTeamMemberReadTransport(assets)),APIInboxTargetAssignmentRepository(FixtureInboxTargetAssignmentReadTransport(assets)),FixtureInboxTargetAssignmentPort(assets),APIInboxTaskSourceRepository(FixtureInboxTaskSourceTransport(assets)),FixtureInboxCreateTaskPort(assets),APIInboxExistingClientRepository(FixtureInboxExistingClientReadTransport(assets)),FixtureInboxExistingClientPort(assets),APIInboxExistingLeadRepository(FixtureInboxExistingLeadReadTransport(assets)),FixtureInboxExistingLeadPort(assets),APIInboxExistingDealRepository(FixtureInboxExistingDealReadTransport(assets)),FixtureInboxExistingDealPort(assets))
                                TaskListViewModel::class.java -> TaskListViewModel(APIReadRepository(FixtureTransport(assets,taskQueries=true)),commentSource=FixtureTaskCommentDraftSource(assets),commentSubmission=FixtureTaskCommentSubmitPort(assets),cancelSubmission=FixtureTaskCancelPort(assets),createSubmission=FixtureTaskCreatePort(assets),completeSubmission=FixtureTaskCompletePort(assets),selfAssignSubmission=FixtureTaskSelfAssignPort(assets),startSubmission=FixtureTaskStartPort(assets),reopenSubmission=FixtureTaskReopenPort(assets),fileMetadataPort=FixtureTaskFileMetadataPort(assets),watcherSubmission=FixtureTaskWatcherPort(assets),undoCancelSubmission=FixtureTaskUndoCancelPort(assets),snoozeSubmission=FixtureTaskSnoozePort(assets),targetAssignSubmission=FixtureTaskAssignPort(assets),dateEditSubmission=FixtureTaskDateEditPort(assets),priorityEditSubmission=FixtureTaskPriorityEditPort(assets),titleEditSubmission=FixtureTaskTitleEditPort(assets),descriptionEditSubmission=FixtureTaskDescriptionEditPort(assets),draftClients=APIReadRepository(FixtureTransport(assets)),draftAppointments=APIReadRepository(FixtureTransport(assets)),draftParents=APIReadRepository(FixtureTransport(assets)),appointmentEditSubmission=FixtureTaskAppointmentEditPort(assets),appointmentEditReads=APIReadRepository(FixtureTransport(assets)),clientEditSubmission=FixtureTaskClientEditPort(assets),clientEditReads=APIReadRepository(FixtureTransport(assets)))
                                LoadedSearchViewModel::class.java -> LoadedSearchViewModel(repository)
                                NotificationCenterViewModel::class.java -> NotificationCenterViewModel(repository,markReadSubmission=FixtureNotificationMarkReadPort(assets),markUnreadSubmission=FixtureNotificationMarkUnreadPort(assets))
                                else -> error("Unknown native ViewModel")
                            } as T
                        }
                    } }
                    val attention: AttentionQueueViewModel = viewModel(factory = factory)
                    val home: HomeTodayViewModel = viewModel(factory = factory)
                    val model: AgendaViewModel = viewModel(factory = factory)
                    val clients: ClientDirectoryViewModel = viewModel(factory = factory)
                    val profile: ClientProfileViewModel = viewModel(factory = factory)
                    val inbox: InboxViewModel = viewModel(factory = factory)
                    val tasks: TaskListViewModel = viewModel(factory = factory)
                    val notifications: NotificationCenterViewModel = viewModel(factory = factory)
                    val search: LoadedSearchViewModel = viewModel(factory = factory)
                    NativeHomeScreen(attention, home, model, clients, profile, inbox, tasks, notifications, search, copy, localized.language)
                } else {
                    // No live fallback until backend/session binding is explicitly configured.
                    Text(copy.getValue("configurationRequired"))
                }
            }
        }
    }
}
