# Tickzen AI Assistant

AI-powered financial chat assistant that talks to OpenAI, Claude, and other models via Puter.js directly from the browser. Designed specifically for stock analysis, market insights, and investment research. No API keys, no backend required.

## Features

- Clean, responsive ChatGPT-like interface with Tickzen green theme
- Multiple conversations with titles and timestamps
- Model picker (OpenAI, Claude, Gemini, Mistral, Llama) and custom model ID
- System prompt, temperature, and memory control
- Streaming responses with Stop button
- Local history (localStorage), import/export JSON
- Specialized prompts for financial analysis and stock research
- Tickzen-branded interface optimized for financial use cases

## Run locally (Windows PowerShell)

Option A — batch file:

```powershell
./start-server.bat
```

Option B — direct command:

```powershell
npx serve .
```

Then open the printed URL (for example http://localhost:3000).

If you prefer Python instead of Node, use:

```powershell
python -m http.server 3000
```

and browse to http://localhost:3000.

## Files

- `index.html` — app shell and layout
- `styles.css` — UI styles
- `models.js` — model groups and population helper
- `app.js` — application logic, state, streaming, history

## Notes

- All AI calls are client-side using `https://js.puter.com/v2/`.
- You can add or adjust model IDs in `models.js`.
- Data is stored in the browser (localStorage). Use Export/Import to move between browsers.
- Interface is customized for Tickzen's financial analysis platform with green accent colors.
- Default suggestions focus on stock analysis, market trends, and investment research.
