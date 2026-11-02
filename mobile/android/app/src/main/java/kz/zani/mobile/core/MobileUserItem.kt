package kz.zani.mobile.core

// Exact existing _user_item source projection. No membership/identity/UPDATE inference.
// Typed display identity keeps exact provided strings; id/valid/decoder/fallback and rights boundaries are unchanged.
data class MobileUserItem(val id: Int,val email: String,val fullName: String) {
    val valid get()=id>0
    val displayName get()=fullName.takeIf {it.isNotBlank()} ?: email.takeIf {it.isNotBlank()}
}
sealed interface MobileUserRead {
    data object NotSet: MobileUserRead
    data object Unknown: MobileUserRead
    data class Person(val user: MobileUserItem): MobileUserRead
}
