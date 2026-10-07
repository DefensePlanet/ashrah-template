import SwiftUI

struct IdleTimerView: View {
    let timer: IdleTimerStatus

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: "clock")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                Text("Idle: \(timer.formattedTime)")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                Spacer()
                if timer.isExpired {
                    Text("EXPIRED")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.red)
                }
            }

            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    // Background
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.secondary.opacity(0.2))
                        .frame(height: 6)

                    // Progress
                    RoundedRectangle(cornerRadius: 4)
                        .fill(progressColor)
                        .frame(width: geometry.size.width * timer.progress, height: 6)
                }
            }
            .frame(height: 6)
        }
        .padding(.vertical, 4)
        .padding(.horizontal, 8)
        .background(Color.primary.opacity(0.05))
        .cornerRadius(6)
    }

    private var progressColor: Color {
        if timer.progress < 0.5 {
            return .green
        } else if timer.progress < 0.8 {
            return .yellow
        } else {
            return .red
        }
    }
}
