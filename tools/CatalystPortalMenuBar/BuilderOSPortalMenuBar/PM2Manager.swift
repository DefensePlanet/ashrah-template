import Foundation
@preconcurrency import Combine
import AppKit

@MainActor
class PM2Manager: ObservableObject {
    @Published var services: [ServiceStatus] = []
    @Published var idleTimer: IdleTimerStatus?
    @Published var overallStatus: OverallStatus = .unknown
    @Published var errorMessage: String?
    @Published var loadingServices: Set<String> = []
    @Published var operationStatus: [String: String] = [:]
    @Published var devServicesOperating: Bool = false
    @Published var devOperationStatus: String = ""

    private let pm2Path = "{{HOME_DIR}}/.npm-global/bin/pm2"
    private let nodePath = "/opt/homebrew/bin/node"
    private let builderosPath = "{{CATALYST_ROOT}}/tools/builderos"
    private let idleTimerPath = "/tmp/builderos/dev-services-last-activity"

    private var cancellables = Set<AnyCancellable>()
    private let validServiceIds: Set<String> = [
        "caddy", "agent-api", "bifrost-gateway",
        "vite-portal", "plasmic-backend", "plasmic-frontend"
    ]

    enum OverallStatus {
        case allGood, someDown, allDown, unknown

        var iconName: String {
            switch self {
            case .allGood: return "status-green"
            case .someDown: return "status-yellow"
            case .allDown: return "status-red"
            case .unknown: return "status-yellow"
            }
        }
    }

    init() {
        validateRequiredPaths()
        startPolling()
    }

    deinit {
        cancellables.forEach { $0.cancel() }
        cancellables.removeAll()
    }

    private func validateRequiredPaths() {
        let fileManager = FileManager.default
        var missingPaths: [String] = []

        if !fileManager.fileExists(atPath: pm2Path) {
            missingPaths.append("PM2: \(pm2Path)")
        }
        if !fileManager.fileExists(atPath: builderosPath) {
            missingPaths.append("Catalyst: \(builderosPath)")
        }

        if !missingPaths.isEmpty {
            errorMessage = "Missing required binaries:\n\(missingPaths.joined(separator: "\n"))"
            print("⚠️ Validation failed: \(errorMessage ?? "")")
        }
    }

    func startPolling() {
        // Initial update
        updateStatus()

        // Poll every 5 seconds
        Timer.publish(every: 5, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.updateStatus()
            }
            .store(in: &cancellables)
    }

    func updateStatus() {
        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.fetchPM2Status()
            await self.updateIdleTimer()
            await self.updateOverallStatus()
        }
    }

    private func fetchPM2Status() async {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pm2Path)
        process.arguments = ["jlist"]

        // Set PATH to include Homebrew node
        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = environment

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()

        do {
            try process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let pm2Processes = try? JSONDecoder().decode([PM2Process].self, from: data) {
                await parseServices(from: pm2Processes)
            }
        } catch {
            let errorMsg = "Failed to fetch PM2 status: \(error.localizedDescription)"
            print(errorMsg)
            await MainActor.run {
                self.errorMessage = errorMsg
            }
        }
    }

    private func parseServices(from processes: [PM2Process]) async {
        var newServices: [ServiceStatus] = []

        let serviceMap: [String: (name: String, port: Int?)] = [
            "caddy": ("Caddy Portal", 443),
            "agent-api": ("Agent API", 8080),
            "bifrost-gateway": ("Bifrost Gateway", 8083),
            "vite-portal": ("Vite Portal", 5174),
            "plasmic-backend": ("Plasmic Backend", 3004),
            "plasmic-frontend": ("Plasmic Frontend", 3003)
        ]

        for (pmId, config) in serviceMap {
            if let process = processes.first(where: { $0.name == pmId }) {
                let status = mapPM2Status(process)
                let memory = process.monit?.memory ?? 0
                let uptime = Double(process.pm2_env?.pm_uptime ?? 0)
                let restarts = process.pm2_env?.restart_time ?? 0

                let service = ServiceStatus(
                    id: pmId,
                    name: config.name,
                    port: config.port,
                    status: status,
                    memory: memory,
                    uptime: uptime,
                    restarts: restarts
                )
                newServices.append(service)
            } else {
                // Service not found in PM2
                let service = ServiceStatus(
                    id: pmId,
                    name: config.name,
                    port: config.port,
                    status: .stopped,
                    memory: 0,
                    uptime: 0,
                    restarts: 0
                )
                newServices.append(service)
            }
        }

        await MainActor.run {
            self.services = newServices
        }
    }

    private func mapPM2Status(_ process: PM2Process) -> ServiceState {
        let status = process.pm2_env?.status ?? "stopped"
        let restarts = process.pm2_env?.unstable_restarts ?? 0

        switch status.lowercased() {
        case "online":
            return restarts > 5 ? .restarting : .online
        case "stopped":
            return .stopped
        case "errored":
            return .errored
        case "launching", "starting":
            return .starting
        default:
            return .stopped
        }
    }

    private func updateIdleTimer() async {
        guard FileManager.default.fileExists(atPath: idleTimerPath) else {
            await MainActor.run {
                self.idleTimer = nil
            }
            return
        }

        do {
            let content = try String(contentsOfFile: idleTimerPath, encoding: .utf8)
            if let timestamp = TimeInterval(content.trimmingCharacters(in: .whitespacesAndNewlines)) {
                let lastActivity = Date(timeIntervalSince1970: timestamp)
                let idleSeconds = Date().timeIntervalSince(lastActivity)
                let idleMinutes = idleSeconds / 60.0

                await MainActor.run {
                    self.idleTimer = IdleTimerStatus(
                        lastActivity: lastActivity,
                        idleMinutes: idleMinutes
                    )
                }
            }
        } catch {
            print("Failed to read idle timer: \(error)")
        }
    }

    private func updateOverallStatus() async {
        await MainActor.run {
            let coreServices = self.services.filter { $0.isCore }
            let runningCore = coreServices.filter { $0.status == .online }.count

            if coreServices.isEmpty {
                self.overallStatus = .unknown
            } else if runningCore == coreServices.count {
                self.overallStatus = .allGood
            } else if runningCore > 0 {
                self.overallStatus = .someDown
            } else {
                self.overallStatus = .allDown
            }
        }
    }

    // MARK: - Actions

    func startDevServices() {
        Task { @MainActor in
            self.devServicesOperating = true
            self.devOperationStatus = "Starting dev services..."
        }

        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.executeCommand(self.builderosPath, arguments: ["start-dev"])
            await self.pollUntilStateChange(timeout: 10.0)

            await MainActor.run {
                self.devServicesOperating = false
                self.devOperationStatus = ""
            }
        }
    }

    func stopDevServices() {
        Task { @MainActor in
            self.devServicesOperating = true
            self.devOperationStatus = "Stopping dev services..."
        }

        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.executeCommand(self.builderosPath, arguments: ["stop-dev"])
            await self.pollUntilStateChange(timeout: 10.0)

            await MainActor.run {
                self.devServicesOperating = false
                self.devOperationStatus = ""
            }
        }
    }

    func restartService(_ serviceId: String) {
        guard validServiceIds.contains(serviceId) else {
            print("⚠️ Invalid service ID: \(serviceId)")
            Task { @MainActor in
                self.errorMessage = "Invalid service ID: \(serviceId)"
            }
            return
        }

        Task { @MainActor in
            self.loadingServices.insert(serviceId)
            self.operationStatus[serviceId] = "Restarting..."
        }

        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.executeCommand(self.pm2Path, arguments: ["restart", serviceId])
            await self.pollUntilStateChange(timeout: 10.0)

            await MainActor.run {
                self.loadingServices.remove(serviceId)
                self.operationStatus.removeValue(forKey: serviceId)
            }
        }
    }

    func startService(_ serviceId: String) {
        guard validServiceIds.contains(serviceId) else {
            print("⚠️ Invalid service ID: \(serviceId)")
            Task { @MainActor in
                self.errorMessage = "Invalid service ID: \(serviceId)"
            }
            return
        }

        Task { @MainActor in
            self.loadingServices.insert(serviceId)
            self.operationStatus[serviceId] = "Starting..."
        }

        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.executeCommand(self.pm2Path, arguments: ["start", serviceId])
            await self.pollUntilStateChange(timeout: 10.0)

            await MainActor.run {
                self.loadingServices.remove(serviceId)
                self.operationStatus.removeValue(forKey: serviceId)
            }
        }
    }

    func stopService(_ serviceId: String) {
        guard validServiceIds.contains(serviceId) else {
            print("⚠️ Invalid service ID: \(serviceId)")
            Task { @MainActor in
                self.errorMessage = "Invalid service ID: \(serviceId)"
            }
            return
        }

        Task { @MainActor in
            self.loadingServices.insert(serviceId)
            self.operationStatus[serviceId] = "Stopping..."
        }

        Task.detached { [weak self] in
            guard let self = self else { return }
            await self.executeCommand(self.pm2Path, arguments: ["stop", serviceId])
            await self.pollUntilStateChange(timeout: 10.0)

            await MainActor.run {
                self.loadingServices.remove(serviceId)
                self.operationStatus.removeValue(forKey: serviceId)
            }
        }
    }

    private func pollUntilStateChange(timeout: TimeInterval) async {
        let startTime = Date()
        while Date().timeIntervalSince(startTime) < timeout {
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
            await self.fetchPM2Status()
            await self.updateIdleTimer()
            await self.updateOverallStatus()
        }
    }

    func viewLogs(for serviceId: String) {
        guard validServiceIds.contains(serviceId) else {
            print("⚠️ Invalid service ID: \(serviceId)")
            Task { @MainActor in
                self.errorMessage = "Invalid service ID: \(serviceId)"
            }
            return
        }

        let script = """
        tell application "Terminal"
            activate
            do script "\(pm2Path) logs \(serviceId)"
        end tell
        """

        if let appleScript = NSAppleScript(source: script) {
            var error: NSDictionary?
            appleScript.executeAndReturnError(&error)
            if let error = error {
                let errorMsg = "AppleScript error: \(error)"
                print(errorMsg)
                Task { @MainActor in
                    self.errorMessage = errorMsg
                }
            }
        }
    }

    func openPM2Monitor() {
        let script = """
        tell application "Terminal"
            activate
            do script "\(pm2Path) monit"
        end tell
        """

        if let appleScript = NSAppleScript(source: script) {
            var error: NSDictionary?
            appleScript.executeAndReturnError(&error)
            if let error = error {
                let errorMsg = "AppleScript error: \(error)"
                print(errorMsg)
                Task { @MainActor in
                    self.errorMessage = errorMsg
                }
            }
        }
    }

    func openPortal() {
        if let url = URL(string: "https://bldr.portal.localhost") {
            NSWorkspace.shared.open(url)
        }
    }

    func viewAllLogs() {
        let script = """
        tell application "Terminal"
            activate
            do script "\(pm2Path) logs"
        end tell
        """

        if let appleScript = NSAppleScript(source: script) {
            var error: NSDictionary?
            appleScript.executeAndReturnError(&error)
            if let error = error {
                let errorMsg = "AppleScript error: \(error)"
                print(errorMsg)
                Task { @MainActor in
                    self.errorMessage = errorMsg
                }
            }
        }
    }

    private func executeCommand(_ path: String, arguments: [String]) async {
        let process = Process()

        // Execute PM2 scripts via explicit node path (GUI apps don't have full shell PATH)
        if path.contains("pm2") {
            process.executableURL = URL(fileURLWithPath: nodePath)
            process.arguments = [path] + arguments  // [pm2Path, "restart", "service-id"]
        } else {
            // For non-PM2 commands (like builderos script)
            process.executableURL = URL(fileURLWithPath: path)
            process.arguments = arguments
        }

        // Set PATH to include Homebrew node
        var environment = ProcessInfo.processInfo.environment
        environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        process.environment = environment

        // Capture output for debugging
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        do {
            print("🔧 Executing: \(path) \(arguments.joined(separator: " "))")
            try process.run()
            process.waitUntilExit()  // Wait for command to complete

            // Read output
            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: outputData, encoding: .utf8) ?? ""
            let errorOutput = String(data: errorData, encoding: .utf8) ?? ""

            // Check exit status
            if process.terminationStatus != 0 {
                let errorMsg = "Command failed with exit code \(process.terminationStatus): \(errorOutput)"
                print("❌ \(errorMsg)")
                await MainActor.run {
                    self.errorMessage = errorMsg
                }
            } else {
                print("✅ Command succeeded: \(output)")
            }
        } catch {
            let errorMsg = "Failed to execute command: \(error.localizedDescription)"
            print(errorMsg)
            await MainActor.run {
                self.errorMessage = errorMsg
            }
        }
    }
}
