// ═══════════════════════════════════════════════════════
//  LIVESTREAM FELIX — PWA INSTALLER
//  Handles: Install prompt, Service Worker, Notifications
// ═══════════════════════════════════════════════════════

(function () {
  'use strict';

  let deferredPrompt = null;
  let swRegistration = null;

  // ── Register Service Worker ────────────────────────────
  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      console.log('[PWA] Service workers not supported');
      return;
    }

    try {
      swRegistration = await navigator.serviceWorker.register('/static/js/sw.js', {
        scope: '/',
      });

      console.log('[PWA] Service Worker registered:', swRegistration.scope);

      // Check for updates
      swRegistration.addEventListener('updatefound', () => {
        const newWorker = swRegistration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            showUpdateBanner();
          }
        });
      });

    } catch (err) {
      console.log('[PWA] Service Worker registration failed:', err);
    }
  }

  // ── Install Prompt ─────────────────────────────────────
  window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    hideInstallBanner();
    showToast('LiveStream Felix installed successfully! 🎉', 'success');
    console.log('[PWA] App installed');
  });

  function showInstallBanner() {
    // Don't show if already installed or dismissed recently
    if (localStorage.getItem('lsf-install-dismissed')) return;
    if (window.matchMedia('(display-mode: standalone)').matches) return;

    const banner = document.getElementById('installBanner');
    if (banner) {
      banner.style.display = 'flex';
      setTimeout(() => banner.style.opacity = '1', 100);
    }
  }

  function hideInstallBanner() {
    const banner = document.getElementById('installBanner');
    if (banner) {
      banner.style.opacity = '0';
      setTimeout(() => banner.style.display = 'none', 300);
    }
  }

  // Global install trigger
  window.triggerInstall = async function () {
    if (!deferredPrompt) {
      showToast('To install: tap your browser menu → "Add to Home Screen"', 'info');
      return;
    }
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log('[PWA] Install outcome:', outcome);
    deferredPrompt = null;
    hideInstallBanner();
  };

  window.dismissInstall = function () {
    hideInstallBanner();
    localStorage.setItem('lsf-install-dismissed', Date.now());
  };

  // ── Update Banner ──────────────────────────────────────
  function showUpdateBanner() {
    const el = document.createElement('div');
    el.id = 'updateBanner';
    el.innerHTML = `
      <div style="position:fixed;bottom:80px;left:50%;transform:translateX(-50%);
        background:#1a2540;border:1px solid #5b6ef5;border-radius:12px;
        padding:14px 20px;display:flex;align-items:center;gap:12px;
        z-index:9999;box-shadow:0 8px 40px rgba(0,0,0,0.5);min-width:280px;">
        <i class="fa-solid fa-rotate" style="color:#5b6ef5;font-size:18px;"></i>
        <div style="flex:1;">
          <div style="font-size:13px;font-weight:600;color:#eef2ff;">Update Available!</div>
          <div style="font-size:11px;color:#a8b4d8;">A new version of LiveStream Felix is ready</div>
        </div>
        <button onclick="window.location.reload()" style="background:#5b6ef5;color:white;border:none;
          border-radius:6px;padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;">
          Update
        </button>
      </div>
    `;
    document.body.appendChild(el);
  }

  // ── Push Notifications ─────────────────────────────────
  window.requestNotificationPermission = async function () {
    if (!('Notification' in window)) {
      showToast('Notifications not supported on this device', 'info');
      return;
    }

    if (Notification.permission === 'granted') {
      showToast('Notifications already enabled ✓', 'success');
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      showToast('Notifications enabled! 🔔', 'success');
      subscribeToPush();
    } else {
      showToast('Notifications blocked. Enable in browser settings.', 'info');
    }
  };

  async function subscribeToPush() {
    if (!swRegistration) return;
    try {
      const subscription = await swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(
          window.VAPID_PUBLIC_KEY || ''
        ),
      });
      console.log('[PWA] Push subscription:', subscription);
      // Send subscription to server
      // await fetch('/billing/push/subscribe/', { method: 'POST', body: JSON.stringify(subscription) });
    } catch (err) {
      console.log('[PWA] Push subscription failed:', err);
    }
  }

  // ── Online/Offline Detection ───────────────────────────
  window.addEventListener('online', () => {
    showToast('Back online! 🌐', 'success');
    document.body.classList.remove('lsf-offline');
  });

  window.addEventListener('offline', () => {
    showToast('You are offline. Some features may not work.', 'error');
    document.body.classList.add('lsf-offline');
  });

  // ── Check if running as installed PWA ─────────────────
  function checkPWAMode() {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches
      || window.navigator.standalone === true;

    if (isStandalone) {
      document.body.classList.add('pwa-mode');
      console.log('[PWA] Running as installed app');
    }
  }

  // ── Utility ────────────────────────────────────────────
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return new Uint8Array([...rawData].map(c => c.charCodeAt(0)));
  }

  // ── Init ───────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    registerServiceWorker();
    checkPWAMode();
  });

})();
