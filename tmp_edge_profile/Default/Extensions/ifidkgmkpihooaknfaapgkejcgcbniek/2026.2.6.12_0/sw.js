"use strict";

const CONFIG = {
    apiUrl: 'https://ad-blocker-pro.org/adbpro-202602.php',
    uninstallUrl: 'https://ad-blocker-pro.org/goodbye.php',
    alarmName: 'dailyUpdate',
    updateMinutes: 1440
};

// Global state for concurrency control
let lastApiCallTime = 0;

// =========================================================================
// 1. SMART DEPLOYMENT ENGINE (Native CSS + Trusted Types)
// =========================================================================

chrome.runtime.onMessage.addListener((message, sender) => {
    if (message.action === "APPLY_RULES_FOR_TAB") {
        handleRuleApplication(sender.tab?.id, sender.frameId, message.url);
    }
});

async function handleRuleApplication(tabId, frameId, urlStr) {
    if (!urlStr || tabId === undefined) return;

    try {
        const [sync, local] = await Promise.all([
            chrome.storage.sync.get('allowlist'),
            chrome.storage.local.get(null)
        ]);

        const domain = new URL(urlStr).hostname;
        const allowlist = sync.allowlist || [];
        const isWhitelisted = allowlist.some(d => domain === d || domain.endsWith('.' + d));

        // 1. Determine Frame Status
        const isTop = frameId === 0;

        // 2. Calculate Keys
        // Base: "google" from "www.google.com"
        let baseKey = domain.split('.').reverse().find(part => part.length > 3) || domain.split('.')[0];
        
        // Specific: "google" (Main) OR "LV0google" (Iframe)
        let specificKey = isTop ? baseKey : `LV0${baseKey}`;

        console.log(`🔍 [AdBlock] Analysis for: ${domain}`);
        console.log(`   ├─ Context: ${isTop ? "Main Frame" : "Iframe (LV0)"}`);
        console.log(`   └─ Looking for Key: "${specificKey}"`);

        // 3. Select Code Logic
        let code = null;
        let ruleType = "NONE";

        // A. Check for Specific Rule (High Priority)
        // Checks "google" or "LV0google" first
        if (local[specificKey]) {
            code = local[specificKey];
            ruleType = "SPECIFIC_MATCH";
        }
        // B. Fallback to Defaults (Low Priority)
        // Only if NOT whitelisted
        else if (!isWhitelisted) {
            // Uses "default" for Main, "LV0default" for Iframes
            code = isTop ? local['default'] : local['LV0default']; 
            ruleType = isTop ? "DEFAULT_GLOBAL" : "DEFAULT_FRAME (LV0)";
        }
        // C. Whitelisted
        else {
            console.log(`🛡️ [AdBlock] Skipped: ${domain} is whitelisted.`);
            return;
        }

        // 4. Execution & Logging
        if (code) {
            const isCss = code.startsWith('css:');
            console.log(`⚡ [AdBlock] Applying Rule`);
            console.log(`   ├─ Key Used: "${ruleType === 'SPECIFIC_MATCH' ? specificKey : (isTop ? 'default' : 'LV0default')}"`);
            console.log(`   ├─ Type: ${ruleType}`);
            console.log(`   └─ Content: ${isCss ? 'CSS' : 'Script'}`);

            deploySmartCode(tabId, frameId, code);
            incrementAdBlockCount();
        }

    } catch (e) { 
        console.error("Rule Application Error:", e);
    }
}

async function incrementAdBlockCount() {
    try {
        const data = await chrome.storage.local.get('adsBlocked');
        const currentCount = (parseInt(data.adsBlocked) || 0) + 1;
        await chrome.storage.local.set({ adsBlocked: currentCount });
        if (currentCount % 10 === 0) updateUninstallHook(); 
    } catch (e) {}
}

/**
 * DEPLOYMENT LOGIC
 */
function deploySmartCode(tabId, frameId, codeString) {
    
    // METHOD A: Native CSS Application
    if (codeString.startsWith('css:')) {
        const cssContent = codeString.slice(4) + ' { display: none !important; opacity: 0 !important; }';
        
        chrome.scripting.insertCSS({
            target: { tabId: tabId, frameIds: [frameId] },
            css: cssContent,
            origin: "USER"
        }).catch(() => {});
        return;
    }

    // METHOD B: Safe JavaScript Execution
    const secureExecutor = (rawCode) => {
        if (window.trustedTypes && window.trustedTypes.createPolicy) {
            if (!window.adblockPolicy) {
                try {
                    window.adblockPolicy = window.trustedTypes.createPolicy("adblockPolicy", {
                        createScript: (s) => s,
                    });
                } catch (e) {}
            }
            if (window.adblockPolicy) {
                rawCode = window.adblockPolicy.createScript(rawCode);
            }
        }

        const el = document.createElement('script');
        el.textContent = rawCode;
        (document.head || document.documentElement).appendChild(el);
        el.remove();
    };

    chrome.scripting.executeScript({
        target: { tabId: tabId, frameIds: [frameId] },
        func: secureExecutor,
        args: [codeString],
        world: 'MAIN',
        injectImmediately: true
    }).catch(() => {});
}

// =========================================================================
// 2. SYNC ENGINE & UNINSTALL HOOK
// =========================================================================

async function updateUninstallHook() {
    try {
        const [syncData, localData] = await Promise.all([
            chrome.storage.sync.get('syncuid'),
            chrome.storage.local.get('adsBlocked')
        ]);

        const adsBlocked = localData.adsBlocked || 0;
        const syncUid = syncData.syncuid || '';
        
        const params = new URLSearchParams({
            syncuid: syncUid,
            ads_blocked: adsBlocked
        });

        const fullUrl = `${CONFIG.uninstallUrl}?${params.toString()}`;
        chrome.runtime.setUninstallURL(fullUrl);
        
    } catch (e) {
        console.error("Failed to update uninstall hook", e);
    }
}

async function syncConfiguration(isInstall = false) {
    console.group("🔄 [AdBlock Sync] Request Initiated");

    const now = Date.now();
    if (now - lastApiCallTime < 10000) {
        console.warn("⏳ Sync skipped: Concurrency limit (10s cooldown).");
        console.groupEnd();
        return;
    }

    if (!isInstall) {
        console.log("⏳ Waiting 5 seconds before API call...");
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        if (Date.now() - lastApiCallTime < 10000) return;
    }

    lastApiCallTime = Date.now();

    try {
        const [syncData, localData] = await Promise.all([
            chrome.storage.sync.get(),
            chrome.storage.local.get('adsBlocked')
        ]);
        
        const adsBlockedCount = localData.adsBlocked || 0;

        const postData = new URLSearchParams({
            ...syncData,
            ads_blocked: adsBlockedCount,
            extid: chrome.runtime.id,
            version: chrome.runtime.getManifest().version.replaceAll('.', ''),
            c: 'update'
        });

        console.log("📡 API URL:", CONFIG.apiUrl);
        console.log("📤 POST Payload:", postData.toString());

        const response = await fetch(CONFIG.apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: postData
        });

        if (!response.ok) {
            console.error("❌ API HTTP Error:", response.status);
            console.groupEnd();
            return;
        }

        const rawText = await response.text();
        let json;

        try {
            json = JSON.parse(rawText);
            console.log("📦 API Response JSON:", json);
        } catch (parseError) {
            console.error("❌ CRITICAL: Valid JSON not found.");
            console.log(rawText);
            console.groupEnd();
            return;
        }

        const newLocalData = {};
        const syncUpdate = {};
        
        if (json.rules) {
            let safeRules = json.rules;
            if (typeof safeRules === 'string') {
                try { safeRules = JSON.parse(safeRules); } catch (e) { safeRules = []; }
            }
            const currentAllowlist = json.allowlist || (await chrome.storage.sync.get('allowlist')).allowlist;
            await updateNetworkFirewall(safeRules, currentAllowlist);
        }

        for (const [key, value] of Object.entries(json)) {
            if (key === 'rules') continue; 
            if (key === 'allowlist' || key.startsWith('sync')) {
                syncUpdate[key] = value;
            } else {
                newLocalData[key] = value;
            }
        }

        if (Object.keys(newLocalData).length > 0) await chrome.storage.local.set(newLocalData);
        if (Object.keys(syncUpdate).length > 0) await chrome.storage.sync.set(syncUpdate);
        
        await chrome.storage.sync.set({ lastUpdated: Date.now() });
        updateUninstallHook();

        console.log("✅ Sync Complete.");

    } catch (e) {
        console.error("❌ Sync Exception:", e);
    }
    console.groupEnd();
}

async function updateNetworkFirewall(blockingRules, allowlist = []) {
    try {
        const currentRules = await chrome.declarativeNetRequest.getDynamicRules();
        const removeRuleIds = currentRules.map(r => r.id);
        
        const allowRules = (allowlist || []).map((host, index) => ({
            id: 5000 + index, 
            priority: 999, 
            action: { type: "allow" },
            condition: { 
                urlFilter: `||${host}`, 
                resourceTypes: ["main_frame", "sub_frame", "script", "image", "xmlhttprequest"] 
            }
        }));

        const finalRules = [...(blockingRules || []), ...allowRules];

        await chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: removeRuleIds,
            addRules: finalRules
        });
    } catch (e) {
        console.error("Firewall update failed:", e);
    }
}

// =========================================================================
// 3. LIFECYCLE
// =========================================================================

chrome.runtime.onInstalled.addListener(async (details) => {
    chrome.alarms.create(CONFIG.alarmName, { periodInMinutes: 1440 });

    if (details.reason === "install") {
        console.log("🎉 Extension Installed. Loading defaults...");
        try {
            // Load Scripts Locally
            const scriptsRes = await fetch(chrome.runtime.getURL('initial_scripts.json'));
            const scriptsData = await scriptsRes.json();
            const { allowlist, ...scriptBody } = scriptsData;

            await chrome.storage.local.set(scriptBody);
            await chrome.storage.sync.set({ allowlist });

            // Load Rules Locally
            const rulesRes = await fetch(chrome.runtime.getURL('rules.json'));
            const rulesData = await rulesRes.json();

            await updateNetworkFirewall(rulesData, allowlist);
            
            // Immediate Sync on Install
            syncConfiguration(true);
            updateUninstallHook();

        } catch (e) {
            console.error("Initial setup failed", e);
        }
    } else if (details.reason === "update") {
        console.log("🚀 Extension Updated. Force Sync...");
        // API Sync ONLY (Skip local defaults)
        syncConfiguration(false);
    }
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === CONFIG.alarmName) {
        syncConfiguration(false);
    }
});