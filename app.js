/* ============================================================
   Verity — shared app logic (storage, auth, scoring, nav)
   Loaded on every page. Uses localStorage so the dashboard can
   show real history/trend across visits (all client-side demo
   data — nothing leaves the browser).
   ============================================================ */

var LS_USER = 'lucida_user';
var LS_HISTORY = 'lucida_history';

/* ---------- storage helpers ----------
   Some browsers (notably Safari) throw a SecurityError on ANY localStorage
   access when a page is opened directly from disk (file://) or in private
   browsing. That used to crash whichever button triggered it (signup,
   login, finishing a test) with no visible error — the click just did
   nothing. This wrapper falls back to an in-memory store instead, so
   every button keeps working even when real persistence isn't available;
   history just won't survive a page reload in that case. */
var memoryStore = {};
var storageWorks = (function(){
  try{
    var k = '__lucida_test__';
    localStorage.setItem(k, '1');
    localStorage.removeItem(k);
    return true;
  }catch(e){ return false; }
})();

function safeGet(key){
  try{
    return storageWorks ? localStorage.getItem(key) : (memoryStore[key] || null);
  }catch(e){ return memoryStore[key] || null; }
}
function safeSet(key, value){
  try{
    if(storageWorks){ localStorage.setItem(key, value); return; }
  }catch(e){ /* fall through to memory */ }
  memoryStore[key] = value;
}
function safeRemove(key){
  try{ if(storageWorks) localStorage.removeItem(key); }catch(e){}
  delete memoryStore[key];
}

function getUser(){
  try{ return JSON.parse(safeGet(LS_USER)); }catch(e){ return null; }
}
function setUser(u){ safeSet(LS_USER, JSON.stringify(u)); renderNavUser(); }

/* ---------- accounts (hashed passwords, real credential checks) ----------
   There's no server here, so this can't be real production auth — but it's
   no longer a fake "any email/password gets you in" flow either. Signup
   creates an account record with a salted SHA-256 hash of the password
   (via Web Crypto). Login looks up the account by username/email and
   rejects unless the submitted password hashes to the same value, so
   random or mismatched credentials are actually refused. */
var LS_ACCOUNTS = 'lucida_accounts';

function getAccounts(){
  try{ return JSON.parse(safeGet(LS_ACCOUNTS)) || []; }catch(e){ return []; }
}
function saveAccounts(list){ safeSet(LS_ACCOUNTS, JSON.stringify(list)); }

function randomSalt(){
  if(window.crypto && window.crypto.getRandomValues){
    var arr = new Uint8Array(16);
    window.crypto.getRandomValues(arr);
    return Array.from(arr).map(function(b){ return b.toString(16).padStart(2,'0'); }).join('');
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/* SHA-256 via Web Crypto when available (requires a secure context —
   https or localhost). Falls back to a simple non-cryptographic hash when
   it isn't (e.g. a page opened directly from disk over file://), so
   account creation/login still work everywhere, just without real
   cryptographic strength in that fallback case. */
async function hashPassword(password, salt){
  var text = salt + ':' + password;
  if(window.crypto && window.crypto.subtle && window.isSecureContext){
    try{
      var enc = new TextEncoder().encode(text);
      var buf = await window.crypto.subtle.digest('SHA-256', enc);
      return 'sha256:' + Array.from(new Uint8Array(buf)).map(function(b){ return b.toString(16).padStart(2,'0'); }).join('');
    }catch(e){ /* fall through to non-crypto fallback below */ }
  }
  var hash = 0;
  for(var i=0;i<text.length;i++){ hash = ((hash<<5)-hash+text.charCodeAt(i))|0; }
  return 'fallback:' + Math.abs(hash).toString(16) + ':' + text.length;
}

/* ---------- email validation ----------
   No backend here, so we can't send a real verification email — but we
   can catch the overwhelming majority of fake/typo'd/placeholder
   addresses before an account is ever created: proper RFC-ish syntax,
   no double dots, a real-looking domain with a TLD, and a blocklist of
   disposable-inbox and obviously-placeholder domains. */
var DISPOSABLE_EMAIL_DOMAINS = [
  'mailinator.com','tempmail.com','temp-mail.org','guerrillamail.com','guerrillamail.info',
  '10minutemail.com','10minutemail.net','yopmail.com','throwawaymail.com','fakeinbox.com',
  'trashmail.com','sharklasers.com','discard.email','maildrop.cc','getnada.com','dispostable.com',
  'mintemail.com','mailnesia.com','mail-temp.com','tempinbox.com','moakt.com','emailondeck.com',
  'spamgourmet.com','mytemp.email','fakemailgenerator.com','burnermail.io','tempr.email'
];
var PLACEHOLDER_EMAIL_DOMAINS = [
  'example.com','example.org','example.net','test.com','tests.com','fake.com','notreal.com',
  'asdf.com','foo.com','bar.com','foobar.com','yourdomain.com','mydomain.com','placeholder.com',
  'email.com','domain.com','none.com','nomail.com','abc.com'
];

function isValidEmail(email){
  email = (email||'').trim();
  if(!email) return { ok:false, reason:'Please enter an email address.' };

  var re = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  if(!re.test(email)) return { ok:false, reason:"That doesn't look like a valid email address." };

  var parts = email.split('@');
  var local = parts[0], domain = parts[1].toLowerCase();
  var tld = domain.split('.').pop();

  if(/\.\./.test(email) || local.charAt(0) === '.' || local.charAt(local.length-1) === '.'){
    return { ok:false, reason:"That email address isn't formatted correctly." };
  }
  if(tld.length < 2 || /^[0-9]+$/.test(tld)){
    return { ok:false, reason:'Please enter an email address with a valid domain (e.g. .com, .org).' };
  }
  if(DISPOSABLE_EMAIL_DOMAINS.indexOf(domain) !== -1){
    return { ok:false, reason:'Please use a real, non-disposable email address — temporary inboxes are not accepted.' };
  }
  if(PLACEHOLDER_EMAIL_DOMAINS.indexOf(domain) !== -1){
    return { ok:false, reason:"That looks like a placeholder email — please enter your real address." };
  }
  return { ok:true };
}

function findAccount(identifier){
  identifier = (identifier||'').trim().toLowerCase();
  return getAccounts().find(function(a){
    return a.username.toLowerCase() === identifier || a.email.toLowerCase() === identifier;
  }) || null;
}

/* Returns {ok:true, account} or {ok:false, reason} — never lets a login
   through without a matching, correctly-hashed password. */
async function createAccount(username, email, password){
  var accounts = getAccounts();
  var uname = username.trim();
  var mail = email.trim();
  if(findAccount(uname) || findAccount(mail)){
    return { ok:false, reason:'An account with that username or email already exists. Try signing in instead.' };
  }
  var salt = randomSalt();
  var hash = await hashPassword(password, salt);
  var account = { username: uname, email: mail, salt: salt, hash: hash, createdAt: Date.now() };
  accounts.push(account);
  saveAccounts(accounts);
  return { ok:true, account: account };
}

async function verifyCredentials(identifier, password){
  var account = findAccount(identifier);
  if(!account) return { ok:false, reason:"We couldn't find an account with that username or email." };
  var hash = await hashPassword(password, account.salt);
  if(hash !== account.hash) return { ok:false, reason:'Incorrect password.' };
  return { ok:true, account: account };
}

function getHistory(){
  try{ return JSON.parse(safeGet(LS_HISTORY)) || []; }catch(e){ return []; }
}
function addHistoryEntry(entry){
  var h = getHistory();
  entry.id = Date.now() + '-' + Math.random().toString(36).slice(2,7);
  entry.timestamp = Date.now();
  h.push(entry);
  safeSet(LS_HISTORY, JSON.stringify(h));
  return entry;
}

/* ---------- theme (light/dark, persisted) ---------- */
var LS_THEME = 'verity_theme';

function applyTheme(theme){
  document.documentElement.setAttribute('data-theme', theme === 'dark' ? 'dark' : 'light');
}
function getTheme(){
  var saved = safeGet(LS_THEME);
  if(saved) return saved;
  // Fall back to the OS-level preference the first time, if the browser exposes it.
  if(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
  return 'light';
}
function toggleTheme(){
  var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  safeSet(LS_THEME, next);
  renderThemeToggle();
}
function renderThemeToggle(){
  var slot = document.getElementById('theme-toggle-slot');
  if(!slot) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  slot.innerHTML = '<button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">' + (isDark ? '☀️' : '🌙') + '</button>';
}
// Applied immediately (not waiting for DOMContentLoaded) so the page never
// flashes light-then-dark on load.
applyTheme(getTheme());

/* ---------- nav (renders user pill + theme toggle) ---------- */
function renderNavUser(){
  var slot = document.getElementById('nav-user-slot');
  renderThemeToggle();
  if(!slot) return;
  var user = getUser();
  if(user){
    slot.innerHTML =
      '<div class="nav-user"><span class="pill">2FA on</span> ' + escapeHtml(user.username) + ' &nbsp;·&nbsp; <a href="dashboard.html" style="color:var(--blue-deep);font-weight:600;">Dashboard</a> &nbsp;·&nbsp; <a href="#" onclick="signOut();return false;" style="color:var(--text-soft);">Sign out</a></div>';
  } else {
    slot.innerHTML = '<a href="signup.html" class="nav-cta">Get started</a>';
  }
}
function signOut(){
  safeRemove(LS_USER);
  window.location.href = 'index.html';
}

function escapeHtml(s){
  var d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

/* ---------- scoring / bands ----------
   `probability` (0–1) is an ad-hoc pattern-match score computed from
   timing/acoustic markers in THIS demo — it is explicitly NOT a
   clinically validated diagnostic probability of having Alzheimer's.
   We show it as a percentage because that was asked for, but every
   place it's rendered pairs it with that disclaimer. */
function clamp01(x){ return Math.max(0, Math.min(1, x)); }
function bandFor(p){ if(p < 0.40) return 'typical'; if(p < 0.65) return 'some'; return 'several'; }
function bandLabel(b){ return { typical:'Markers look typical', some:'Some markers worth noting', several:'Several markers worth discussing' }[b]; }
function bandClass(b){ return 'band-' + b; }
function bandColor(b){ return { typical:'#2d6b52', some:'#8a6212', several:'#9c4030' }[b]; }

function computeStdDev(arr){
  if(!arr.length) return 0;
  var mean = arr.reduce(function(a,b){return a+b;},0)/arr.length;
  var variance = arr.reduce(function(a,b){return a+(b-mean)*(b-mean);},0)/arr.length;
  return Math.sqrt(variance);
}

function breakdownItem(value, label, note){
  return '<div class="breakdown-item"><div class="bv">' + value + '</div><div class="bl">' + label + '</div><div class="bn">' + note + '</div></div>';
}

function scoreBlockHtml(probability){
  var band = bandFor(probability);
  var pct = Math.round(probability*100);
  return (
    '<div class="score-hero">' +
      '<div class="score-num" style="color:' + bandColor(band) + ';">' + pct + '%</div>' +
      '<div class="score-sub">Alzheimer\'s-related marker match — how closely this sample lines up with speech/motor patterns research has associated with cognitive aging</div>' +
      '<div style="margin-top:10px;"><span class="band-pill ' + bandClass(band) + '">' + bandLabel(band) + '</span></div>' +
    '</div>'
  );
}

/* ---------- speech analysis (adaptive threshold — shared by mic + upload) ---------- */
function computeSpeechMetrics(samples, durationSec){
  var n = samples.length;
  var mean = samples.reduce(function(a,b){return a+b;},0)/n;
  var max = Math.max.apply(null, samples);
  var sorted = samples.slice().sort(function(a,b){return a-b;});
  var noiseFloor = sorted[Math.floor(n*0.15)] || 0;
  var threshold = Math.max(noiseFloor*1.8, mean*0.3, 0.004);
  if(threshold >= max*0.9) threshold = max*0.3;

  var silentFlags = samples.map(function(s){ return s < threshold; });
  var silentCount = silentFlags.filter(Boolean).length;
  var silenceRatio = silentCount/n;
  var speakingRatio = 1 - silenceRatio;
  var variability = computeStdDev(samples);
  var estWordsPerMin = Math.round(70 + speakingRatio*100 - silenceRatio*20);
  estWordsPerMin = Math.max(20, Math.min(220, estWordsPerMin));

  // "Detected pause segments" is meant to represent real hesitations, not
  // just the natural micro-gaps between syllables that show up in every
  // fluent speaker's audio at frame-level sampling. Counting every single
  // below-threshold sample as its own pause massively over-counted pauses
  // for anyone who talks normally. Two fixes: (1) require a dip to last at
  // least ~250ms (the standard acoustic definition of a pause) before it
  // counts, using the sample rate actually used for this recording so it
  // works the same for live mic frames and uploaded-file hops; (2) ignore
  // silence before the first word and after the last word — that's just
  // recording start/stop lag, not a hesitation while speaking.
  var samplesPerSec = durationSec > 0 ? n / durationSec : 0;
  var minPauseSamples = Math.max(2, Math.round(samplesPerSec * 0.25));
  var firstVoiced = silentFlags.indexOf(false);
  var lastVoiced = silentFlags.lastIndexOf(false);

  var pauseCount = 0, run = 0;
  if(firstVoiced !== -1){
    for(var i=firstVoiced;i<=lastVoiced;i++){
      if(silentFlags[i]){
        run++;
      } else {
        if(run >= minPauseSamples) pauseCount++;
        run = 0;
      }
    }
    if(run >= minPauseSamples) pauseCount++;
  }

  return {
    durationSec: durationSec,
    speakingRatio: speakingRatio,
    silenceRatio: silenceRatio,
    estWordsPerMin: estWordsPerMin,
    pauseCount: pauseCount,
    avgVol: mean,
    variability: variability
  };
}
function probabilityFromSpeechMetrics(r){
  // pauseCount now only counts sustained (~250ms+) real pauses instead of
  // every frame-level dip, so it's a much smaller number than before —
  // recalibrated the "worth flagging" cutoff from >12 to >4 to match.
  return clamp01(0.15 + r.silenceRatio*0.35 + (r.pauseCount>4 ? 0.15:0) + (r.estWordsPerMin<90?0.15:0));
}

function speechBreakdownHtml(r, probability){
  return (
    scoreBlockHtml(probability) +
    '<div class="breakdown-grid">' +
      breakdownItem(r.durationSec.toFixed(1)+'s', 'Recording length', 'Total time you spoke for, used to normalize every other marker.') +
      breakdownItem(r.estWordsPerMin+' wpm', 'Estimated speaking rate', 'Slower rates and long word-finding gaps are one of the most replicated markers in cognitive-aging speech research.') +
      breakdownItem((r.speakingRatio*100).toFixed(0)+'%', 'Time spent speaking', 'Share of the recording that had active voice vs. silence.') +
      breakdownItem((r.silenceRatio*100).toFixed(0)+'%', 'Pause / silence ratio', 'Higher ratios can reflect word-finding difficulty or hesitation.') +
      breakdownItem(r.pauseCount, 'Detected pause segments', 'Number of distinct gaps in speech longer than a brief breath.') +
      breakdownItem(r.variability.toFixed(3), 'Vocal energy variability', 'How much your loudness varied — very flat or very erratic patterns are both noted.') +
    '</div>'
  );
}

/* ---------- handwriting analysis ---------- */
function handwritingBreakdownHtml(r, probability, replayId){
  var replayBlock = '';
  if(r.strokes && r.strokes.length && replayId){
    __replayStore[replayId] = r.strokes;
    replayBlock =
      '<div style="text-align:center;margin:0 0 18px;">' +
        '<canvas id="' + replayId + '-canvas" style="width:100%;max-width:500px;height:180px;border-radius:12px;border:1px solid var(--border);background:var(--card);"></canvas>' +
        '<div><button class="btn btn-secondary btn-sm" style="margin-top:10px;" onclick="replayStrokes(\'' + replayId + '-canvas\', __replayStore[\'' + replayId + '\'])">▶ Replay how it was written</button></div>' +
      '</div>';
  }
  return (
    replayBlock +
    scoreBlockHtml(probability) +
    '<div class="breakdown-grid">' +
      breakdownItem(r.totalTimeSec.toFixed(1)+'s', 'Total writing time', 'Time from first touch to last stroke, used to normalize the other markers.') +
      breakdownItem(r.strokeCount, 'Stroke (pen-lift) count', 'How many separate strokes it took — more lifts can reflect more deliberate, effortful writing.') +
      breakdownItem(Math.round(r.avgSpeed)+' px/s', 'Average writing speed', 'Slower, more variable writing speed is one marker researchers associate with motor and cognitive changes.') +
      breakdownItem(r.speedVariability.toFixed(0), 'Speed variability', 'How much your speed sped up and slowed down within strokes.') +
      breakdownItem(r.pauseCount, 'Mid-stroke hesitations', 'Pauses longer than 300ms while writing, a proxy for hesitation.') +
      breakdownItem(r.pointCount, 'Captured data points', 'Raw sample density used to compute every marker above.') +
    '</div>'
  );
}

/* ---------- stroke replay (used by the live test result AND dashboard
   history detail — both call handwritingBreakdownHtml with a unique
   replayId, which stashes the stroke data here for the button to find). */
var __replayStore = {};

function replayStrokes(canvasId, strokes){
  var canvas = document.getElementById(canvasId);
  if(!canvas || !strokes || !strokes.length) return;
  var rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * devicePixelRatio;
  canvas.height = rect.height * devicePixelRatio;
  var ctx = canvas.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(devicePixelRatio, devicePixelRatio);
  var strokeColor = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#3b3a3f';
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2.4;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Fit the original (canvas-pixel) coordinates into whatever size this
  // replay canvas actually is, preserving aspect ratio with a little padding.
  var minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
  strokes.forEach(function(stroke){
    stroke.forEach(function(p){
      if(p[0]<minX) minX=p[0]; if(p[0]>maxX) maxX=p[0];
      if(p[1]<minY) minY=p[1]; if(p[1]>maxY) maxY=p[1];
    });
  });
  var pad = 16;
  var srcW = Math.max(1, maxX-minX), srcH = Math.max(1, maxY-minY);
  var scale = Math.min((rect.width-pad*2)/srcW, (rect.height-pad*2)/srcH);
  var offX = pad + ((rect.width-pad*2) - srcW*scale)/2;
  var offY = pad + ((rect.height-pad*2) - srcH*scale)/2;
  function tx(x){ return offX + (x-minX)*scale; }
  function ty(y){ return offY + (y-minY)*scale; }

  var totalMs = 0;
  strokes.forEach(function(stroke){ if(stroke.length) totalMs = Math.max(totalMs, stroke[stroke.length-1][2]); });
  // Clamp playback to a snappy 0.6–9s regardless of how long the original
  // writing took, so replaying a 45-second sample doesn't take 45 seconds.
  var playbackMs = Math.min(Math.max(totalMs, 600), 9000);
  var speedFactor = totalMs > 0 ? playbackMs/totalMs : 1;

  var startTs = null;
  function frame(ts){
    if(!startTs) startTs = ts;
    var elapsed = (ts - startTs) / speedFactor;
    ctx.clearRect(0, 0, rect.width, rect.height);
    var stillGoing = false;
    strokes.forEach(function(stroke){
      if(!stroke.length) return;
      ctx.beginPath();
      var started = false;
      for(var i=0;i<stroke.length;i++){
        var p = stroke[i];
        if(p[2] > elapsed){ stillGoing = true; break; }
        var x = tx(p[0]), y = ty(p[1]);
        if(!started){ ctx.moveTo(x,y); started = true; } else { ctx.lineTo(x,y); }
      }
      if(started) ctx.stroke();
    });
    if(stillGoing) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ---------- Gemini-powered handwriting photo analysis ----------
   Alternative to the on-screen canvas: the person uploads a photo of
   handwriting on paper, and Gemini's vision model rates a handful of
   visual qualities. This calls Google's API directly from the browser
   with the user's own key — nothing goes through any Verity server
   (there isn't one). The key is saved in localStorage only, purely so
   the person doesn't have to re-paste it every visit. */
var LS_GEMINI_KEY = 'lucida_gemini_key';

function getGeminiKey(){ return safeGet(LS_GEMINI_KEY) || ''; }
function setGeminiKey(key){ safeSet(LS_GEMINI_KEY, key || ''); }

function fileToBase64(file){
  return new Promise(function(resolve, reject){
    var reader = new FileReader();
    reader.onload = function(){
      var result = reader.result; // "data:image/png;base64,AAAA..."
      var base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

var GEMINI_PROMPT =
  'You are looking at a photo that is supposed to contain a short handwritten sentence, as part of ' +
  'a non-clinical screening demo (NOT a diagnosis) that looks at handwriting motor patterns. ' +
  'First, check whether the image actually shows legible handwriting on paper (not typed text, not a ' +
  'blank page, not an unrelated photo, not a screenshot). ' +
  'If it does NOT show real handwriting, set "containsHandwriting" to false, set every numeric field to 0, ' +
  'and explain what you actually saw in "notes". Do not invent scores for an image with no handwriting in it. ' +
  'If it DOES show handwriting, set "containsHandwriting" to true and rate these visual qualities on a ' +
  '0-100 scale (100 = very steady/consistent/typical for a healthy adult, 0 = very irregular), based only ' +
  'on what is visibly in the image: legibility, strokeSteadiness (wavering/tremor in the pen strokes), ' +
  'spacingConsistency (evenness of spacing between letters/words), and letterSizeConsistency (uniformity of ' +
  'letter size). Also include a 0-100 "confidence" reflecting how confident you are in this reading given ' +
  'photo quality, lighting, and angle. ' +
  'Respond with ONLY raw JSON, no markdown fences, no extra commentary, in exactly this shape: ' +
  '{"containsHandwriting":true|false,"confidence":0-100,"legibility":0-100,"strokeSteadiness":0-100,' +
  '"spacingConsistency":0-100,"letterSizeConsistency":0-100,"notes":"one short plain-language sentence describing what you observed"}';

/* Model names Google exposes change over time — gemini-1.5-flash was
   retired and started returning 404 "model not found" for everyone still
   pointing at it. Rather than hardcode one name that will eventually rot
   again, try a short list of current/likely model names in order and
   fall through to the next one specifically on a 404, so the feature
   keeps working across Google's renames without needing a code update
   every time. */
var GEMINI_MODEL_CANDIDATES = [
  'gemini-2.5-flash',
  'gemini-2.0-flash',
  'gemini-2.5-flash-lite',
  'gemini-1.5-flash-latest'
];

/* Calls Gemini's vision model. Returns {ok:true, analysis} or
   {ok:false, reason}. Never throws — every failure path (bad key, no
   network, malformed response) resolves with ok:false so the caller can
   show a clear message instead of a dead button. */
async function analyzeHandwritingPhoto(file, apiKey){
  if(!apiKey) return { ok:false, reason:'Please enter your Gemini API key first.' };
  if(!file) return { ok:false, reason:'Please choose a photo to analyze.' };

  var base64;
  try{
    base64 = await fileToBase64(file);
  }catch(e){
    return { ok:false, reason:"Couldn't read that image file." };
  }

  var body = {
    contents: [{
      parts: [
        { text: GEMINI_PROMPT },
        { inline_data: { mime_type: file.type || 'image/jpeg', data: base64 } }
      ]
    }],
    // response_mime_type forces the API itself to return valid JSON rather
    // than hoping the model obeys "respond with only JSON" in plain text —
    // this is what actually stops "nonsense"/unparsable replies, not the
    // prompt wording alone.
    generationConfig: { temperature: 0.2, response_mime_type: 'application/json' }
  };

  /* 429 (rate limit) and 403 (permission) are per-MODEL, not necessarily
     per-key — a free-tier key can be throttled on one model but fine on
     another. So we now keep trying the remaining candidates on 404, 429,
     AND 403, instead of giving up on the very first rate-limited model.
     We only stop early for things retrying can't fix (a flatly invalid
     key format, or the network being unreachable). A single 429 also
     gets one short backoff-and-retry on the SAME model before moving on,
     since transient rate limits often clear within a second or two. */
  var res, lastStatus, sawRateLimit = false;
  for(var i=0;i<GEMINI_MODEL_CANDIDATES.length;i++){
    var model = GEMINI_MODEL_CANDIDATES[i];
    var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(apiKey);

    for(var attempt=0; attempt<2; attempt++){
      try{
        res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      }catch(e){
        return { ok:false, reason:'Could not reach Gemini — check your internet connection and try again.' };
      }
      if(res.ok || res.status !== 429 || attempt === 1) break;
      sawRateLimit = true;
      await new Promise(function(r){ setTimeout(r, 1500); }); // brief backoff, then one retry on the same model
    }

    if(res.ok) break;
    lastStatus = res.status;
    if(res.status === 429) sawRateLimit = true;
    if(res.status !== 404 && res.status !== 429 && res.status !== 403) break; // a non-retryable error (bad request, etc.)
    res = null; // this model wasn't usable, try the next candidate
  }

  if(!res){
    if(sawRateLimit){
      return { ok:false, reason:"Gemini's free-tier rate limit was hit on every available model. Wait about a minute and try again, or check your quota at aistudio.google.com." };
    }
    return { ok:false, reason:"None of Gemini's current models responded for this API key/region (last status " + lastStatus + "). Your key may not have Gemini API access enabled yet." };
  }
  if(!res.ok){
    var status = res.status;
    if(status === 400) return { ok:false, reason:'Gemini rejected that request. Double-check your API key and try again.' };
    if(status === 429) return { ok:false, reason:"Gemini's rate limit was hit — wait a moment and try again." };
    return { ok:false, reason:'Gemini returned an error (status ' + status + ').' };
  }

  var data;
  try{ data = await res.json(); }catch(e){ return { ok:false, reason:'Got an unreadable response from Gemini.' }; }

  var text = data && data.candidates && data.candidates[0] && data.candidates[0].content &&
             data.candidates[0].content.parts && data.candidates[0].content.parts[0] &&
             data.candidates[0].content.parts[0].text;
  if(!text) return { ok:false, reason:"Gemini didn't return an analysis for that image — try a clearer photo." };

  var cleaned = text.trim().replace(/^```json/i,'').replace(/^```/,'').replace(/```$/,'').trim();
  var parsed;
  try{
    parsed = JSON.parse(cleaned);
  }catch(e){
    // Fallback for the rare case a model ignores response_mime_type and
    // wraps the JSON in extra prose despite the prompt: pull out the
    // outermost {...} block and try again before giving up.
    var start = cleaned.indexOf('{');
    var end = cleaned.lastIndexOf('}');
    if(start !== -1 && end !== -1 && end > start){
      try{ parsed = JSON.parse(cleaned.slice(start, end+1)); }catch(e2){ /* still no good */ }
    }
    if(!parsed) return { ok:false, reason:"Couldn't parse Gemini's response — try again." };
  }

  // Gemini explicitly told us this photo doesn't contain real handwriting —
  // refuse to fabricate a score for it instead of showing a confident-looking
  // but meaningless result.
  if(parsed.containsHandwriting === false){
    return {
      ok:false,
      reason: "That doesn't look like a photo of handwriting" + (parsed.notes ? (' — ' + parsed.notes) : '') + '. Try a clear, well-lit photo of the written sentence.'
    };
  }

  var fields = ['legibility','strokeSteadiness','spacingConsistency','letterSizeConsistency'];
  for(var i=0;i<fields.length;i++){
    var v = parsed[fields[i]];
    if(typeof v !== 'number' || isNaN(v)){
      return { ok:false, reason:'Gemini\'s response was missing expected fields — try again.' };
    }
    parsed[fields[i]] = Math.max(0, Math.min(100, v));
  }
  parsed.notes = typeof parsed.notes === 'string' ? parsed.notes : '';
  parsed.confidence = (typeof parsed.confidence === 'number' && !isNaN(parsed.confidence))
    ? Math.max(0, Math.min(100, parsed.confidence)) : null;

  if(parsed.confidence !== null && parsed.confidence < 40){
    return {
      ok:false,
      reason: "Gemini wasn't confident enough in this photo to give a reliable reading (low confidence due to lighting, angle, or image quality). Try a clearer, well-lit, straight-on photo."
    };
  }

  return { ok:true, analysis: parsed };
}

function probabilityFromGeminiAnalysis(a){
  var avg = (a.legibility + a.strokeSteadiness + a.spacingConsistency + a.letterSizeConsistency) / 4;
  return clamp01(1 - avg/100);
}

function geminiHandwritingBreakdownHtml(a, probability){
  return (
    scoreBlockHtml(probability) +
    '<div class="breakdown-grid">' +
      breakdownItem(Math.round(a.legibility), 'Legibility', 'How clearly formed and readable the letters appear.') +
      breakdownItem(Math.round(a.strokeSteadiness), 'Stroke steadiness', 'How steady vs. wavering/tremorous the pen strokes look.') +
      breakdownItem(Math.round(a.spacingConsistency), 'Spacing consistency', 'How even the spacing is between letters and words.') +
      breakdownItem(Math.round(a.letterSizeConsistency), 'Letter size consistency', 'How uniform letter sizes stay across the sample.') +
      (a.confidence !== null && a.confidence !== undefined
        ? breakdownItem(Math.round(a.confidence)+'%', "Gemini's confidence", 'How confident the model was in this reading, given the photo\'s lighting, angle, and clarity.')
        : '') +
    '</div>' +
    (a.notes ? '<p style="font-size:13px;color:var(--text-soft);margin:0 0 8px;"><strong>Gemini\'s note:</strong> ' + escapeHtml(a.notes) + '</p>' : '')
  );
}

/* ---------- history detail rendering (dashboard row expand) ----------
   Every history entry already stores its full metrics object — the
   dashboard previously only showed the band + percentage in the list.
   This reconstructs the same breakdown shown right after taking the
   test, so past results aren't a dead end. */
function historyDetailHtml(entry){
  if(entry.modality === 'speech') return speechBreakdownHtml(entry.metrics, entry.probability);
  if(entry.modality === 'handwriting' && entry.source === 'gemini-photo') return geminiHandwritingBreakdownHtml(entry.metrics, entry.probability);
  if(entry.modality === 'handwriting') return handwritingBreakdownHtml(entry.metrics, entry.probability, 'hist-' + entry.id);
  return scoreBlockHtml(entry.probability);
}

function historyToCsv(history){
  var header = ['date','modality','source','score_percent','band'];
  var lines = [header.join(',')];
  history.forEach(function(h){
    var row = [
      new Date(h.timestamp).toISOString(),
      h.modality,
      h.source || (h.modality === 'handwriting' ? 'canvas' : 'microphone'),
      Math.round(h.probability*100),
      h.band
    ].map(function(v){
      var s = String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
    });
    lines.push(row.join(','));
  });
  return lines.join('\n');
}

/* ---------- generic 2FA (reused on signup) ---------- */
var pendingSignupCode = null;

/* Surface any uncaught script error as a visible banner instead of a
   silently dead button — makes it obvious when something (like a missing
   sibling file) broke, rather than looking like nothing happened. */
window.addEventListener('error', function(e){
  if(document.getElementById('lucida-error-banner')) return;
  var banner = document.createElement('div');
  banner.id = 'lucida-error-banner';
  banner.style.cssText = 'position:fixed;bottom:16px;left:16px;right:16px;max-width:520px;margin:0 auto;background:#f6d4cd;color:#7a3527;padding:14px 18px;border-radius:12px;font-size:13px;z-index:999;box-shadow:0 4px 20px rgba(0,0,0,0.15);';
  banner.textContent = 'Something on this page didn\'t load correctly (' + (e.message || 'script error') + '). Try reopening this file from the same folder as its other Verity files, or reload the page.';
  document.body.appendChild(banner);
});

document.addEventListener('DOMContentLoaded', renderNavUser);

/* ---------- scroll reveal (Apple.com-style fade/rise on scroll) ----------
   Auto-tags the common content blocks on every page with .reveal, adds a
   slight stagger between siblings so groups of cards cascade in rather
   than popping simultaneously, then flips each one to .in-view the first
   time it scrolls into the viewport. No per-page markup needed — new
   pages/sections pick this up automatically as long as they use these
   existing classes. */
document.addEventListener('DOMContentLoaded', function(){
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if(!('IntersectionObserver' in window)) return;

  var selector = [
    '.hero h1', '.hero p', '.hero-actions',
    '.step-card', '.test-card', '.marker-card',
    '.disclaimer', '.pricing-card', '.auth-card',
    '.runner-card', '.dash-stat', '.chart-card', '.history-card',
    '.section-title', '.page-header h1', '.page-header p',
    '.empty-state', '.feature-card', '.clip-tabs', '.stat-counter'
  ].join(',');

  document.querySelectorAll(selector).forEach(function(el){
    el.classList.add('reveal');
  });

  // Stagger siblings inside the same grid/container (e.g. three step-cards
  // land one after another instead of all at once).
  var containers = document.querySelectorAll('.steps, .test-grid, .markers, .dash-grid, .features-grid, .counters-row');
  containers.forEach(function(container){
    Array.from(container.children).forEach(function(child, i){
      child.style.transitionDelay = (i * 90) + 'ms';
    });
  });

  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting){
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(function(el){ observer.observe(el); });
});

/* ---------- magnetic buttons (site-wide) ----------
   Any element with .magnetic-btn gently pulls toward the cursor within a
   small radius. Auto-applies here so every page's CTA buttons get it, not
   just the ones on the landing page. */
document.addEventListener('DOMContentLoaded', function(){
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var range = 60, intensity = 0.35;
  document.querySelectorAll('.magnetic-btn').forEach(function(btn){
    btn.addEventListener('mousemove', function(e){
      var r = btn.getBoundingClientRect();
      var dx = e.clientX - (r.left + r.width/2);
      var dy = e.clientY - (r.top + r.height/2);
      var dist = Math.sqrt(dx*dx + dy*dy);
      if(dist < range){
        btn.style.transform = 'translate(' + (dx*intensity).toFixed(1) + 'px,' + (dy*intensity).toFixed(1) + 'px)';
      }
    });
    btn.addEventListener('mouseleave', function(){ btn.style.transform = ''; });
  });
});

/* ---------- tilt cards (site-wide) ----------
   Any element with .tilt-card does a subtle 3D tilt following the cursor,
   applied to test/feature/marker/step cards for a bit of depth. */
document.addEventListener('DOMContentLoaded', function(){
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if(window.matchMedia && window.matchMedia('(hover: none)').matches) return; // skip on touch
  document.querySelectorAll('.tilt-card').forEach(function(card){
    card.style.transformStyle = 'preserve-3d';
    card.style.willChange = 'transform';
    card.addEventListener('mousemove', function(e){
      var r = card.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width - 0.5;
      var py = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = 'perspective(600px) rotateX(' + (-py*6).toFixed(2) + 'deg) rotateY(' + (px*6).toFixed(2) + 'deg) translateZ(2px)';
    });
    card.addEventListener('mouseleave', function(){
      card.style.transform = '';
    });
  });
});

/* ---------- reusable typewriter effect (site-wide) ----------
   Types the given text into an element one character at a time. Pulled out
   of the per-page inline scripts so every page can use it the same way:
   <p id="foo" data-typewriter="Some text"></p> and it runs automatically
   on load, or call typewriterInto(el, text) directly. */
function typewriterInto(el, text, speed){
  if(!el) return;
  speed = speed || 28;
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    el.textContent = text;
    return;
  }
  var i = 0;
  function tick(){
    el.textContent = text.slice(0, i) + (i < text.length ? '▌' : '');
    i++;
    if(i <= text.length) setTimeout(tick, speed);
  }
  tick();
}
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('[data-typewriter]').forEach(function(el){
    typewriterInto(el, el.getAttribute('data-typewriter'));
  });
});

/* ---------- toast notifications (site-wide) ----------
   Small dismissable pill in the bottom-left, used instead of alert() for
   lightweight confirmations like "Copied" or "Exported". */
function showToast(message){
  var existing = document.getElementById('toast-stack');
  var stack = existing || document.createElement('div');
  if(!existing){
    stack.id = 'toast-stack';
    stack.style.cssText = 'position:fixed;left:22px;bottom:22px;display:flex;flex-direction:column;gap:8px;z-index:90;';
    document.body.appendChild(stack);
  }
  var toast = document.createElement('div');
  toast.className = 'toast-pill';
  toast.textContent = message;
  stack.appendChild(toast);
  setTimeout(function(){
    toast.classList.add('toast-out');
    setTimeout(function(){ toast.remove(); }, 300);
  }, 2400);
}

/* ---------- button ripple (site-wide) ----------
   A small material-style ripple on .btn clicks — purely visual feedback,
   doesn't interfere with the button's own onclick handler. */
document.addEventListener('DOMContentLoaded', function(){
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.addEventListener('click', function(e){
    var btn = e.target.closest && e.target.closest('.btn');
    if(!btn) return;
    var rect = btn.getBoundingClientRect();
    var ripple = document.createElement('span');
    var size = Math.max(rect.width, rect.height);
    ripple.className = 'btn-ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size/2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size/2) + 'px';
    var prevPosition = getComputedStyle(btn).position;
    if(prevPosition === 'static') btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(function(){ ripple.remove(); }, 600);
  });
});

/* ---------- Konami code easter egg (site-wide) ----------
   ↑ ↑ ↓ ↓ ← → ← → B A — a small nod for anyone who tries it. */
document.addEventListener('DOMContentLoaded', function(){
  var sequence = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  var pos = 0;
  document.addEventListener('keydown', function(e){
    var key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if(key === sequence[pos]){
      pos++;
      if(pos === sequence.length){
        pos = 0;
        celebrateTypicalResult();
        showToast('✨ You found the secret. No hidden diagnosis here either — still just a screening tool.');
      }
    } else {
      pos = (key === sequence[0]) ? 1 : 0;
    }
  });
});

/* ---------- celebratory confetti for "typical" results ----------
   Small, tasteful — a couple dozen pieces that fall and fade, meant as
   light positive reinforcement, never shown for "some"/"several" bands. */
function celebrateTypicalResult(){
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var colors = ['#7fb3d5', '#8fcbb2', '#b3a2dc', '#f3c98a'];
  var container = document.createElement('div');
  container.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:80;overflow:hidden;';
  document.body.appendChild(container);
  var n = 28;
  for(var i=0;i<n;i++){
    var piece = document.createElement('div');
    var size = 6 + Math.random()*5;
    var left = Math.random()*100;
    var delay = Math.random()*300;
    var duration = 1600 + Math.random()*900;
    var color = colors[i % colors.length];
    piece.style.cssText =
      'position:absolute;top:-20px;left:' + left + '%;width:' + size + 'px;height:' + (size*0.4) + 'px;' +
      'background:' + color + ';opacity:0.9;border-radius:2px;' +
      'transform:rotate(' + Math.floor(Math.random()*360) + 'deg);' +
      'animation:confetti-fall ' + duration + 'ms ease-in ' + delay + 'ms forwards;';
    container.appendChild(piece);
  }
  setTimeout(function(){ container.remove(); }, 3200);
}

/* ---------- back-to-top button (site-wide) ----------
   Shows once you've scrolled past the fold, scrolls smoothly back up. */
document.addEventListener('DOMContentLoaded', function(){
  var btn = document.createElement('button');
  btn.id = 'back-to-top';
  btn.setAttribute('aria-label', 'Back to top');
  btn.textContent = '↑';
  document.body.appendChild(btn);
  window.addEventListener('scroll', function(){
    btn.classList.toggle('show', window.scrollY > 600);
  });
  btn.addEventListener('click', function(){
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
