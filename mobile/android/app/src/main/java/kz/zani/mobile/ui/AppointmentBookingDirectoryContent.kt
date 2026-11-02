package kz.zani.mobile.ui

import androidx.compose.runtime.Composable

@Composable fun AppointmentBookingDirectoryContent(model:AppointmentBookingModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val expected=model.selectorControl
    when(model.selector) {
        AppointmentBookingDirectoryKind.SERVICE->model.serviceChoices?.let {child->ServiceDirectoryContent(child,copy,onClose={model.closeSelector(expected)},useChoiceLabel=text("bookingUseService"),useChoice={choice,control->if(isCurrent())model.useService(choice,control,expected)},isCurrent={isCurrent() && model.matchesSelector(expected)})}
        AppointmentBookingDirectoryKind.RESOURCE->model.resourceChoices?.let {child->ResourceDirectoryContent(child,copy,onClose={model.closeSelector(expected)},useChoiceLabel=text("bookingUseResource"),useChoice={choice,control->if(isCurrent())model.useResource(choice,control,expected)},isCurrent={isCurrent() && model.matchesSelector(expected)})}
        null->Unit
    }
}
