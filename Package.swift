// swift-tools-version: 5.10
import PackageDescription
let package = Package(
    name: "ContextLens", platforms: [.macOS(.v14)],
    products: [.executable(name: "ContextLens", targets: ["ContextLensApp"]),
               .executable(name: "contextlens-cli", targets: ["ContextLensCLI"])],
    targets: [
        .target(name: "ContextLensCore"),
        .target(name: "ContextLensImaging", dependencies: ["ContextLensCore"]),
        .target(name: "ContextLensCapture", dependencies: ["ContextLensCore", "ContextLensImaging"]),
        .executableTarget(name: "ContextLensApp", dependencies: ["ContextLensCore", "ContextLensImaging", "ContextLensCapture"]),
        .executableTarget(name: "ContextLensCLI", dependencies: ["ContextLensCore", "ContextLensImaging", "ContextLensCapture"]),
        .testTarget(name: "ContextLensCoreTests", dependencies: ["ContextLensCore"]),
        .testTarget(name: "ContextLensImagingTests", dependencies: ["ContextLensCore", "ContextLensImaging"]),
        .testTarget(name: "ContextLensCaptureTests", dependencies: ["ContextLensCore", "ContextLensImaging", "ContextLensCapture"])
    ])
