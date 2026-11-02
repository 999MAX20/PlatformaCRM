import Foundation

/// UI labels only. API enums and merchant-entered values are never translated here.
public struct UICopy: Sendable {
    public let language: String
    private let dictionaries: [String: [String: String]]
    public init(data: Data, preferredLanguage: String) throws {
        let parsed: [String: [String: String]]
        do { parsed = try JSONDecoder().decode([String: [String: String]].self, from: data) }
        catch { throw ReadFailure.invalidPayload }
        guard let english = parsed["en"], !english.isEmpty else { throw ReadFailure.invalidPayload }
        let keys = Set(english.keys)
        guard ["en", "ru", "kk"].allSatisfy({ locale in
            guard let values = parsed[locale], Set(values.keys) == keys else { return false }
            return values.values.allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        }) else { throw ReadFailure.invalidPayload }
        dictionaries = parsed
        let primary = preferredLanguage.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "_", with: "-").split(separator: "-").first.map(String.init)?.lowercased() ?? "en"
        language = ["en", "ru", "kk"].contains(primary) ? primary : "en"
    }
    public func text(_ key: String) -> String { dictionaries[language]?[key] ?? key }
}
