// Supported models for puter.ai.chat must come from the official list.
// We attempt to fetch from https://puter.com/puterai/chat/models, and fall back to a known set.

const FALLBACK_MODELS = [
  'gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-5-chat-latest',
  'gpt-4.5-preview', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
  'gpt-4o', 'gpt-4o-mini',
  'o1', 'o1-mini', 'o1-pro',
  'o3', 'o3-mini', 'o4-mini'
];

let SUPPORTED = [...FALLBACK_MODELS];
let LAST_FETCH = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes cache

export async function getSupportedChatModels(){
  // Use cache if recent
  if (Date.now() - LAST_FETCH < CACHE_DURATION && SUPPORTED.length > 0) {
    return SUPPORTED;
  }
  
  try{
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
    const res = await fetch('https://puter.com/puterai/chat/models', { 
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }
    });
    
    clearTimeout(timeoutId);
    
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if(Array.isArray(data) && data.length){ 
      SUPPORTED = data;
      LAST_FETCH = Date.now();
    }
  }catch(error){
    console.warn('Failed to fetch supported models, using fallback:', error.message);
    // keep fallback - don't update LAST_FETCH so we'll try again next time
  }
  return SUPPORTED;
}

export function isSupportedModel(name){
  if(!name) return false;
  return SUPPORTED.includes(name);
}

export async function populateModelSelect(selectEl){
  const list = await getSupportedChatModels();
  const currentValue = selectEl.value;
  
  selectEl.innerHTML = '';
  
  // Group models by type for better organization
  const modelGroups = {
    'GPT-5': list.filter(m => m.startsWith('gpt-5')),
    'GPT-4': list.filter(m => m.startsWith('gpt-4')),
    'O-Series': list.filter(m => m.startsWith('o')),
    'Other': list.filter(m => !m.startsWith('gpt-') && !m.startsWith('o'))
  };
  
  // Add models with optgroups for better organization
  for (const [groupName, models] of Object.entries(modelGroups)) {
    if (models.length === 0) continue;
    
    if (models.length > 3) {
      const optgroup = document.createElement('optgroup');
      optgroup.label = groupName;
      
      for (const m of models) {
        const o = document.createElement('option');
        o.value = m; 
        o.textContent = m;
        optgroup.appendChild(o);
      }
      selectEl.appendChild(optgroup);
    } else {
      // If few models, add directly without grouping
      for (const m of models) {
        const o = document.createElement('option');
        o.value = m; 
        o.textContent = m;
        selectEl.appendChild(o);
      }
    }
  }
  
  // Restore previous selection if still available, otherwise use default
  if (currentValue && list.includes(currentValue)) {
    selectEl.value = currentValue;
  } else if(list.includes('gpt-4o')) {
    selectEl.value = 'gpt-4o';
  } else if(list.length) {
    selectEl.value = list[0];
  }
}
