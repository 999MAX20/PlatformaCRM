import SwiftUI
import CRMCore

struct InboxClientRoute<Content: View>: View {
    @ObservedObject var links: InboxClientViewModel
    let business: Business
    let isCurrent:@MainActor ()->Bool
    let retry:@MainActor (InboxClientControl)->Void
    let content: Content
    init(links: InboxClientViewModel,business: Business,isCurrent:@escaping @MainActor ()->Bool,retry:@escaping @MainActor (InboxClientControl)->Void,@ViewBuilder content: () -> Content) { self.links = links; self.business = business;self.isCurrent=isCurrent;self.retry=retry; self.content = content() }
    var body:some View {InboxClientObservedContent(links:links) {routeContent}}
    private var routeContent:some View {
        let presentation=links.presentation,control=links.control,returnControl=links.returnControl
        let request = presentation?.request
        let readScope=AppCopy.text("inbox")+": "+AppCopy.text("senderClient")+": "+AppCopy.text("details")
        return content.navigationDestination(isPresented: Binding(get: {
            isCurrent() && control != nil && links.control == control && request?.business == business.id && links.selectedID != nil
        }, set: {if !$0,isCurrent() {_=links.close(expected:returnControl)}})) {
            if let control,isCurrent(),links.control == control, let id = links.selectedID {
                Group {
                    if links.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
                    else { ClientProfileContent(model: links.profile,business: business,id: id,onRetry:{if isCurrent() {retry(control)}},isCurrent:{isCurrent() && links.control==control}) }
                }.navigationTitle(AppCopy.text("senderClient"))
            }
        }
    }
}
struct InboxClientButton: View {
    @ObservedObject var links: InboxClientViewModel
    let open:(InboxClientEntryControl)->Void
    var body: some View {
        if let entry=links.entryControl {
            Button(AppCopy.text("openTarget") + " · " + AppCopy.text("senderClient")) {if links.entryControl==entry {open(entry)}}
        }
    }
}

// Refresh captured return snapshots when the independent profile or work view changes,
// including the transition back to the parent. These observers do not start reads.
struct InboxClientObservedContent<Content:View>:View {
    @ObservedObject var links:InboxClientViewModel
    @ObservedObject var profile:ClientProfileViewModel
    let content:()->Content
    init(links:InboxClientViewModel,@ViewBuilder content:@escaping ()->Content) {self.links=links;self.profile=links.profile;self.content=content}
    @ViewBuilder var body:some View {
        if let work=profile.work {InboxClientWorkObservedContent(work:work,content:content)} else {content()}
    }
}
private struct InboxClientWorkObservedContent<Content:View>:View {
    @ObservedObject var work:ClientWorkViewModel
    let content:()->Content
    var body:some View {let _=work.presentation;return content()}
}
