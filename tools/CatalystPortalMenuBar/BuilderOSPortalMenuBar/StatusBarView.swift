import SwiftUI

struct StatusBarView: View {
    @ObservedObject var pm2Manager: PM2Manager

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Catalyst Portal")
                    .font(.headline)
                Spacer()
                Button(action: { NSApplication.shared.terminate(nil) }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Core Services Section
                    ServiceSectionView(
                        title: "Core Services",
                        services: pm2Manager.services.filter { $0.isCore },
                        pm2Manager: pm2Manager
                    )

                    Divider()

                    // Dev Services Section
                    DevServicesSectionView(
                        services: pm2Manager.services.filter { $0.isDev },
                        idleTimer: pm2Manager.idleTimer,
                        pm2Manager: pm2Manager
                    )

                    Divider()

                    // Actions Section
                    ActionsSectionView(pm2Manager: pm2Manager)
                }
                .padding()
            }
        }
        .frame(width: 400, height: 600)
    }
}

struct ServiceSectionView: View {
    let title: String
    let services: [ServiceStatus]
    @ObservedObject var pm2Manager: PM2Manager

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            ForEach(services) { service in
                ServiceRowView(service: service, pm2Manager: pm2Manager)
            }
        }
    }
}

struct ServiceRowView: View {
    let service: ServiceStatus
    @ObservedObject var pm2Manager: PM2Manager
    @State private var showingMenu = false

    var isLoading: Bool {
        pm2Manager.loadingServices.contains(service.id)
    }

    var operationText: String? {
        pm2Manager.operationStatus[service.id]
    }

    var body: some View {
        HStack {
            // Show spinner if loading, otherwise status emoji
            if isLoading {
                ProgressView()
                    .scaleEffect(0.7)
                    .frame(width: 14, height: 14)
            } else {
                Text(service.status.emoji)
                    .font(.system(size: 14))
            }

            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(service.name)
                        .font(.system(size: 13))
                    if let port = service.port {
                        Text("(\(port))")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }
                }

                // Show operation status if loading, otherwise normal status
                if let opStatus = operationText {
                    Text(opStatus)
                        .font(.system(size: 11))
                        .foregroundColor(.blue)
                } else if service.status == .stopped {
                    Text("Stopped")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                } else if service.restarts > 5 {
                    Text("restarting...")
                        .font(.system(size: 11))
                        .foregroundColor(.orange)
                }
            }

            Spacer()

            if service.status != .stopped && !isLoading {
                Text(service.memoryFormatted)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Menu {
                if service.status == .stopped {
                    Button("Start") {
                        pm2Manager.startService(service.id)
                    }
                    .disabled(isLoading)
                } else {
                    Button("Restart") {
                        pm2Manager.restartService(service.id)
                    }
                    .disabled(isLoading)
                    Button("Stop") {
                        pm2Manager.stopService(service.id)
                    }
                    .disabled(isLoading)
                }
                Divider()
                Button("View Logs") {
                    pm2Manager.viewLogs(for: service.id)
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .foregroundColor(isLoading ? .gray : .secondary)
            }
            .menuStyle(.borderlessButton)
            .frame(width: 20)
            .disabled(isLoading)
        }
        .padding(.vertical, 4)
        .padding(.horizontal, 8)
        .background(Color.primary.opacity(isLoading ? 0.08 : 0.05))
        .cornerRadius(6)
        .opacity(isLoading ? 0.8 : 1.0)
    }
}

struct DevServicesSectionView: View {
    let services: [ServiceStatus]
    let idleTimer: IdleTimerStatus?
    @ObservedObject var pm2Manager: PM2Manager

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Dev Services (On-Demand)")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            ForEach(services) { service in
                ServiceRowView(service: service, pm2Manager: pm2Manager)
            }

            if let timer = idleTimer {
                IdleTimerView(timer: timer)
                    .padding(.top, 4)
            }

            // Show operation status for dev services
            if pm2Manager.devServicesOperating {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text(pm2Manager.devOperationStatus)
                        .font(.system(size: 11))
                        .foregroundColor(.blue)
                }
                .padding(.vertical, 4)
            }

            HStack(spacing: 8) {
                Button(action: { pm2Manager.startDevServices() }) {
                    Label("Start Dev Services", systemImage: "play.fill")
                        .font(.system(size: 12))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .disabled(pm2Manager.devServicesOperating)

                Button(action: { pm2Manager.stopDevServices() }) {
                    Label("Stop Dev Services", systemImage: "stop.fill")
                        .font(.system(size: 12))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(pm2Manager.devServicesOperating)
            }
        }
    }
}

struct ActionsSectionView: View {
    @ObservedObject var pm2Manager: PM2Manager

    var body: some View {
        VStack(spacing: 8) {
            Button(action: { pm2Manager.viewAllLogs() }) {
                Label("View All Logs", systemImage: "doc.text")
                    .font(.system(size: 13))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button(action: { pm2Manager.openPortal() }) {
                Label("Open Portal", systemImage: "safari")
                    .font(.system(size: 13))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button(action: { pm2Manager.openPM2Monitor() }) {
                Label("PM2 Monitor", systemImage: "chart.bar")
                    .font(.system(size: 13))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Divider()
                .padding(.vertical, 4)

            Button(action: { NSApplication.shared.terminate(nil) }) {
                Label("Quit App", systemImage: "power")
                    .font(.system(size: 13))
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(.red)
        }
    }
}
