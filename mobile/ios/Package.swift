// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "PlatformaCRMNative",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "CRMCore", targets: ["CRMCore"]), .executable(name: "CRMCoreChecks", targets: ["CRMCoreChecks"])],
    targets: [.target(name: "CRMCore"), .executableTarget(name: "CRMCoreChecks", dependencies: ["CRMCore"], path: "Checks")]
)
