import Carbon
import Foundation

/// Registers only Command-Shift-S. No keyboard event stream or typed characters are observed.
public final class SnapshotHotKey {
    private var reference: EventHotKeyRef?
    private var handler: EventHandlerRef?
    private let action: () -> Void
    public init(action: @escaping () -> Void) { self.action = action }
    public func register() {
        unregister()
        var event = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        let pointer = Unmanaged.passUnretained(self).toOpaque()
        InstallEventHandler(GetApplicationEventTarget(), { _, _, context in
            guard let context else { return OSStatus(eventNotHandledErr) }
            Unmanaged<SnapshotHotKey>.fromOpaque(context).takeUnretainedValue().action()
            return noErr
        }, 1, &event, pointer, &handler)
        let id = EventHotKeyID(signature: 0x434C454E, id: 1)
        RegisterEventHotKey(UInt32(kVK_ANSI_S), UInt32(cmdKey | shiftKey), id, GetApplicationEventTarget(), 0, &reference)
    }
    public func unregister() {
        if let reference { UnregisterEventHotKey(reference) }; reference = nil
        if let handler { RemoveEventHandler(handler) }; handler = nil
    }
    deinit { unregister() }
}
