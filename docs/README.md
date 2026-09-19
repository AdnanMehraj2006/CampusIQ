# PDF Documentation Generation

## Available Documentation Source

The project documentation is available in `docs/DOCUMENTATION.md`. This Markdown file can be converted to PDF using various methods.

## Recommended Methods to Generate PDF

### Method 1: Using Pandoc (Recommended)

```bash
# Install pandoc first: https://pandoc.org/installing.html
pandoc docs/DOCUMENTATION.md -o docs/CAMPUSIQ_DOCUMENTATION.pdf
```

### Method 2: Using Markdown-to-PDF Online Tool

1. Open `docs/DOCUMENTATION.md` in your editor
2. Use an online markdown-to-pdf converter:
   - https://markdown-to-pdf.com/
   - https://markdowntopdf.com/

### Method 3: Using Browser Print to PDF

1. View `docs/DOCUMENTATION.md` in a markdown viewer (VS Code, Typora, etc.)
2. Press Ctrl+P (or Cmd+P on Mac)
3. Select "Save as PDF"

### Method 4: Using VS Code Extension

1. Install "Markdown PDF" extension in VS Code
2. Right-click on `docs/DOCUMENTATION.md`
3. Select "Markdown PDF: Export (pdf)"

## Documentation Contents

The documentation covers:

- Project Overview
- Features
- Technology Stack
- Architecture Diagram
- Setup Instructions
- API Documentation
- Testing
- Security
- Deployment
- File Structure

## File Locations

- Source Markdown: `docs/DOCUMENTATION.md`
- Output PDF: `docs/CAMPUSIQ_DOCUMENTATION.pdf` (after conversion)

---

*For questions about the documentation, please open an issue on the repository.*
