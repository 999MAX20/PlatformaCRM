import SwiftUI
import CRMCore

struct ClientProfileScreen: View {
    @ObservedObject var model: ClientProfileViewModel
    let business: Business
    let id: Int
    let epoch: Int?
    init(model: ClientProfileViewModel,business: Business,id: Int,epoch: Int? = nil,isCurrent: @escaping @MainActor ()->Bool = {true},onContact: @escaping @MainActor (Int,ClientContact)->Void) {self.model=model;self.business=business;self.id=id;self.epoch=epoch;self.isCurrent=isCurrent;self.onContact=onContact}
    let onContact: @MainActor (Int, ClientContact) -> Void
    let isCurrent:@MainActor ()->Bool
    var body: some View {
        let expected=model.readSelection
        return ClientProfileContent(model: model, business: business, id: id, onRetry: { Task {if isCurrent() {await model.retry(expected:expected,epoch:epoch,onContact:onContact)}} },isCurrent:{isCurrent() && model.readSelection==expected})
            .task(id: "\(business.id)/\(id)/\(epoch ?? 0)") {
                guard isCurrent() else {return}
                if model.business != business.id || model.id != id || model.scopeEpoch != epoch || (model.detail == nil && !model.loading && model.failure == nil) { await model.load(business: business.id, id: id, epoch:epoch,onContact: onContact) }
            }
    }
}
