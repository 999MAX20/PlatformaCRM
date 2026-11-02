import Foundation
import SwiftUI
import CRMCore

// Local owner/read/presentation identities; never wire versions or permissions.
struct HomeOwnerControl:Equatable {let business:Int;let day:String;let epoch:Int;let generation:Int}
enum HomeSection:Equatable {case home,today}
struct HomeSectionControl:Equatable {let owner:HomeOwnerControl;let section:HomeSection;let revision:Int;let presentation:Int}
struct HomeNavigationControl:Equatable {let owner:HomeOwnerControl;let generation:Int;let destination:HomeDestination?}

@MainActor final class HomeTodayViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var day: String?
    @Published private(set) var scopeEpoch:Int?
    @Published private var navigationRevision=0
    private var ownerRevision=0
    private var navigationPending=false
    @Published private(set) var home: HomeSummary?
    @Published private(set) var today: TodaySummary?
    @Published private(set) var homeLoading = false
    @Published private(set) var todayLoading = false
    @Published private(set) var homeFailure: ReadFailure?
    @Published private(set) var todayFailure: ReadFailure?
    @Published private(set) var destination: HomeDestination?
    private var homeRevision = 0
    private var todayRevision = 0
    private let repository: any HomeTodayRepository
    private let now: () -> Date
    init(repository: any HomeTodayRepository, now: @escaping () -> Date = Date.init) { self.repository = repository; self.now = now }
    func currentDay(timezone: String) -> String { Day.string(now(), timezone: timezone) }
    var owner:HomeOwnerControl? {guard let business,business>0,let day,Day.isValid(day),let scopeEpoch,scopeEpoch>0 else {return nil};return HomeOwnerControl(business:business,day:day,epoch:scopeEpoch,generation:ownerRevision)}
    var homeControl:HomeSectionControl? {owner.map {HomeSectionControl(owner:$0,section:.home,revision:homeRevision,presentation:navigationRevision)}}
    var todayControl:HomeSectionControl? {owner.map {HomeSectionControl(owner:$0,section:.today,revision:todayRevision,presentation:navigationRevision)}}
    var navigationControl:HomeNavigationControl? {owner.map {HomeNavigationControl(owner:$0,generation:navigationRevision,destination:destination)}}
    func matches(_ expected:HomeNavigationControl?)->Bool {expected != nil && navigationControl==expected}
    func start(business: Int, day: String,epoch:Int?=nil) async {
        if self.business == business && self.day == day && scopeEpoch==epoch { return }
        clear(); self.business = business; self.day = day;scopeEpoch=epoch
        guard business > 0, Day.isValid(day),(epoch == nil || epoch!>0) else { homeFailure = .invalidContext; todayFailure = .invalidContext; return }
        homeLoading=true;todayLoading=true
        async let h: Void = reloadHome()
        async let t: Void = reloadToday()
        _ = await (h, t)
    }
    func reloadHome() async {
        guard let business, business > 0 else { return }
        homeRevision += 1; let ticket = homeRevision; home = nil; homeFailure = nil; homeLoading = true
        do {
            let response = try await repository.home(business: business)
            guard ticket == homeRevision else { return }
            guard response.valid(for: business) else { throw ReadFailure.invalidPayload }
            home = response; homeLoading = false
        } catch {
            guard ticket == homeRevision else { return }; homeLoading = false
            if !(error is CancellationError) { homeFailure = error as? ReadFailure ?? .unavailable }
        }
    }
    func reloadToday() async {
        guard let business, business > 0, let day, Day.isValid(day) else { return }
        todayRevision += 1; let ticket = todayRevision; today = nil; todayFailure = nil; todayLoading = true
        do {
            let response = try await repository.today(business: business, day: day)
            guard ticket == todayRevision else { return }
            guard response.valid(for: business, day: day) else { throw ReadFailure.invalidPayload }
            today = response; todayLoading = false
        } catch {
            guard ticket == todayRevision else { return }; todayLoading = false
            if !(error is CancellationError) { todayFailure = error as? ReadFailure ?? .unavailable }
        }
    }
    func reloadHome(expected:HomeSectionControl?) async {guard let expected,homeControl==expected,!homeLoading,destination==nil else {return};await reloadHome()}
    func reloadToday(expected:HomeSectionControl?) async {guard let expected,todayControl==expected,!todayLoading,destination==nil else {return};await reloadToday()}
    func open(_ target:HomeDestination,expected:HomeNavigationControl?) {guard matches(expected),destination==nil else {return};open(target)}
    func open(_ target: HomeDestination) { guard let business, business > 0 else { return };navigationRevision += 1;destination = target;navigationPending=true }
    func takeNavigation(expected:HomeNavigationControl?)->HomeDestination? {guard matches(expected),navigationPending,let destination else {return nil};navigationPending=false;return destination}
    func back(expected:HomeNavigationControl?) {guard matches(expected) else {return};back()}
    func back() {navigationRevision += 1;destination = nil;navigationPending=false}
    func reconcileOwner(business next:Int?,epoch:Int) {if business != next || scopeEpoch != epoch {clear()}}
    func clear() {
        ownerRevision += 1;navigationRevision += 1;navigationPending=false;scopeEpoch=nil
        homeRevision += 1; todayRevision += 1; business = nil; day = nil; home = nil; today = nil
        homeLoading = false; todayLoading = false; homeFailure = nil; todayFailure = nil; destination = nil
    }
}
