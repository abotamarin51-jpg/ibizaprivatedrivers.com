(function () {
  'use strict';

  function redirectLegacyPostUrl() {
    if (window.location.pathname !== '/') return false;
    var params = new URLSearchParams(window.location.search);
    var post = params.get('post');
    if (!post) return false;

    var legacyTargets = {
      'private-driver-ibiza-nightlife': '/blog/ibiza-nightlife-guide-2026/',
      'private-airport-pickup-ibiza': '/airport-transfers/',
      'private-transfer-ibiza-to-villa': '/villa-transfers/',
      'explore-ibiza-without-driving-private-driver': '/blog/explore-ibiza-without-driving-private-driver/'
    };

    if (!legacyTargets[post]) return false;
    window.location.replace(legacyTargets[post]);
    return true;
  }

  if (redirectLegacyPostUrl()) return;

  var CONSENT_KEY = 'ipd_google_consent_v1';

  function removeSoroFeed() {
    var feed = document.getElementById('soro-blog');
    if (feed) feed.remove();

    document.querySelectorAll('script[src*="app.trysoro.com/api/embed"]').forEach(function (script) {
      script.remove();
    });
  }

  // analytics.js is a deferred head script and runs before the deferred Soro embed.
  // Remove the homepage feed before it can inject unrelated multilingual articles.
  removeSoroFeed();

  if (document.body && window.MutationObserver) {
    var soroObserver = new MutationObserver(function () {
      var feed = document.getElementById('soro-blog');
      var scripts = document.querySelectorAll('script[src*="app.trysoro.com/api/embed"]');
      if (feed || scripts.length) removeSoroFeed();
    });
    soroObserver.observe(document.documentElement, {childList: true, subtree: true});
    window.setTimeout(function () { soroObserver.disconnect(); }, 5000);
  }

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
    } catch (error) {}
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
      return {text:'Usamos Google Analytics únicamente con tu permiso para medir visitas y solicitudes de reserva.',accept:'Aceptar Analytics',reject:'Solo esenciales',privacy:'Privacidad'};
    }
    if (lang.indexOf('fr') === 0) {
      return {text:'Nous utilisons Google Analytics uniquement avec votre accord afin de mesurer les visites et les demandes de réservation.',accept:'Accepter Analytics',reject:'Essentiels uniquement',privacy:'Confidentialité'};
    }
    if (lang.indexOf('de') === 0) {
      return {text:'Wir verwenden Google Analytics nur mit Ihrer Zustimmung, um Besuche und Buchungsanfragen zu messen.',accept:'Analytics akzeptieren',reject:'Nur notwendige',privacy:'Datenschutz'};
    }
    if (lang.indexOf('ar') === 0) {
      return {text:'نستخدم Google Analytics فقط بموافقتك لقياس الزيارات وطلبات الحجز.',accept:'قبول Analytics',reject:'الضروري فقط',privacy:'الخصوصية'};
    }
    return {text:'We use Google Analytics only with your permission to measure visits and booking enquiries.',accept:'Accept analytics',reject:'Essential only',privacy:'Privacy'};
  }

  function addConsentBanner() {
    if (getConsentChoice() || document.getElementById('ipd-consent')) return;

    var copy = copyForLanguage();
    var banner = document.createElement('aside');
    banner.id = 'ipd-consent';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Analytics consent');
    banner.innerHTML = '<p>' + copy.text + ' <a href="/privacy/">' + copy.privacy + '</a></p>' +
      '<div class="ipd-consent-actions">' +
      '<button type="button" data-consent="denied">' + copy.reject + '</button>' +
      '<button type="button" class="ipd-consent-accept" data-consent="granted">' + copy.accept + '</button>' +
      '</div>';

    var style = document.createElement('style');
    style.id = 'ipd-consent-style';
    style.textContent =
      '#ipd-consent{position:fixed;z-index:2147483647;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;padding:18px 20px;background:#111;color:#fff;border:1px solid rgba(255,255,255,.22);border-radius:14px;box-shadow:0 14px 44px rgba(0,0,0,.35);font:14px/1.45 Inter,Arial,sans-serif;display:flex;align-items:center;justify-content:space-between;gap:18px}' +
      '#ipd-consent p{margin:0;max-width:470px}#ipd-consent a{color:#fff;text-decoration:underline}' +
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
        window.gtag('event', 'page_view', {page_location: window.location.href,page_title: document.title});
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

  function serviceIntentForPath() {
    var path = (window.location.pathname || '/').toLowerCase();
    if (path.indexOf('private-aviation') !== -1) return 'private_aviation';
    if (path.indexOf('airport') !== -1) return 'airport_transfer';
    if (path.indexOf('multi-day') !== -1) return 'multi_day_chauffeur';
    if (path.indexOf('chauffeur') !== -1 || path.indexOf('chauffeur-prive') !== -1 || path.indexOf('privatchauffeur') !== -1) return 'chauffeur';
    if (path.indexOf('villa') !== -1) return 'villa_transfer';
    if (path.indexOf('yacht') !== -1 || path.indexOf('marina') !== -1) return 'yacht_marina';
    if (path.indexOf('hotel') !== -1 || path.indexOf('nobu') !== -1 || path.indexOf('six-senses') !== -1 || path.indexOf('7pines') !== -1 || path.indexOf('standard') !== -1 || path.indexOf('destino') !== -1) return 'hotel_transfer';
    if (path.indexOf('night') !== -1 || path.indexOf('club') !== -1 || path.indexOf('pacha') !== -1 || path.indexOf('ushuaia') !== -1 || path.indexOf('hi-ibiza') !== -1 || path.indexOf('unvrs') !== -1 || path.indexOf('amnesia') !== -1 || path.indexOf('dc10') !== -1 || path.indexOf('blue-marlin') !== -1) return 'nightlife';
    if (path.indexOf('mercedes-v-class') !== -1) return 'mercedes_v_class';
    if (path.indexOf('taxi') !== -1) return 'private_taxi_alternative';
    if (path.indexOf('travel-advisors') !== -1 || path.indexOf('international-private-clients') !== -1) return 'b2b_international';
    if (path.indexOf('private-driver') !== -1 || path.indexOf('conductor-privado') !== -1) return 'private_driver';
    if (path.indexOf('transfer') !== -1) return 'private_transfer';
    return 'general_private_transport';
  }

  function whatsappMessageForIntent(intent) {
    var lang = (document.documentElement.lang || 'en').toLowerCase();

    var messages = {
      en: {
        general_private_transport:'Hello, I would like to request private transport in Ibiza.\nDate:\nTime:\nPickup:\nDestination or itinerary:\nPassengers:\nLuggage:',
        private_driver:'Hello, I would like to request a private driver in Ibiza.\nDate:\nTime:\nPickup:\nDestination or itinerary:\nPassengers:\nLuggage:',
        private_transfer:'Hello, I would like to request a private transfer in Ibiza.\nDate:\nTime:\nPickup:\nDestination:\nPassengers:\nLuggage:',
        private_taxi_alternative:'Hello, I would like to request a pre-booked private driver in Ibiza.\nDate:\nTime:\nPickup:\nDestination:\nPassengers:\nLuggage:',
        airport_transfer:'Hello, I would like to request an Ibiza Airport transfer.\nDate:\nFlight number:\nArrival or departure time:\nDestination:\nPassengers:\nLuggage:',
        private_aviation:'Hello, I would like to request private aviation chauffeur service in Ibiza.\nDate:\nArrival/departure details:\nMeeting point or terminal:\nDestination or itinerary:\nPassengers:\nLuggage:',
        chauffeur:'Hello, I would like to request chauffeur service in Ibiza.\nDate(s):\nStart time:\nExpected duration:\nPickup:\nItinerary/stops:\nPassengers:\nLuggage:',
        multi_day_chauffeur:'Hello, I would like to request multi-day chauffeur service in Ibiza.\nDate(s):\nDaily start time(s):\nExpected daily hours:\nAccommodation/pickup:\nItinerary:\nPassengers:\nLuggage:',
        villa_transfer:'Hello, I would like to request private transport for a villa in Ibiza.\nDate:\nTime:\nPickup:\nVilla name or map pin:\nPassengers:\nLuggage:\nReturn required:',
        yacht_marina:'Hello, I would like to request yacht or marina transport in Ibiza.\nDate:\nTime:\nPickup:\nMarina / yacht / meeting point:\nDestination:\nPassengers:\nLuggage:',
        hotel_transfer:'Hello, I would like to request private hotel transport in Ibiza.\nDate:\nTime:\nHotel:\nPickup or destination:\nPassengers:\nLuggage:\nReturn required:',
        nightlife:'Hello, I would like to request private nightlife transport in Ibiza.\nDate:\nPickup time and place:\nVenue(s):\nReturn time/place:\nPassengers:',
        mercedes_v_class:'Hello, I would like to request a Mercedes-Benz V-Class in Ibiza.\nDate:\nTime:\nPickup:\nDestination or itinerary:\nPassengers:\nLuggage:',
        b2b_international:'Hello, I would like to coordinate private transport in Ibiza for a client/guest.\nCompany or contact name:\nDate(s):\nPickup(s):\nItinerary:\nPassengers:\nVehicle requirements:'
      },
      es: {
        general_private_transport:'Hola, quisiera solicitar transporte privado en Ibiza.\nFecha:\nHora:\nRecogida:\nDestino o itinerario:\nPasajeros:\nEquipaje:',
        private_driver:'Hola, quisiera solicitar un conductor privado en Ibiza.\nFecha:\nHora:\nRecogida:\nDestino o itinerario:\nPasajeros:\nEquipaje:',
        private_transfer:'Hola, quisiera solicitar un traslado privado en Ibiza.\nFecha:\nHora:\nRecogida:\nDestino:\nPasajeros:\nEquipaje:',
        airport_transfer:'Hola, quisiera solicitar un traslado desde o hacia el Aeropuerto de Ibiza.\nFecha:\nNúmero de vuelo:\nHora de llegada o salida:\nDestino:\nPasajeros:\nEquipaje:',
        chauffeur:'Hola, quisiera solicitar un servicio de chófer en Ibiza.\nFecha(s):\nHora de inicio:\nDuración prevista:\nRecogida:\nItinerario/paradas:\nPasajeros:\nEquipaje:',
        villa_transfer:'Hola, quisiera solicitar transporte privado para una villa en Ibiza.\nFecha:\nHora:\nRecogida:\nNombre o ubicación de la villa:\nPasajeros:\nEquipaje:\n¿Necesita regreso?:',
        yacht_marina:'Hola, quisiera solicitar transporte para un yate o marina en Ibiza.\nFecha:\nHora:\nRecogida:\nMarina / yate / punto de encuentro:\nDestino:\nPasajeros:\nEquipaje:',
        nightlife:'Hola, quisiera solicitar transporte privado para la noche en Ibiza.\nFecha:\nHora y lugar de recogida:\nLugar(es):\nHora/lugar de regreso:\nPasajeros:',
        mercedes_v_class:'Hola, quisiera solicitar una Mercedes-Benz V-Class en Ibiza.\nFecha:\nHora:\nRecogida:\nDestino o itinerario:\nPasajeros:\nEquipaje:'
      },
      fr: {
        general_private_transport:'Bonjour, je souhaite réserver un transport privé à Ibiza.\nDate :\nHeure :\nDépart :\nDestination ou itinéraire :\nPassagers :\nBagages :',
        airport_transfer:'Bonjour, je souhaite réserver un transfert depuis ou vers l’aéroport d’Ibiza.\nDate :\nNuméro de vol :\nHeure d’arrivée ou de départ :\nDestination :\nPassagers :\nBagages :',
        chauffeur:'Bonjour, je souhaite réserver un chauffeur privé à Ibiza.\nDate(s) :\nHeure de début :\nDurée prévue :\nDépart :\nItinéraire / arrêts :\nPassagers :\nBagages :',
        villa_transfer:'Bonjour, je souhaite réserver un transport privé pour une villa à Ibiza.\nDate :\nHeure :\nDépart :\nNom ou localisation de la villa :\nPassagers :\nBagages :\nRetour nécessaire :',
        yacht_marina:'Bonjour, je souhaite réserver un transport pour un yacht ou une marina à Ibiza.\nDate :\nHeure :\nDépart :\nMarina / yacht / point de rendez-vous :\nDestination :\nPassagers :\nBagages :',
        nightlife:'Bonjour, je souhaite réserver un transport privé pour une soirée à Ibiza.\nDate :\nHeure et lieu de départ :\nLieu(x) :\nHeure / lieu de retour :\nPassagers :',
        mercedes_v_class:'Bonjour, je souhaite réserver une Mercedes-Benz V-Class à Ibiza.\nDate :\nHeure :\nDépart :\nDestination ou itinéraire :\nPassagers :\nBagages :'
      },
      de: {
        general_private_transport:'Hallo, ich möchte privaten Transport in Ibiza anfragen.\nDatum:\nUhrzeit:\nAbholung:\nZiel oder Route:\nPassagiere:\nGepäck:',
        airport_transfer:'Hallo, ich möchte einen Flughafentransfer in Ibiza anfragen.\nDatum:\nFlugnummer:\nAnkunfts- oder Abflugzeit:\nZiel:\nPassagiere:\nGepäck:',
        chauffeur:'Hallo, ich möchte einen Chauffeurservice in Ibiza anfragen.\nDatum/Daten:\nStartzeit:\nVoraussichtliche Dauer:\nAbholung:\nRoute / Stopps:\nPassagiere:\nGepäck:',
        villa_transfer:'Hallo, ich möchte einen privaten Transfer zu oder von einer Villa in Ibiza anfragen.\nDatum:\nUhrzeit:\nAbholung:\nVilla / Karten-Pin:\nPassagiere:\nGepäck:\nRückfahrt benötigt:',
        yacht_marina:'Hallo, ich möchte einen Yacht- oder Marina-Transfer in Ibiza anfragen.\nDatum:\nUhrzeit:\nAbholung:\nMarina / Yacht / Treffpunkt:\nZiel:\nPassagiere:\nGepäck:',
        nightlife:'Hallo, ich möchte einen privaten Nachtleben-Transfer in Ibiza anfragen.\nDatum:\nAbholzeit und Ort:\nLocation(s):\nRückfahrt Zeit/Ort:\nPassagiere:',
        mercedes_v_class:'Hallo, ich möchte eine Mercedes-Benz V-Class in Ibiza anfragen.\nDatum:\nUhrzeit:\nAbholung:\nZiel oder Route:\nPassagiere:\nGepäck:'
      },
      ar: {
        general_private_transport:'مرحباً، أود طلب نقل خاص في إيبيزا.\nالتاريخ:\nالوقت:\nمكان الاستلام:\nالوجهة أو البرنامج:\nعدد الركاب:\nالأمتعة:',
        airport_transfer:'مرحباً، أود طلب خدمة نقل من أو إلى مطار إيبيزا.\nالتاريخ:\nرقم الرحلة:\nوقت الوصول أو المغادرة:\nالوجهة:\nعدد الركاب:\nالأمتعة:',
        chauffeur:'مرحباً، أود طلب خدمة سائق خاص في إيبيزا.\nالتاريخ/التواريخ:\nوقت البدء:\nالمدة المتوقعة:\nمكان الاستلام:\nالبرنامج / التوقفات:\nعدد الركاب:\nالأمتعة:',
        villa_transfer:'مرحباً، أود طلب نقل خاص إلى أو من فيلا في إيبيزا.\nالتاريخ:\nالوقت:\nمكان الاستلام:\nاسم الفيلا أو رابط الموقع:\nعدد الركاب:\nالأمتعة:\nهل توجد رحلة عودة:',
        yacht_marina:'مرحباً، أود طلب نقل إلى يخت أو مارينا في إيبيزا.\nالتاريخ:\nالوقت:\nمكان الاستلام:\nالمارينا / اليخت / نقطة اللقاء:\nالوجهة:\nعدد الركاب:\nالأمتعة:',
        nightlife:'مرحباً، أود طلب نقل خاص للسهرات في إيبيزا.\nالتاريخ:\nوقت ومكان الاستلام:\nالمكان/الأماكن:\nوقت ومكان العودة:\nعدد الركاب:',
        mercedes_v_class:'مرحباً، أود طلب Mercedes-Benz V-Class في إيبيزا.\nالتاريخ:\nالوقت:\nمكان الاستلام:\nالوجهة أو البرنامج:\nعدد الركاب:\nالأمتعة:'
      }
    };

    var key = 'en';
    if (lang.indexOf('es') === 0) key = 'es';
    else if (lang.indexOf('fr') === 0) key = 'fr';
    else if (lang.indexOf('de') === 0) key = 'de';
    else if (lang.indexOf('ar') === 0) key = 'ar';

    return messages[key][intent] || messages[key].general_private_transport || messages.en[intent] || messages.en.general_private_transport;
  }

  function whatsappUrlForPath() {
    return 'https://wa.me/34613756211?text=' + encodeURIComponent(whatsappMessageForIntent(serviceIntentForPath()));
  }

  function addWhatsAppFloat() {
    var path = window.location.pathname.replace(/\/+$/, '/') || '/';
    if (path === '/privacy/' || path === '/legal-notice/') return;

    var existingLinks = document.querySelectorAll('a[href*="wa.me/"],a[href*="api.whatsapp.com/"],a[href^="whatsapp://"]');
    for (var index = 0; index < existingLinks.length; index += 1) {
      var existingLink = existingLinks[index];
      if (window.getComputedStyle(existingLink).position === 'fixed') {
        existingLink.href = whatsappUrlForPath();
        existingLink.setAttribute('aria-label', whatsappLabelForLanguage());
        return;
      }
    }

    if (document.getElementById('ipd-whatsapp-float')) return;

    var link = document.createElement('a');
    link.id = 'ipd-whatsapp-float';
    link.href = whatsappUrlForPath();
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('aria-label', whatsappLabelForLanguage());
    link.innerHTML = '<svg viewBox="0 0 24 24" width="30" height="30" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12.001 2C6.478 2 2 6.478 2 12c0 1.821.487 3.53 1.338 5.003L2 22l5.144-1.352A9.958 9.958 0 0012.001 22C17.523 22 22 17.522 22 12S17.523 2 12.001 2zm0 18.15a8.13 8.13 0 01-4.146-1.135l-.297-.176-3.055.803.815-2.978-.194-.306A8.14 8.14 0 013.85 12c0-4.5 3.65-8.15 8.151-8.15 4.5 0 8.15 3.65 8.15 8.15 0 4.501-3.65 8.15-8.15 8.15z"/></svg>';

    var style = document.createElement('style');
    style.id = 'ipd-whatsapp-float-style';
    style.textContent = '#ipd-whatsapp-float{position:fixed;right:18px;bottom:18px;z-index:9998;width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#168a52;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.24);border:1px solid rgba(255,255,255,.5);text-decoration:none;transition:transform .2s ease,box-shadow .2s ease}#ipd-whatsapp-float:hover,#ipd-whatsapp-float:focus-visible{transform:translateY(-2px);box-shadow:0 11px 28px rgba(0,0,0,.3);outline:3px solid rgba(22,138,82,.25);outline-offset:3px}@media(max-width:480px){#ipd-whatsapp-float{right:14px;bottom:14px;width:54px;height:54px}}';
    document.head.appendChild(style);
    document.body.appendChild(link);
  }

  function trackLeadClick(link) {
    if (getConsentChoice() !== 'granted' || typeof window.gtag !== 'function') return;

    var href = (link.getAttribute('href') || '').toLowerCase();
    var eventName = '';
    var leadType = '';
    var serviceIntent = serviceIntentForPath();

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

    var params = {
      event_category: 'lead',
      lead_type: leadType,
      service_intent: serviceIntent,
      link_url: link.href,
      page_path: window.location.pathname,
      page_title: document.title,
      transport_type: 'beacon'
    };

    window.gtag('event', eventName, params);
    window.gtag('event', 'generate_lead', {
      currency: 'EUR',
      value: 0,
      lead_type: leadType,
      service_intent: serviceIntent,
      page_path: window.location.pathname,
      page_title: document.title,
      transport_type: 'beacon'
    });
  }

  document.addEventListener('click', function (event) {
    var reset = event.target.closest('[data-reset-consent]');
    if (reset) {
      event.preventDefault();
      try { window.localStorage.removeItem(CONSENT_KEY); } catch (error) {}
      updateConsent('denied');
      window.location.reload();
      return;
    }

    var link = event.target.closest('a[href]');
    if (link) trackLeadClick(link);
  });

  function init() {
    removeSoroFeed();
    addConsentBanner();
    addWhatsAppFloat();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
