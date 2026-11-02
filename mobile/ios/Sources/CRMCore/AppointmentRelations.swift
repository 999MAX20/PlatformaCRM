import Foundation

public enum AppointmentRelatedTarget: Equatable, Sendable { case client(Int), task(Int), service(Int), resource(Int) }
public extension AppointmentDetail {
    var linkedClientID: Int? {
        guard let outer = appointment.client_id, let nested = details.client?.id, outer > 0, outer == nested else { return nil }
        return outer
    }
    var clientLinkAmbiguous: Bool { linkedClientID == nil && (appointment.client_id != nil || details.client?.id != nil) }
    var providedTasks: [WorkTask]? {
        guard let tasks = related?.tasks, let cap = payload_budget?.max_related_per_section, (1...5).contains(cap), tasks.count <= cap,
              tasks.allSatisfy(\.valid), Set(tasks.map(\.id)).count == tasks.count else { return nil }
        return tasks
    }
    var relatedTaskWindowCapped: Bool { guard let tasks = providedTasks else { return false }; return tasks.count == payload_budget?.max_related_per_section }
}

public extension AppointmentRelatedTarget {
    var referenceKind:AppointmentReferenceKind? {switch self {case .service:.service;case .resource:.resource;default:nil}}
}
