package kz.zani.mobile.core

// Source-defined schemas only; no credential access/storage, device generation or execution.
enum class MobileDevicePlatform(val wire:String) {IOS("ios"),ANDROID("android")}
class MobileAuthDeviceInput(val deviceID:String,val platform:MobileDevicePlatform,val appVersion:String?,val buildNumber:String?,val osVersion:String?,val deviceModel:String?) {
    override fun toString()="MobileAuthDeviceInput(redacted)"
}
class MobileLoginInput(val device:MobileAuthDeviceInput,val email:String,val password:String,val business:Int?) {
    override fun toString()="MobileLoginInput(redacted)"
}
class MobileRefreshInput(val refresh:String) {override fun toString()="MobileRefreshInput(redacted)"}
class MobileLogoutInput(val refresh:String?) {override fun toString()="MobileLogoutInput(redacted)"}
enum class MobileAuthContractProblem {INVALID_PAYLOAD,CONTEXT_MISMATCH}
class MobileAuthContractException(val problem:MobileAuthContractProblem):Exception(problem.name)
// Supplied descriptors, not grants/roles or an authorization decision API.
class MobilePermissionDescriptor(val resource:String,val action:String,val scope:String)
class MobileAuthBusiness(val id:Int,val name:String,val slug:String,val businessType:String,val city:String,val timezone:String,val language:String,val currency:String,val status:String,permissions:List<MobilePermissionDescriptor>) {
    private val provided=permissions.toList()
    val permissions:List<MobilePermissionDescriptor> get()=provided.toList()
}
class MobileAuthDeviceReply(val id:Int,val business:Int,val platform:MobileDevicePlatform,val appVersion:String,val buildNumber:String,val osVersion:String,val deviceModel:String,val lastSeenAt:String?,val revokedAt:String?,val createdAt:String,val updatedAt:String)
class MobileTokenReply(val access:String,val refresh:String,val tokenType:String) {override fun toString()="MobileTokenReply(redacted)"}
class MobileLoginReply(val tokens:MobileTokenReply,val business:MobileAuthBusiness,val device:MobileAuthDeviceReply) {override fun toString()="MobileLoginReply(redacted)"}
class MobileLogoutReply(val ok:Boolean)
