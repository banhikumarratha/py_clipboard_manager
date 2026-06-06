#!/usr/bin/env python3
"""
macOS Clipboard Manager - Native PyObjC Implementation
A fast, native clipboard history manager with a "Windows+V" like experience.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from threading import Lock
from dataclasses import dataclass, asdict
from typing import List, Optional

import objc
from PyObjCTools import AppHelper
from AppKit import (
    NSApplication, NSApp, NSStatusBar, NSMenu, NSMenuItem, NSWorkspace,
    NSPasteboard, NSPasteboardTypeString, NSPasteboardTypePNG, NSPasteboardTypeTIFF, NSPasteboardTypeFileURL,
    NSWindow, NSWindowStyleMaskNonactivatingPanel, NSWindowStyleMaskBorderless, NSBackingStoreBuffered,
    NSVisualEffectView, NSVisualEffectMaterialHUDWindow, NSVisualEffectBlendingModeBehindWindow, NSVisualEffectStateActive,
    NSTableView, NSScrollView, NSTableColumn, NSTextField,
    NSColor, NSFont, NSMakeRect,
    NSEvent, NSNotificationCenter, NSWindowDidResignKeyNotification
)
from Foundation import (
    NSObject, NSTimer, NSURL, NSData, NSIndexSet
)
import Quartz
from pynput import keyboard

MAX_HISTORY = 20
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "ClipboardManager"
HISTORY_FILE = APP_SUPPORT_DIR / "history.json"
IMAGES_DIR = APP_SUPPORT_DIR / "images"

CHECK_INTERVAL = 0.5


@dataclass
class ClipboardItem:
    id: str
    timestamp: float
    content_type: str  # 'text', 'image', 'file'
    content: str
    content_hash: str

    def preview_text(self, max_length=60):
        if self.content_type == 'text':
            # Remove newlines for single-line preview
            text = self.content.replace('\n', ' ')
            return text[:max_length] + ('...' if len(text) > max_length else '')
        elif self.content_type == 'image':
            return '🖼️ [Image]'
        elif self.content_type == 'file':
            return f"📄 [File: {Path(self.content).name}]"
        return '❓ [Unknown]'

    def relative_time(self) -> str:
        elapsed = time.time() - self.timestamp
        if elapsed < 60: return 'Just now'
        elif elapsed < 3600: return f'{int(elapsed / 60)}m ago'
        elif elapsed < 86400: return f'{int(elapsed / 3600)}h ago'
        else: return f'{int(elapsed / 86400)}d ago'


class HistoryStorage:
    """Manages clipboard metadata via JSON and image blobs as separate files."""
    def __init__(self, max_items=MAX_HISTORY):
        self.max_items = max_items
        self.lock = Lock()
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.items: List[ClipboardItem] = self.load_history()

    def load_history(self) -> List[ClipboardItem]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return [ClipboardItem(**item) for item in data.get('items', [])]
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def save_history(self):
        try:
            data = {'version': '2.0', 'items': [asdict(item) for item in self.items]}
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_item(self, item: ClipboardItem):
        with self.lock:
            # Check for duplicate
            for existing in self.items:
                if existing.content_hash == item.content_hash:
                    # Move to front
                    self.items.remove(existing)
                    existing.timestamp = time.time()
                    self.items.insert(0, existing)
                    self.save_history()
                    return

            self.items.insert(0, item)
            
            # Truncate and clean up old images
            while len(self.items) > self.max_items:
                removed = self.items.pop()
                if removed.content_type == 'image':
                    try:
                        os.remove(removed.content)
                    except OSError:
                        pass
            
            self.save_history()

    def get_items(self) -> List[ClipboardItem]:
        with self.lock:
            return list(self.items)


class ClipboardMonitor(NSObject):
    """Polls NSPasteboard safely from the main thread."""
    def init(self):
        self = objc.super(ClipboardMonitor, self).init()
        if self is None: return None
        self.pasteboard = NSPasteboard.generalPasteboard()
        self.last_change_count = self.pasteboard.changeCount()
        self.storage = None
        self.on_change = None
        self.is_self_copy = False
        return self

    def start_monitoring(self, storage):
        self.storage = storage
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            CHECK_INTERVAL, self, 'checkClipboard:', None, True
        )

    def checkClipboard_(self, timer):
        current_count = self.pasteboard.changeCount()
        if current_count != self.last_change_count:
            self.last_change_count = current_count
            
            if self.is_self_copy:
                self.is_self_copy = False
                return
                
            item = self.extract_content()
            if item:
                self.storage.add_item(item)
                if hasattr(self, 'on_change') and self.on_change:
                    self.on_change()

    def extract_content(self) -> Optional[ClipboardItem]:
        types = self.pasteboard.types()
        if not types: return None
        
        # 1. Image
        if NSPasteboardTypePNG in types or NSPasteboardTypeTIFF in types:
            img_type = NSPasteboardTypePNG if NSPasteboardTypePNG in types else NSPasteboardTypeTIFF
            data = self.pasteboard.dataForType_(img_type)
            if data:
                bytes_data = bytes(data)
                content_hash = hashlib.sha256(bytes_data).hexdigest()
                file_path = IMAGES_DIR / f"{content_hash}.png"
                if not file_path.exists():
                    data.writeToFile_atomically_(str(file_path), True)
                return ClipboardItem(
                    id=f"img_{int(time.time()*1000)}",
                    timestamp=time.time(),
                    content_type='image',
                    content=str(file_path),
                    content_hash=content_hash
                )
                
        # 2. File URL
        if NSPasteboardTypeFileURL in types:
            url_str = self.pasteboard.stringForType_(NSPasteboardTypeFileURL)
            if url_str:
                url = NSURL.URLWithString_(url_str)
                path = url.path()
                return ClipboardItem(
                    id=f"file_{int(time.time()*1000)}",
                    timestamp=time.time(),
                    content_type='file',
                    content=path,
                    content_hash=hashlib.sha256(path.encode()).hexdigest()
                )

        # 3. Text
        if NSPasteboardTypeString in types:
            text = self.pasteboard.stringForType_(NSPasteboardTypeString)
            if text and text.strip():
                return ClipboardItem(
                    id=f"txt_{int(time.time()*1000)}",
                    timestamp=time.time(),
                    content_type='text',
                    content=text,
                    content_hash=hashlib.sha256(text.encode()).hexdigest()
                )
                
        return None


class FocusableWindow(NSWindow):
    def canBecomeKeyWindow(self):
        return True
    
    def canBecomeMainWindow(self):
        return True


class UIWindowController(NSObject):
    """Handles the native macOS UI (NSWindow, NSTableView)."""
    def init(self):
        self = objc.super(UIWindowController, self).init()
        if self is None: return None
        
        # Window setup
        rect = NSMakeRect(0, 0, 450, 400)
        self.window = FocusableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskNonactivatingPanel | NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )
        self.window.center()
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        # Float above everything
        self.window.setLevel_(Quartz.kCGPopUpMenuWindowLevel)
        self.window.setHasShadow_(True)
        
        # Frosted glass background
        self.visual_effect = NSVisualEffectView.alloc().initWithFrame_(rect)
        self.visual_effect.setMaterial_(NSVisualEffectMaterialHUDWindow)
        self.visual_effect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        self.visual_effect.setState_(NSVisualEffectStateActive)
        self.window.setContentView_(self.visual_effect)
        
        # Scroll View
        self.scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 10, 430, 380))
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setDrawsBackground_(False)
        self.visual_effect.addSubview_(self.scroll_view)
        
        # Table View
        self.table_view = NSTableView.alloc().initWithFrame_(self.scroll_view.bounds())
        col = NSTableColumn.alloc().initWithIdentifier_("MainCol")
        col.setWidth_(410)
        self.table_view.addTableColumn_(col)
        self.table_view.setHeaderView_(None)
        self.table_view.setBackgroundColor_(NSColor.clearColor())
        
        self.scroll_view.setDocumentView_(self.table_view)
        
        self.items = []
        self.monitor = None
        self.table_view.setDataSource_(self)
        self.table_view.setDelegate_(self)
        self.table_view.setTarget_(self)
        self.table_view.setAction_("clickedAction:")
        
        # Hide when focus is lost
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "windowLostFocus:", NSWindowDidResignKeyNotification, self.window
        )
        
        # Local event monitor for Escape/Enter
        NSEventMaskKeyDown = 1 << 10
        self.event_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, self.handle_key_event
        )
        
        return self

    def windowLostFocus_(self, notification):
        self.hide()

    def handle_key_event(self, event):
        if not self.window.isVisible():
            return event
            
        keycode = event.keyCode()
        
        if keycode == 53: # Escape
            self.hide()
            return None
        elif keycode == 36: # Return
            self.select_current()
            return None
        
        return event
        
    def numberOfRowsInTableView_(self, tv):
        return len(self.items)
        
    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        return None
        
    def tableView_viewForTableColumn_row_(self, tv, col, row):
        item = self.items[row]
        text_id = "CellID"
        view = tv.makeViewWithIdentifier_owner_(text_id, self)
        if not view:
            view = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 50))
            view.setIdentifier_(text_id)
            view.setEditable_(False)
            view.setSelectable_(False)
            view.setBezeled_(False)
            view.setDrawsBackground_(False)
            view.setFont_(NSFont.systemFontOfSize_(14))
            view.setTextColor_(NSColor.labelColor())
            
        view.setStringValue_(f"{item.preview_text(60)}\n{item.relative_time()}")
        return view

    def tableView_heightOfRow_(self, tv, row):
        return 60.0

    def clickedAction_(self, sender):
        row = self.table_view.clickedRow()
        if row >= 0 and row < len(self.items):
            item = self.items[row]
            self.hide()
            self.perform_paste(item)
        else:
            self.select_current()

    def select_current(self):
        row = self.table_view.selectedRow()
        if row >= 0 and row < len(self.items):
            item = self.items[row]
            self.hide()
            self.perform_paste(item)

    def perform_paste(self, item):
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        
        # Flag to prevent monitor from recording our own paste
        if self.monitor:
            self.monitor.is_self_copy = True
            
        if item.content_type == 'text':
            pb.declareTypes_owner_([NSPasteboardTypeString], None)
            pb.setString_forType_(item.content, NSPasteboardTypeString)
        elif item.content_type == 'file':
            url = NSURL.fileURLWithPath_(item.content)
            pb.declareTypes_owner_([NSPasteboardTypeFileURL], None)
            pb.writeObjects_([url])
        elif item.content_type == 'image':
            data = NSData.dataWithContentsOfFile_(item.content)
            if data:
                pb.declareTypes_owner_([NSPasteboardTypePNG], None)
                pb.setData_forType_(data, NSPasteboardTypePNG)
                
        # Update change count state to prevent picking it up immediately
        if self.monitor:
            self.monitor.last_change_count = pb.changeCount()

        # Simulate Cmd+V using CGEvent
        # Slight delay to ensure focus returns to original app after window closes
        import threading
        def _paste_delayed():
            time.sleep(0.5)
            from pynput.keyboard import Controller, Key
            kbd = Controller()
            with kbd.pressed(Key.cmd):
                kbd.press('v')
                kbd.release('v')
            
        threading.Thread(target=_paste_delayed).start()

    def show_items(self, items):
        self.previous_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        self.items = items
        self.table_view.reloadData()
        if len(self.items) > 0:
            self.table_view.selectRowIndexes_byExtendingSelection_(NSIndexSet.indexSetWithIndex_(0), False)
        
        # Position window near mouse cursor
        mouse_loc = NSEvent.mouseLocation()
        frame = self.window.frame()
        new_origin = NSMakeRect(mouse_loc.x - frame.size.width/2, mouse_loc.y - frame.size.height/2, frame.size.width, frame.size.height).origin
        self.window.setFrameOrigin_(new_origin)

        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    def hide(self):
        self.window.orderOut_(None)
        NSApp.hide_(None)
        if hasattr(self, 'previous_app') and self.previous_app:
            self.previous_app.activateWithOptions_(0)


class AppController(NSObject):
    """Main App Delegate linking all components."""
    def applicationDidFinishLaunching_(self, notification):
        self.storage = HistoryStorage()
        
        self.ui = UIWindowController.alloc().init()
        
        self.monitor = ClipboardMonitor.alloc().init()
        self.monitor.start_monitoring(self.storage)
        self.monitor.on_change = self.refresh_ui_if_visible
        
        self.ui.monitor = self.monitor
        
        self.setup_menu()
        self.setup_hotkey()

    def refresh_ui_if_visible(self):
        if self.ui.window.isVisible():
            self.ui.items = self.storage.get_items()
            self.ui.table_view.reloadData()

    def setup_menu(self):
        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(-1)
        self.status_item.button().setTitle_("📋")
        
        menu = NSMenu.alloc().init()
        
        info = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Cmd+Shift+V to show", None, "")
        info.setEnabled_(False)
        menu.addItem_(info)
        menu.addItem_(NSMenuItem.separatorItem())
        
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
        menu.addItem_(quit_item)
        
        self.status_item.setMenu_(menu)

    def setup_hotkey(self):
        def on_activate():
            print("Hotkey pressed! Showing UI.")
            AppHelper.callAfter(self.show_ui)
            
        hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<cmd>+<shift>+v'),
            on_activate
        )
        
        self.listener = keyboard.Listener(
            on_press=lambda k: hotkey.press(self.listener.canonical(k)),
            on_release=lambda k: hotkey.release(self.listener.canonical(k))
        )
        self.listener.start()

    def show_ui(self):
        items = self.storage.get_items()
        self.ui.show_items(items)


def main():
    app = NSApplication.sharedApplication()
    delegate = AppController.alloc().init()
    app.setDelegate_(delegate)
    
    # Run as a background accessory app (no dock icon, but can have windows)
    # NSApplicationActivationPolicyAccessory = 1
    app.setActivationPolicy_(1) 
    
    print("🚀 Clipboard Manager Started!")
    print("   Press Cmd+Shift+V to show history.")
    
    AppHelper.runEventLoop()


if __name__ == '__main__':
    main()
