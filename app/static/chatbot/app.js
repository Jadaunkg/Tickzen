import { populateModelSelect, isSupportedModel, getSupportedChatModels } from './models.js';
// Markdown renderer + sanitizer (ESM from CDN)
import { marked } from 'https://cdn.jsdelivr.net/npm/marked@12/+esm';
import DOMPurify from 'https://cdn.jsdelivr.net/npm/dompurify@3.1.6/+esm';

// Simple local persistence using localStorage
const STORAGE_KEYS = {
  sessions: 'tickzen-ai.sessions.v1',
  lastSessionId: 'tickzen-ai.lastSessionId.v1'
};

// Generate an id
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

// Render helpers
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function formatTime(ts){
  const d = new Date(ts);
  return d.toLocaleString();
}

// Full Markdown rendering with GFM and sanitization
marked.setOptions({ 
  gfm: true, 
  breaks: true, 
  headerIds: false, 
  mangle: false,
  sanitize: false
});

function renderMarkdown(text){
  if (!text) return '';
  
  // Pre-process text to handle special cases
  let processedText = text
    // Handle inline code that might contain mathematical expressions
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Handle code blocks with better formatting
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    })
    // Handle single line code blocks in brackets
    .replace(/^\[([^\]]+)\]$/gm, '```\n$1\n```')
    // Handle mathematical expressions
    .replace(/\\max\(/g, 'max(')
    .replace(/\\\\/g, '\\');
  
  const raw = marked.parse(processedText);
  return DOMPurify.sanitize(raw, { 
    USE_PROFILES: { html: true },
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    ALLOWED_ATTR: ['href', 'class', 'target']
  });
}

// Session model
function newSession(){
  return {
    id: uid(),
    title: 'New conversation',
    model: 'gpt-4o',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    system: 'You are Tickzen AI, a specialized financial assistant focused on stock analysis, market research, and investment insights. You help users understand financial markets, analyze stocks, interpret financial data, and provide investment research. Always provide educational information and remind users that this is not financial advice and they should consult with qualified financial professionals for investment decisions.',
    messages: [] // {role:'user'|'assistant'|'system'|'tool', content:string}
  };
}

function loadSessions(){
  try{ return JSON.parse(localStorage.getItem(STORAGE_KEYS.sessions)||'[]'); }catch{ return []; }
}
function saveSessions(sessions){
  localStorage.setItem(STORAGE_KEYS.sessions, JSON.stringify(sessions));
}
function loadLastSessionId(){ return localStorage.getItem(STORAGE_KEYS.lastSessionId) }
function saveLastSessionId(id){ localStorage.setItem(STORAGE_KEYS.lastSessionId, id) }

// Global state
let sessions = loadSessions();
let current = null; // active session object
let cancelStreaming = false; // simple cancel flag for streaming

// UI elements
const elList = $('#sessionList');
const elSearch = $('#search');
const elModel = $('#modelSelect');
const elCustomModel = $('#customModel');
const elSystem = $('#systemPrompt');
const elMessages = $('#messages');
const elInput = $('#userInput');
const elSend = $('#btnSend');
const elStop = $('#btnStop');
const elClear = $('#btnClear');
const elDelete = $('#btnDelete');
const elNew = $('#btnNew');
const elTokenInfo = $('#tokenInfo');
const elSidebar = $('#sidebar');
const elToggleSidebar = $('#btnToggleSidebar');
const elImport = $('#importFile');
const elExport = $('#btnExport');
const elTemp = $('#temperature');
const elTempVal = $('#temperatureVal');
const elSpeed = $('#chkSpeed');

// Initialize and preload for faster responses
let connectionWarmed = false;

async function warmupConnection() {
  if (connectionWarmed) return;
  
  try {
    // Small test call to warm up the connection
    const testMessages = [{ role: 'user', content: 'hi' }];
    const supported = await getSupportedChatModels();
    const fastModel = supported.find(m => m.includes('mini') || m.includes('nano')) || supported[0];
    
    if (fastModel) {
      const stream = await puter.ai.chat(testMessages, { 
        model: fastModel, 
        stream: true, 
        max_tokens: 1,
        temperature: 0.1
      });
      
      // Just start the stream to warm up, then stop
      for await (const part of stream) {
        break; // Stop after first chunk
      }
      
      connectionWarmed = true;
      console.log('Connection warmed up with model:', fastModel);
    }
  } catch (error) {
    console.log('Warmup failed, but continuing:', error.message);
  }
}

// Initialize model list dynamically with error handling
(async()=>{ 
  try {
    await populateModelSelect(elModel);
    
    // Warm up connection after models are loaded
    setTimeout(warmupConnection, 1000);
  } catch (error) {
    console.warn('Failed to load models:', error);
    // Fallback if model loading fails
    const fallbackModels = ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini'];
    elModel.innerHTML = '';
    fallbackModels.forEach(model => {
      const option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      elModel.appendChild(option);
    });
    elModel.value = 'gpt-4o';
  }
})();

function ensureAtLeastOneSession(){
  if(!sessions.length){
    const s = newSession();
    sessions.push(s); saveSessions(sessions); saveLastSessionId(s.id);
  }
}
ensureAtLeastOneSession();

function setActiveSessionById(id){
  const s = sessions.find(x=>x.id===id) || sessions[0];
  current = s; saveLastSessionId(s.id); renderAll();
}

function renderSessionList(){
  const q = (elSearch.value||'').toLowerCase();
  elList.innerHTML = '';
  for(const s of sessions){
    const title = s.title || 'New conversation';
    if(q && !title.toLowerCase().includes(q)) continue;
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'session' + (current && current.id===s.id ? ' active' : '');
    item.innerHTML = `
      <div class="avatar">💬</div>
      <div class="title">${escapeHtml(title)}</div>
      <div class="time">${formatTime(s.updatedAt)}</div>
    `;
    item.onclick = ()=>{ 
      setActiveSessionById(s.id); 
      if(window.innerWidth < 1024) {
        elSidebar.classList.remove('open'); 
      }
    };
    elList.appendChild(item);
  }
}

function renderMessages(){
  if(!current) return;
  
  // Store scroll position to maintain it
  const wasAtBottom = elMessages.scrollTop >= (elMessages.scrollHeight - elMessages.clientHeight - 50);
  
  elMessages.innerHTML = '';
  
  // Add welcome message for empty conversations
  if(current.messages.length === 0) {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
      <div class="welcome-content">
        <h2><img src="/static/chatbot/favicon.png" alt="Tickzen" style="width: 40px; height: 40px; vertical-align: middle; margin-right: 12px; object-fit: contain;"> Welcome to Tickzen AI</h2>
        <p>Your intelligent financial assistant powered by advanced AI. Ask me about stocks, market analysis, investment strategies, and financial insights!</p>
        <div class="welcome-suggestions">
          <button class="suggestion-btn" data-suggestion="Analyze the financial performance of Apple (AAPL)">� Analyze a stock</button>
          <button class="suggestion-btn" data-suggestion="What are the current market trends?">� Market trends</button>
          <button class="suggestion-btn" data-suggestion="Explain technical analysis indicators">� Technical analysis</button>
          <button class="suggestion-btn" data-suggestion="Help me build an investment portfolio">� Investment advice</button>
        </div>
      </div>
    `;
    elMessages.appendChild(welcomeDiv);
    
    // Add click handlers for suggestions
    welcomeDiv.querySelectorAll('.suggestion-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const suggestion = btn.dataset.suggestion;
        elInput.value = suggestion;
        elInput.focus();
      });
    });
    
    return;
  }
  
  // Create document fragment to avoid multiple reflows
  const fragment = document.createDocumentFragment();
  
  for(const msg of current.messages){
    const row = document.createElement('div');
    row.className = 'msg ' + (msg.role==='assistant'?'assistant':'user');
    row.setAttribute('data-role', msg.role);
    const contentHtml = renderMarkdown(msg.content);
    row.innerHTML = `
      <div class="content">${contentHtml}</div>
      <button class="msg-copy-btn" data-action="copy-msg" title="Copy message">📋</button>
    `;
    fragment.appendChild(row);
  }
  
  // Single DOM update
  elMessages.appendChild(fragment);
  
  // Add code copy buttons in a separate pass
  const preElements = elMessages.querySelectorAll('pre:not([data-copy-added])');
  preElements.forEach(pre => {
    pre.setAttribute('data-copy-added', 'true');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'code-copy-btn';
    btn.textContent = 'Copy';
    btn.title = 'Copy code';
    btn.addEventListener('click', async ()=>{
      const code = pre.querySelector('code');
      const text = code ? code.innerText : pre.innerText;
      try {
        await navigator.clipboard.writeText(text||'');
        btn.textContent = '✓ Copied';
        setTimeout(() => btn.textContent = 'Copy', 2000);
      } catch (err) {
        console.warn('Copy failed:', err);
        btn.textContent = '❌ Failed';
        setTimeout(() => btn.textContent = 'Copy', 2000);
      }
    });
    pre.appendChild(btn);
  });
  
  // Attach message copy handlers in a single pass
  elMessages.querySelectorAll('[data-action="copy-msg"]:not([data-handler-added])').forEach(btn=>{
    btn.setAttribute('data-handler-added', 'true');
    btn.onclick = async (e)=>{
      const msgEl = e.currentTarget.closest('.msg');
      const text = msgEl?.querySelector('.content')?.innerText || '';
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = '✓';
        setTimeout(() => btn.textContent = '📋', 2000);
      } catch (err) {
        console.warn('Copy failed:', err);
        btn.textContent = '❌';
        setTimeout(() => btn.textContent = '📋', 2000);
      }
    };
  });
  
  // Restore scroll position if we were at bottom, scroll to bottom
  if (wasAtBottom) {
    elMessages.scrollTop = elMessages.scrollHeight;
  }
}

function renderTop(){
  if(!current) return;
  elModel.value = current.model || 'gpt-4o';
  elSystem.value = current.system || '';
}

function renderAll(){
  renderSessionList();
  renderTop();
  renderMessages();
}

// Utils
function escapeHtml(str){
  return (str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function updateSessionMetaFromFirstAssistantMessage(s){
  if(!s.title || s.title==='New chat' || s.title==='New conversation'){
    const firstUser = s.messages.find(m=>m.role==='user');
    if(firstUser){
      // Better title generation - take first meaningful phrase
      let title = firstUser.content.slice(0,50).trim();
      if(firstUser.content.length > 50) {
        const lastSpace = title.lastIndexOf(' ');
        if(lastSpace > 20) title = title.slice(0, lastSpace);
        title += '...';
      }
      s.title = title;
    }
  }
  s.updatedAt = Date.now();
}

// Error formatting helper so we don't show [object Object]
function formatError(err){
  try{
    if(!err) return 'Unknown error';
    if(typeof err === 'string') return err;
    if(err instanceof Error) return err.message || err.toString();
    // Common shapes: {message, error: {message, type, code}}
    if(err.message) return err.message;
    if(err.error){
      const inner = err.error;
      if(typeof inner === 'string') return inner;
      if(inner.message) return inner.message + (inner.type? ` (${inner.type})`: '');
      return JSON.stringify(inner);
    }
    if(err.status && err.statusText) return `${err.status} ${err.statusText}`;
    return JSON.stringify(err);
  }catch{
    try{ return String(err); }catch{ return 'Unknown error'; }
  }
}

// Token estimation (very rough)
function approxTokensFromText(text){
  // crude heuristic: 1 token ~ 4 chars
  return Math.ceil((text||'').length/4);
}
function updateTokenInfoPreview(){
  if(!current) { elTokenInfo.textContent=''; return; }
  const includeMemory = $('#chkMemory').checked;
  const history = includeMemory ? current.messages.slice(-(elSpeed && elSpeed.checked ? 8 : 20)) : [];
  const sys = (current.system||'');
  const input = elInput.value||'';
  const histText = history.map(m=>m.content).join('\n');
  const total = approxTokensFromText(sys) + approxTokensFromText(histText) + approxTokensFromText(input);
  
  // More informative token display
  const model = elModel.value || 'gpt-4o';
  elTokenInfo.textContent = `~${total.toLocaleString()} tokens • ${model}`;
}

// Chat logic
async function sendMessage(text){
  if(!text.trim()) return;
  if(!current) return;

  // Resolve model and validate (prefer lighter model in Speed mode if custom is not set)
  const fromCustom = elCustomModel.value.trim();
  const supported = await getSupportedChatModels();
  let chosen = (fromCustom || elModel.value).trim();
  if(elSpeed && elSpeed.checked && !fromCustom){
    const preferredOrder = ['gpt-4.1-nano','gpt-4.1-mini','gpt-4o-mini','gpt-4.1','gpt-4o'];
    const fast = preferredOrder.find(m=>supported.includes(m));
    if(fast) chosen = fast;
  }
  const model = chosen;
  const valid = supported.includes(model);
  if(!valid){
    const msg = `Selected model "${model}" is not supported. Pick one of: ${supported.slice(0,30).join(', ')}${supported.length>30?' …':''}`;
    alert(msg);
    return;
  }
  current.model = model;
  current.system = elSystem.value;

  // Compose context with optimized history length for speed
  const includeMemory = $('#chkMemory').checked;
  const historyLength = elSpeed && elSpeed.checked ? 6 : 12; // Reduced for faster responses
  const history = includeMemory ? current.messages.slice(-historyLength) : [];
  const messages = [];
  if(current.system?.trim()) messages.push({ role:'system', content: current.system.trim() });
  messages.push(...history);
  messages.push({ role:'user', content: text });

  // Push to UI and state
  current.messages.push({ role:'user', content: text });
  updateSessionMetaFromFirstAssistantMessage(current);
  saveSessions(sessions); renderAll();

  // Streaming with optimized loading state
  cancelStreaming = false;
  const assistantMsg = { role:'assistant', content: '' };
  current.messages.push(assistantMsg);
  renderMessages();
  
  // Show enhanced typing indicator
  const indicator = document.createElement('div');
  indicator.className = 'msg assistant typing';
  indicator.innerHTML = `
    <div class="content">
      <div class="typing-text">Thinking...</div>
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  elMessages.appendChild(indicator);
  elMessages.scrollTop = elMessages.scrollHeight;

  // Update button states
  elSend.disabled = true; 
  elSend.textContent = 'Generating...';
  elStop.disabled = false; 
  elInput.value = '';
  elInput.style.height = 'auto';

  async function streamWith(modelId){
    // Optimized temperature and streaming settings for faster responses
    const temperature = elSpeed && elSpeed.checked ? 0.3 : (Number(elTemp.value)||1);
    const streamSettings = { 
      model: modelId, 
      stream: true, 
      temperature,
      max_tokens: elSpeed && elSpeed.checked ? 1500 : 3000, // Limit tokens for speed
      top_p: 0.9, // Optimize for faster generation
      frequency_penalty: 0.1
    };
    
    const stream = await puter.ai.chat(messages, streamSettings);
    let firstChunk = true;
    
    for await (const part of stream){
      if(cancelStreaming) break;
      
      // Remove typing indicator on first chunk for faster perceived response
      if(firstChunk && indicator.parentElement){ 
        indicator.remove(); 
        firstChunk = false;
      }
      
      // Puter.js parts have .text or .message?.content
      const chunk = part?.text ?? part?.message?.content ?? '';
      assistantMsg.content += chunk;
      
      // Optimized DOM updates - batch every few chunks for better performance
      if (assistantMsg.content.length % 50 === 0 || chunk.includes('\n')) {
        const lastMsg = elMessages.querySelector('.msg:last-child .content');
        if (lastMsg) {
          lastMsg.innerHTML = renderMarkdown(assistantMsg.content);
          
          // Add code copy buttons to any new pre elements
          const newPre = lastMsg.querySelectorAll('pre:not([data-copy-added])');
          newPre.forEach(pre => {
            pre.setAttribute('data-copy-added', 'true');
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'code-copy-btn';
            btn.textContent = 'Copy';
            btn.title = 'Copy code';
            btn.addEventListener('click', async ()=>{
              const code = pre.querySelector('code');
              const text = code ? code.innerText : pre.innerText;
              try {
                await navigator.clipboard.writeText(text||'');
                btn.textContent = '✓ Copied';
                setTimeout(() => btn.textContent = 'Copy', 2000);
              } catch (err) {
                btn.textContent = '❌ Failed';
                setTimeout(() => btn.textContent = 'Copy', 2000);
              }
            });
            pre.appendChild(btn);
          });
          
          // Smooth scroll to bottom only if user was already at bottom
          const isAtBottom = elMessages.scrollTop >= (elMessages.scrollHeight - elMessages.clientHeight - 100);
          if (isAtBottom) {
            elMessages.scrollTop = elMessages.scrollHeight;
          }
        }
      }
    }
    
    // Final update to ensure everything is rendered
    const lastMsg = elMessages.querySelector('.msg:last-child .content');
    if (lastMsg) {
      lastMsg.innerHTML = renderMarkdown(assistantMsg.content);
      
      // Add copy buttons to final content
      const newPre = lastMsg.querySelectorAll('pre:not([data-copy-added])');
      newPre.forEach(pre => {
        pre.setAttribute('data-copy-added', 'true');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'code-copy-btn';
        btn.textContent = 'Copy';
        btn.title = 'Copy code';
        btn.addEventListener('click', async ()=>{
          const code = pre.querySelector('code');
          const text = code ? code.innerText : pre.innerText;
          try {
            await navigator.clipboard.writeText(text||'');
            btn.textContent = '✓ Copied';
            setTimeout(() => btn.textContent = 'Copy', 2000);
          } catch (err) {
            btn.textContent = '❌ Failed';
            setTimeout(() => btn.textContent = 'Copy', 2000);
          }
        });
        pre.appendChild(btn);
      });
      
      elMessages.scrollTop = elMessages.scrollHeight;
    }
  }

  try{
    await streamWith(model);
  }catch(err){
    console.error('AI error', err);
    const msgText = formatError(err);
    const isPermission = /permission denied/i.test(msgText) || /usage-limited-chat/i.test(msgText) || /403|401/.test(msgText);
    if(isPermission){
      // Show notice banner with login suggestion and retry button
      const notice = document.querySelector('#notice');
      if(notice){
        notice.classList.remove('hidden');
        notice.innerHTML = `Permission denied for model <code>${escapeHtml(model)}</code>. `+
          `Try signing in to Puter and then Retry. <button id="btnLogin" class="btn">Sign in</button> <button id="btnRetry" class="btn primary">Retry</button>`;
        const btnLogin = document.querySelector('#btnLogin');
        const btnRetry = document.querySelector('#btnRetry');
        btnLogin?.addEventListener('click', async ()=>{
          try{ await puter.auth.signIn(); notice.classList.add('hidden'); }catch(e){ console.warn('Sign-in cancelled or failed', e); }
        }, { once:true });
        btnRetry?.addEventListener('click', async ()=>{
          notice.classList.add('hidden');
          // Retry with a smarter fallback cycle across supported fast models, then the rest
          try{
            const supported = await getSupportedChatModels();
            const fast = ['gpt-4.1-nano','gpt-4.1-mini','gpt-4o-mini','gpt-4.1','gpt-4o'].filter(m=>supported.includes(m));
            const rest = supported.filter(m=>!fast.includes(m));
            const order = [...fast, ...rest].filter(m=>m!==model);
            let done = false;
            for(const m of order){
              try{
                assistantMsg.content += `\n[fallback] Trying ${m}…\n`;
                current.model = m;
                await streamWith(m);
                done = true; break;
              }catch(e){
                const t = formatError(e);
                if(!/permission denied|usage-limited-chat|403|401/i.test(t)){
                  // break on non-permission errors
                  assistantMsg.content += `\n[error] ${t}`; break;
                }
              }
            }
            if(!done){ assistantMsg.content += `\n[error] ${msgText}`; }
          }catch(e){ assistantMsg.content += `\n[error] ${formatError(e)}`; }
        }, { once:true });
      }
      // also append a short note into the chat
      assistantMsg.content += `\n[fallback] Permission denied on ${model}. Use Sign in + Retry above.`;
    }else{
      assistantMsg.content += `\n[error] ${msgText}`;
    }
  }finally{
    // Reset button states
    elSend.disabled = false; 
    elSend.innerHTML = '<span>Send</span><span>↗</span>';
    elStop.disabled = true;
    
    // Ensure typing indicator is gone
    if(indicator.parentElement){ indicator.remove(); }
    
    updateSessionMetaFromFirstAssistantMessage(current);
    saveSessions(sessions); 
    renderAll();
    
    // Focus input for next message
    elInput.focus();
  }
}

// Enhanced Events with better UX
$('#composer').addEventListener('submit', (e)=>{
  e.preventDefault();
  const text = elInput.value.trim();
  if (text) {
    sendMessage(text);
  }
});

elInput.addEventListener('keydown', (e)=>{
  if(e.key==='Enter' && !e.shiftKey){ 
    e.preventDefault(); 
    const text = elInput.value.trim();
    if (text) {
      $('#btnSend').click(); 
    }
  }
});

// Improved auto-resize to prevent shaking
let resizeTimeout;
elInput.addEventListener('input', ()=>{
  updateTokenInfoPreview();
  
  // Debounce resize operations
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    const minHeight = 52;
    const maxHeight = 300;
    
    // Store current scroll position
    const scrollTop = elMessages.scrollTop;
    
    // Reset height to measure content
    elInput.style.height = minHeight + 'px';
    const scrollHeight = elInput.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
    
    // Only change if different
    if (parseInt(elInput.style.height) !== newHeight) {
      elInput.style.height = newHeight + 'px';
    }
    
    // Restore scroll position to prevent jumping
    elMessages.scrollTop = scrollTop;
  }, 16); // ~60fps
});

elStop.addEventListener('click', ()=>{ 
  cancelStreaming = true; 
  elStop.disabled = true;
  elSend.disabled = false;
});

elClear.addEventListener('click', ()=>{
  if(!current) return;
  if(!confirm('Clear all messages in this conversation?')) return;
  current.messages = []; 
  current.updatedAt = Date.now(); 
  saveSessions(sessions); 
  renderAll();
});

elDelete.addEventListener('click', ()=>{
  if(!current) return;
  if(!confirm('Delete this conversation permanently?')) return;
  sessions = sessions.filter(s=>s.id!==current.id); 
  saveSessions(sessions);
  ensureAtLeastOneSession(); 
  setActiveSessionById(sessions[0].id);
});

elNew.addEventListener('click', ()=>{
  const s = newSession(); 
  s.title = 'New conversation';
  sessions.unshift(s); 
  saveSessions(sessions); 
  setActiveSessionById(s.id);
  elInput.focus();
});

elSearch.addEventListener('input', renderSessionList);

elToggleSidebar.addEventListener('click', ()=>{ 
  elSidebar.classList.toggle('open'); 
});

elModel.addEventListener('change', async ()=>{ 
  if(current){ 
    const selectedModel = elModel.value;
    
    // Validate model immediately
    try {
      const supported = await getSupportedChatModels();
      if (!supported.includes(selectedModel)) {
        alert(`Model "${selectedModel}" is not supported. Please select a different model.`);
        // Revert to previous working model
        elModel.value = current.model || 'gpt-4o';
        return;
      }
      
      current.model = selectedModel; 
      saveSessions(sessions); 
      updateTokenInfoPreview();
      
      // Show visual feedback that model was selected
      const modelSelect = elModel;
      const originalBorder = modelSelect.style.borderColor;
      modelSelect.style.borderColor = '#22c55e';
      modelSelect.style.boxShadow = '0 0 0 2px rgba(34, 197, 94, 0.2)';
      
      setTimeout(() => {
        modelSelect.style.borderColor = originalBorder;
        modelSelect.style.boxShadow = '';
      }, 1000);
      
    } catch (error) {
      console.error('Error validating model:', error);
      alert('Error validating model selection. Please try again.');
    }
  }
});

elSystem.addEventListener('input', ()=>{ 
  if(current){ 
    current.system = elSystem.value; 
    current.updatedAt = Date.now(); 
    saveSessions(sessions); 
    updateTokenInfoPreview(); 
  }
});

elTemp.addEventListener('input', ()=>{ 
  elTempVal.textContent = Number(elTemp.value).toFixed(1); 
});

// Initialize temperature display
elTempVal.textContent = Number(elTemp.value).toFixed(1);
updateTokenInfoPreview();

// Memory and speed toggles
$('#chkMemory').addEventListener('change', updateTokenInfoPreview);
if(elSpeed){ 
  elSpeed.addEventListener('change', updateTokenInfoPreview); 
}

// Import/Export
elExport.addEventListener('click', ()=>{
  const data = JSON.stringify({ version: 1, sessions }, null, 2);
  const blob = new Blob([data], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `tickzen-ai-export-${Date.now()}.json`; a.click();
  URL.revokeObjectURL(url);
});

elImport.addEventListener('change', async (e)=>{
  const file = e.target.files?.[0]; if(!file) return;
  try{
    const text = await file.text();
    const data = JSON.parse(text);
    if(!data.sessions || !Array.isArray(data.sessions)) throw new Error('Invalid file');
    sessions = data.sessions; saveSessions(sessions); setActiveSessionById(sessions[0]?.id || null);
  }catch(err){ alert('Import failed: '+(err?.message||err)); }
  finally{ e.target.value=''; }
});

// Initial selection
const last = loadLastSessionId();
setActiveSessionById(last || sessions[0].id);

// Accessibility: focus input on load
setTimeout(()=>{ elInput.focus(); }, 300);
