import SwiftUI
import AppKit
@preconcurrency import Combine

@MainActor
class MenuBarController: ObservableObject {
    private var statusItem: NSStatusItem!
    private var popover: NSPopover!
    private var pm2Manager: PM2Manager!
    private var cancellables = Set<AnyCancellable>()

    init() {
        pm2Manager = PM2Manager()
        setupStatusItem()
        setupPopover()
        setupObservers()
    }

    deinit {
        cancellables.forEach { $0.cancel() }
        cancellables.removeAll()
    }

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            updateStatusIcon(for: .unknown)
            button.action = #selector(togglePopover)
            button.target = self
        }
    }

    private func setupPopover() {
        popover = NSPopover()
        popover.contentSize = NSSize(width: 400, height: 600)
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(
            rootView: StatusBarView(pm2Manager: pm2Manager)
        )
    }

    private func setupObservers() {
        pm2Manager.$overallStatus
            .receive(on: DispatchQueue.main)
            .sink { [weak self] status in
                self?.updateStatusIcon(for: status)
            }
            .store(in: &cancellables)
    }

    @objc func togglePopover() {
        if let button = statusItem.button {
            if popover.isShown {
                popover.performClose(nil)
            } else {
                popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            }
        }
    }

    private func updateStatusIcon(for status: PM2Manager.OverallStatus) {
        guard let button = statusItem.button else { return }

        // Load icon directly from bundle to bypass asset catalog caching
        if let iconURL = Bundle.main.url(forResource: "StatusIcon-32", withExtension: "png", subdirectory: "Assets.xcassets/StatusIcon.imageset"),
           let image = NSImage(contentsOf: iconURL) {
            image.isTemplate = false
            image.size = NSSize(width: 18, height: 18)  // Slightly larger for visibility
            button.image = image
            button.contentTintColor = nil
        } else {
            // Fallback: try asset catalog method
            if let image = NSImage(named: "StatusIcon") {
                image.isTemplate = false
                button.image = image
                button.contentTintColor = nil
            }
        }
    }
}
