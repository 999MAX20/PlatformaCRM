import Foundation

// Exact existing apps/mobile/selectors._user_item projection. Display is not a grant.
public struct MobileUserItem: Decodable,Equatable,Sendable {
    public let id: Int;public let email: String;public let full_name: String
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.id==rhs.id && SourceTextIdentity.same(lhs.email,rhs.email) && SourceTextIdentity.same(lhs.full_name,rhs.full_name)}
    public var valid: Bool {id>0}
    public var displayName: String? {
        if !full_name.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {return full_name}
        return email.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty ? nil:email
    }
}
public enum MobileUserRead: Equatable,Sendable {
    case notSet,unknown,person(MobileUserItem)
    static func decode<Key: CodingKey>(_ container: KeyedDecodingContainer<Key>,forKey key: Key) -> MobileUserRead {
        guard container.contains(key) else {return .unknown}
        if (try? container.decodeNil(forKey:key))==true {return .notSet}
        guard let user=try? container.decode(MobileUserItem.self,forKey:key),user.valid else {return .unknown}
        return .person(user)
    }
}
