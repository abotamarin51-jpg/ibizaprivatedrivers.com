(function () {
  'use strict';

  var CONSENT_KEY = 'ipd_google_consent_v1';

  function getConsentChoice() {
    try {
      return window.localStorage.getItem(CONSENT_KEY);
    } catch (error) {
      return null;
    }
  }

  function setConsentChoice(choice) {
    try {
      window.localStorage.setItem(CONSENT_KEY, choice);
    } catch (error) {
      // Consent still applies for the current page if storage is unavailable.
    }
  }

  function updateConsent(choice) {
    if (typeof window.gtag !== 'function') return;

    window.gtag('consent', 'update', {
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      analytics_storage: choice === 'granted' ? 'granted' : 'denied'
    });
  }

  function copyForLanguage() {
    var lang = (document.documentElement.lang || 'en').toLowerCase();

    if (lang.indexOf('es') === 0) {
      return {
        text: 'Usamos Google Analytics únicamente con tu permiso para medir visitas y solicitudes de reserva.',
        accept: 'Aceptar Analytics',
        reject: 'Solo esenciales',
        privacy: 'Privacidad'
      };
    }

    if (lang.indexOf('fr') === 0) {
      return {
        text: 'Nous utilisons Google Analytics uniquement avec votre accord afin de mesurer les visites et les demandes de réservation.',
        accept: 'Accepter Analytics',
        reject: 'Essentiels uniquement',
        privacy: 'Confidentialité'
      };
    }

    if (lang.indexOf('de') === 0) {
      return {
        text: 'Wir verwenden Google Analytics nur mit Ihrer Zustimmung, um Besuche und Buchungsanfragen zu messen.',
        accept: 'Analytics akzeptieren',
        reject: 'Nur notwendige',
        privacy: 'Datenschutz'
      };
    }

    if (lang.indexOf('ar') === 0) {
      return {
        text: 'نستخدم Google Analytics فقط بموافقتك لقياس الزيارات وطلبات الحجز.',
        accept: 'قبول Analytics',
        reject: 'الضروري فقط',
        privacy: 'الخصوصية'
      };
    }

    return {
      text: 'We use Google Analytics only with your permission to measure visits and booking enquiries.',
      accept: 'Accept analytics',
      reject: 'Essential only',
      privacy: 'Privacy'
    };
  }

  function addConsentBanner() {
    if (getConsentChoice() || document.getElementById('ipd-consent')) return;

    var copy = copyForLanguage();
    var banner = document.createElement('aside');
    banner.id = 'ipd-consent';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Analytics consent');
    banner.innerHTML =
      '<p>' + copy.text + ' <a href="/privacy/">' + copy.privacy + '</a></p>' +
      '<div class="ipd-consent-actions">' +
        '<button type="button" data-consent="denied">' + copy.reject + '</button>' +
        '<button type="button" class="ipd-consent-accept" data-consent="granted">' + copy.accept + '</button>' +
      '</div>';

    var style = document.createElement('style');
    style.textContent =
      '#ipd-consent{position:fixed;z-index:2147483647;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;padding:18px 20px;background:#111;color:#fff;border:1px solid rgba(255,255,255,.22);border-radius:14px;box-shadow:0 14px 44px rgba(0,0,0,.35);font:14px/1.45 Inter,Arial,sans-serif;display:flex;align-items:center;justify-content:space-between;gap:18px}' +
      '#ipd-consent p{margin:0;max-width:470px}' +
      '#ipd-consent a{color:#fff;text-decoration:underline}' +
      '.ipd-consent-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}' +
      '#ipd-consent button{border:1px solid rgba(255,255,255,.45);border-radius:999px;padding:10px 14px;background:transparent;color:#fff;font:inherit;cursor:pointer;white-space:nowrap}' +
      '#ipd-consent .ipd-consent-accept{background:#fff;color:#111;border-color:#fff}' +
      '@media(max-width:640px){#ipd-consent{align-items:stretch;flex-direction:column;padding:16px}.ipd-consent-actions{justify-content:stretch}.ipd-consent button{flex:1}}';

    document.head.appendChild(style);
    document.body.appendChild(banner);

    banner.addEventListener('click', function (event) {
      var button = event.target.closest('button[data-consent]');
      if (!button) return;

      var choice = button.getAttribute('data-consent');
      setConsentChoice(choice);
      updateConsent(choice);

      if (choice === 'granted' && typeof window.gtag === 'function') {
        window.gtag('event', 'page_view', {
          page_location: window.location.href,
          page_title: document.title
        });
      }

      banner.remove();
      style.remove();
    });
  }

  function trackLeadClick(link) {
    if (getConsentChoice() !== 'granted' || typeof window.gtag !== 'function') return;

    var rawHref = link.getAttribute('href') || '';
    var href = rawHref.toLowerCase();
    var eventName = '';
    var leadType = '';

    if (href.indexOf('wa.me/') !== -1 || href.indexOf('api.whatsapp.com/') !== -1 || href.indexOf('whatsapp://') === 0) {
      eventName = 'whatsapp_click';
      leadType = 'whatsapp';
    } else if (href.indexOf('tel:') === 0) {
      eventName = 'phone_click';
      leadType = 'phone';
    } else if (href.indexOf('mailto:') === 0) {
      eventName = 'email_click';
      leadType = 'email';
    }

    if (!eventName) return;

    window.gtag('event', eventName, {
      event_category: 'lead',
      lead_type: leadType,
      link_url: link.href,
      page_path: window.location.pathname,
      transport_type: 'beacon'
    });

    window.gtag('event', 'generate_lead', {
      currency: 'EUR',
      value: 0,
      lead_type: leadType,
      page_path: window.location.pathname,
      transport_type: 'beacon'
    });
  }

  document.addEventListener('click', function (event) {
    var reset = event.target.closest('[data-reset-consent]');
    if (reset) {
      event.preventDefault();
      try {
        window.localStorage.removeItem(CONSENT_KEY);
      } catch (error) {}
      updateConsent('denied');
      window.location.reload();
      return;
    }

    var link = event.target.closest('a[href]');
    if (link) trackLeadClick(link);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addConsentBanner);
  } else {
    addConsentBanner();
  }
})();
