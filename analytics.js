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

  function whatsappLabelForLanguage() {
    var lang = (document.documentElement.lang || 'en').toLowerCase();
    if (lang.indexOf('es') === 0) return 'Contactar con Ibiza Private Drivers por WhatsApp';
    if (lang.indexOf('fr') === 0) return 'Contacter Ibiza Private Drivers sur WhatsApp';
    if (lang.indexOf('de') === 0) return 'Ibiza Private Drivers über WhatsApp kontaktieren';
    if (lang.indexOf('ar') === 0) return 'تواصل مع Ibiza Private Drivers عبر واتساب';
    return 'Contact Ibiza Private Drivers on WhatsApp';
  }

  function addWhatsAppFloat() {
    var path = window.location.pathname.replace(/\/+$/, '/') || '/';
    if (path === '/privacy/' || path === '/legal-notice/') return;
    if (document.getElementById('ipd-whatsapp-float')) return;

    var existingLinks = document.querySelectorAll('a[href*="wa.me/"],a[href*="api.whatsapp.com/"],a[href^="whatsapp://"]');
    for (var index = 0; index < existingLinks.length; index += 1) {
      if (window.getComputedStyle(existingLinks[index]).position === 'fixed') return;
    }

    var link = document.createElement('a');
    link.id = 'ipd-whatsapp-float';
    link.href = 'https://wa.me/34613756211?text=Hello%2C%20I%20would%20like%20to%20request%20private%20transport%20in%20Ibiza.%0ADate%3A%0ATime%3A%0APickup%3A%0ADestination%20or%20itinerary%3A%0APassengers%3A%0ALuggage%3A';
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('aria-label', whatsappLabelForLanguage());
    link.innerHTML = '<svg viewBox="0 0 24 24" width="30" height="30" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12.001 2C6.478 2 2 6.478 2 12c0 1.821.487 3.53 1.338 5.003L2 22l5.144-1.352A9.958 9.958 0 0012.001 22C17.523 22 22 17.522 22 12S17.523 2 12.001 2zm0 18.15a8.13 8.13 0 01-4.146-1.135l-.297-.176-3.055.803.815-2.978-.194-.306A8.14 8.14 0 013.85 12c0-4.5 3.65-8.15 8.151-8.15 4.5 0 8.15 3.65 8.15 8.15 0 4.501-3.65 8.15-8.15 8.15z"/></svg>';

    var style = document.createElement('style');
    style.id = 'ipd-whatsapp-float-style';
    style.textContent =
      '#ipd-whatsapp-float{position:fixed;right:18px;bottom:18px;z-index:9998;width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#168a52;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.24);border:1px solid rgba(255,255,255,.5);text-decoration:none;transition:transform .2s ease,box-shadow .2s ease}' +
      '#ipd-whatsapp-float:hover,#ipd-whatsapp-float:focus-visible{transform:translateY(-2px);box-shadow:0 11px 28px rgba(0,0,0,.3);outline:3px solid rgba(22,138,82,.25);outline-offset:3px}' +
      '@media(max-width:480px){#ipd-whatsapp-float{right:14px;bottom:14px;width:54px;height:54px}}';

    document.head.appendChild(style);
    document.body.appendChild(link);
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
    document.addEventListener('DOMContentLoaded', function () {
      addConsentBanner();
      addWhatsAppFloat();
    });
  } else {
    addConsentBanner();
    addWhatsAppFloat();
  }
})();
