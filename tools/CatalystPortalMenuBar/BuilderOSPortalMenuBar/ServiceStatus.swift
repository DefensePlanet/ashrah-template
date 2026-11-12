import Foundation

enum ServiceState: String, Codable {
    case online
    case stopped
    case errored
    case restarting
    case starting

    var emoji: String {
        switch self {
        case .online: return "✅"
        case .stopped: return "⏸️"
        case .errored: return "❌"
        case .restarting: return "⚠️"
        case .starting: return "🔄"
        }
    }
}

struct ServiceStatus: Identifiable, Codable {
    let id: String
    let name: String
    let port: Int?
    let status: ServiceState
    let memory: Int64
    let uptime: TimeInterval
    let restarts: Int

    var memoryFormatted: String {
        let mb = Double(memory) / 1024.0 / 1024.0
        return String(format: "%.1f MB", mb)
    }

    var isCore: Bool {
        ["caddy", "agent-api", "bifrost-gateway"].contains(id)
    }

    var isDev: Bool {
        ["vite-portal", "plasmic-backend", "plasmic-frontend"].contains(id)
    }
}

struct PM2Process: Codable {
    let name: String
    let pm_id: Int?
    let pid: Int?
    let pm2_env: PM2Env?
    let monit: PM2Monit?

    struct PM2Env: Codable {
        let status: String
        let restart_time: Int?
        let unstable_restarts: Int?
        let pm_uptime: Int?
    }

    struct PM2Monit: Codable {
        let memory: Int64?
    }
}

struct IdleTimerStatus {
    let lastActivity: Date
    let idleMinutes: Double
    let totalMinutes: Double = 30.0

    var progress: Double {
        min(idleMinutes / totalMinutes, 1.0)
    }

    var isExpired: Bool {
        idleMinutes >= totalMinutes
    }

    var formattedTime: String {
        "\(Int(idleMinutes)) min / \(Int(totalMinutes)) min"
    }
}
