# Future Features for Implementation

The following features have been identified to improve the workflow of Mac power users who perform frequent file operations and copy-pasting.

### 1. Instant Search and Filtering
- Allow immediate typing when the clipboard manager opens to fuzzy-search the history.
- Quickly filter down to specific file paths or text snippets.

### 2. Flexible File Pasting (Path vs. Actual File)
- **Default paste into Finder**: Paste the actual file.
- **Alternative paste**: Provide a modifier key (e.g., `Option + Click` or `Shift + Enter`) to paste the file's absolute text path (e.g., `/Users/banhi/Downloads/data.csv`) instead of the file itself.

### 3. Number Row Hotkeys (1-9)
- Enable pressing `1`, `2`, `3`, etc., immediately after opening the clipboard manager to instantly paste the corresponding item from the list without using the mouse or arrow keys.

### 4. Paste as Plain Text (Format Stripping)
- Add an option or a hotkey within the menu to force the item to paste as strictly plain, unformatted text to strip away formatting, fonts, and colors copied from browsers or rich text editors.

### 5. Pinned / Favorite Items
- Allow pinning frequently used items (server paths, bash commands, email signatures).
- Keep pinned items at the top of the clipboard list so they never get pushed out of the history.

### 6. Drag and Drop Support
- Allow clicking and dragging an image or file directly out of the clipboard manager window and dropping it onto the desktop, into an email draft, or other applications.

### 7. Multi-Item Merge Paste
- Support multi-selection (e.g., holding `Cmd` to select multiple items).
- Upon hitting Enter, paste all selected items at once, separated by newlines.

### 8. Privacy Exclusions
- Automatically ignore copied passwords by respecting macOS's native concealed pasteboard types.
- Provide a blacklist for specific applications (like 1Password, Bitwarden) to prevent sensitive data from being saved in the plain text history.

### 9. AI Integration (Lightweight & Native Architecture)
The following AI features are architected specifically to keep the clipboard manager extremely lightweight, fast, and secure by minimizing massive dependencies like local LLMs or Heavy ML frameworks.

**Phase 1: The Offline Upgrades (0 API Keys required)**
- **Image-to-Text (Smart OCR)**
  - *Implementation:* Use macOS's native `Vision` framework (`VNRecognizeTextRequest`) via `PyObjC`. This adds 0 MB to the app, runs instantly offline, and extracts searchable text from any copied screenshot.
- **Context-Aware Actions (Smart Triggers)**
  - *Implementation:* Use the native macOS `Foundation` framework's `NSDataDetector`. It instantly parses copied text to detect addresses, dates, and URLs, allowing us to show quick-action buttons (e.g., "Open in Maps") without any machine learning overhead.
- **Auto-Categorization & Smart Tags**
  - *Implementation:* Use a hybrid approach. Use simple Python Regex heuristics (e.g., detecting `{}` or `def ` for code). Use the native macOS `NaturalLanguage` framework (`NLTagger`) to extract names, organizations, and places.
- **Semantic/Fuzzy Search**
  - *Implementation:* Use the lightweight Python package `rank_bm25` to provide fuzzy, keyword-based search that improves on basic text matching without the heavy memory cost of running a local embedding model.
- **Extractive Summarization**
  - *Implementation:* Use the pure-Python package `sumy` (TextRank algorithm) to generate instant, mathematically-based summaries of long text without needing an LLM.

**Phase 2: The Opt-In Cloud Features (API Key required)**
- **"Magic Paste" Transformations (Rewrite, Translate, Fix Grammar)**
  - *Implementation:* Create an optional "Bring Your Own Key" (BYOK) settings panel for OpenAI, Anthropic, or Gemini. Since rewriting and translating require generative AI, it must use cloud LLMs to keep the app small. If the user provides a key, these Magic Paste buttons become available.
