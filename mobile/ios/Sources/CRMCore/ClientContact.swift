import Foundation

// Consumer of the existing _client_item read projection, not a new server schema.
public struct ClientContact: Decodable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String?
    public let phone: String?
    public let email: String?
    // Existing full ClientSerializer fields only; a bounded title/160-notes item is not this shape.
    public let business:Int?;public let full_name:String?;public let source:String?;public let notes:String?;public let created_at:String?;public let updated_at:String?
    public init(id:Int,title:String?,phone:String?,email:String?,business:Int?=nil,full_name:String?=nil,source:String?=nil,notes:String?=nil,created_at:String?=nil,updated_at:String?=nil) {
        self.id=id;self.title=title;self.phone=phone;self.email=email;self.business=business;self.full_name=full_name;self.source=source;self.notes=notes;self.created_at=created_at;self.updated_at=updated_at
    }
    private enum CodingKeys:String,CodingKey {case id,title,phone,email,business,full_name,source,notes,created_at,updated_at}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(Int.self,forKey:.id);title=try c.decodeIfPresent(String.self,forKey:.title);phone=try c.decodeIfPresent(String.self,forKey:.phone);email=try c.decodeIfPresent(String.self,forKey:.email)
        if c.contains(.business),c.contains(.full_name) {
            business=try c.decodeIfPresent(Int.self,forKey:.business);full_name=try c.decodeIfPresent(String.self,forKey:.full_name);source=try c.decodeIfPresent(String.self,forKey:.source);notes=try c.decodeIfPresent(String.self,forKey:.notes);created_at=try c.decodeIfPresent(String.self,forKey:.created_at);updated_at=try c.decodeIfPresent(String.self,forKey:.updated_at)
        } else {business=nil;full_name=nil;source=nil;notes=nil;created_at=nil;updated_at=nil}
    }
}
public struct ClientList: Decodable, Sendable {
    public struct Summary: Decodable, Sendable { public let total: Int }
    public let business: Int
    public let items: [ClientContact]
    public let summary: Summary
}
