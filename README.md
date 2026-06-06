# Native macOS Clipboard Manager (Python)

A blazing fast, truly native macOS clipboard history manager built with Python and PyObjC. 
It provides a seamless "Windows+V" like experience, allowing you to quickly preview and paste text, images, and files without losing focus of your current application.

## ✨ Features

- ⚡️ **Native UI**: Uses `NSWindow`, `NSTableView`, and `NSVisualEffectView` for a gorgeous, native frosted-glass macOS aesthetic.
- 🚀 **Instant Pasting**: Uses native macOS CoreGraphics (`CGEvent`) to simulate keystrokes, ensuring pastes are instant and reliable.
- ⌨️ **Global Hotkey**: Press `Cmd+Shift+V` from anywhere to summon the history.
- 🖼️ **Rich Previews**: Supports Text, Images (PNG/TIFF), and File paths.
- 🔒 **Privacy First**: Fully local. Metadata is stored in a lightweight JSON file, and image blobs are saved cleanly to your disk.
- 🔋 **Optimized Storage**: Uses SHA-256 hashing to instantly deduplicate clipboard items without slowing down your system.

## 📋 Requirements

- macOS 10.13+
- Python 3.8+

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd py_clipboard_manager
pip3 install -r requirements.txt
```

### 2. Run the App

```bash
python3 clipboard_manager.py
```

### 3. Grant Accessibility Permissions (IMPORTANT)

For the global hotkey (`Cmd+Shift+V`) and native pasting mechanism (`CGEvent`) to work, macOS requires Accessibility permissions.

When you first run the app, macOS might prompt you. If it doesn't, or if the hotkey isn't working:
1. Open **System Settings** → **Privacy & Security** → **Accessibility**.
2. Click the `+` icon (or toggle the switch) to grant permission to your **Terminal** app (e.g., Terminal, iTerm2, or Python itself).
3. Restart the application.

## 📖 Usage

- **`Cmd+Shift+V`**: Show the clipboard history HUD. It will appear near your mouse cursor.
- **Up/Down Arrows**: Navigate your history.
- **Enter/Return**: Select the item and instantly paste it into your previously active window.
- **Escape**: Close the HUD without pasting.

The app runs quietly in the background. You will see a `📋` icon in your menu bar, where you can easily Quit the application.

## 🗂️ Architecture Details

The application has been completely redesigned to avoid the pitfalls of older Python clipboard managers:

- **No AppleScript**: We strictly use PyObjC Cocoa bindings, keeping the macOS main event loop fully responsive.
- **Smart Storage**: `~/Library/Application Support/ClipboardManager/history.json` only holds lightweight metadata. Large image blobs are stored efficiently as standalone `.png` files and automatically cleaned up when they fall out of your history limit.
- **Thread Safety**: `pynput` runs the keyboard listener in a background thread, safely dispatching UI invocations back to the main thread via `AppHelper.callAfter`.

---

**Made for macOS Power Users**

