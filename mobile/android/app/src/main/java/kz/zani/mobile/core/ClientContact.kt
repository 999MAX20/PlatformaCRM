package kz.zani.mobile.core

// Consumer of the existing _client_item read projection, not a new server schema.
data class ClientContact(val id: Int, val title: String?, val phone: String?, val email: String?,val business:Int?=null,val fullName:String?=null,val source:String?=null,val notes:String?=null,val createdAt:String?=null,val updatedAt:String?=null)
data class ClientList(val business: Int, val items: List<ClientContact>, val total: Int)
