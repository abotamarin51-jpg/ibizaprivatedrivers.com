#!/usr/bin/env python3
"""PR #10 only: exact candidate, complete local site assets, fail-closed browser QA.
Never connects a browser to production. No deployment or repository writes.
Font downloads are an explicit read-only preparation stage; browser requests are
fulfilled from memory or aborted. Font binaries are never included in reports.
A pass is automated evidence, NOT approval to merge or a native Safari certificate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
import sys
import traceback
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPO = 'abotamarin51-jpg/ibizaprivatedrivers.com'
BRANCH = 'fix/home-mobile-nav-focus-inert-2026-10-06'
MAIN = '35590040c76d6af3ac90143575a4fffd46fc78b9'
MAIN_BLOB = 'ac53b99ba18ee92275c4c738790de0794a5c36dc'
CANDIDATE_BLOB = '937d9ece4a1d3ee63de50df24c471ef0d6de71db'
BAD_FONT_URL = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght;500;600&family=Manrope:wght;400;500;600&display=swap'
GOOD_FONT_URL = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Manrope:wght@400;500;600&display=swap'
ORIGIN = 'http://127.0.0.1:8765'
SITE_HOSTS = {'127.0.0.1', 'ibizaprivatedrivers.com', 'www.ibizaprivatedrivers.com'}
FONT_HOSTS = {'fonts.googleapis.com', 'fonts.gstatic.com'}
TRACKING_HOSTS = {'www.googletagmanager.com', 'www.google-analytics.com', 'region1.google-analytics.com'}
URL_RE = re.compile(r'''url\(\s*['"]?([^'"\)]+)['"]?\s*\)''', re.I)
UA = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
SIZES = [(390,844), (320,568), (195,422), (844,390), (720,900), (768,900), (769,900), (1280,900)]

class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets=[]; self.links=[]; self.shape=[]; self.text=[]; self.scripts=[]; self.styles=[]
        self.block=None; self.script_text=[]; self.style_text=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ('script','style'):
            self.block=tag
            if tag=='style': self.style_text=[]
            if tag=='script':
                self.script_text=[]
                if a.get('src'): self.assets.append(a['src'])
            return
        self.shape.append((tag,sorted(attrs)))
        if tag=='link' and any(x in a.get('rel','').split() for x in ['stylesheet','icon','apple-touch-icon','preload']):
            if a.get('href'): self.assets.append(a['href'])
        if tag in ('img','source'):
            if a.get('src'): self.assets.append(a['src'])
            if a.get('srcset'):
                self.assets.extend(x.strip().split()[0] for x in a['srcset'].split(',') if x.strip())
        if tag=='a' and a.get('href'): self.links.append(a['href'])
    def handle_endtag(self,tag):
        if tag==self.block:
            if tag=='script': self.scripts.append(''.join(self.script_text))
            if tag=='style': self.styles.append(''.join(self.style_text))
            self.block=None
    def handle_data(self,data):
        if self.block=='script': self.script_text.append(data)
        elif self.block=='style': self.style_text.append(data)
        elif self.block is None and data.strip(): self.text.append(' '.join(data.split()))

def parse(data):
    p=Markup();p.feed(data.decode('utf-8'));return p

def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def safe_local(root, url):
    u=urlsplit(urljoin(ORIGIN+'/',url))
    if u.hostname not in SITE_HOSTS or u.scheme not in ('http','https'): return None
    p=(root/unquote(u.path).lstrip('/')).resolve()
    if not p.is_relative_to(root): raise ValueError('Path traversal rejected')
    if p.is_dir() or u.path.endswith('/'):p=p/'index.html'
    return p

def frozen_signature(p):
    scripts=[s for s in p.scripts if not ('navToggle' in s and 'navLinks' in s)]
    shape=[]
    for tag,attrs in p.shape:
        norm=[]
        attr_map=dict(attrs)
        for k,v in attrs:
            if tag=='ul' and attr_map.get('id')=='navLinks' and k=='tabindex' and v=='-1':
                continue
            if tag=='link' and k=='href' and v in (BAD_FONT_URL,GOOD_FONT_URL):
                v='__IPD_GOOGLE_FONTS_STYLESHEET__'
            norm.append((k,v))
        shape.append((tag,norm))
    return {'markup':shape,'visible_text':p.text,'scripts_except_nav':scripts}

class FontsOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlsplit(newurl).scheme!='https' or urlsplit(newurl).hostname not in FONT_HOSTS:
            raise ValueError('Font download redirect refused: '+newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_fonts(urls, manifest):
    """No page views, production fetches, arbitrary hosts or contacts."""
    cache={}; todo=list(urls); opener=build_opener(FontsOnlyRedirect())
    while todo:
        url=todo.pop()
        if url in cache:continue
        u=urlsplit(url)
        if u.scheme!='https' or u.hostname not in FONT_HOSTS:raise ValueError('Not an approved font asset')
        if len(cache)>60:raise ValueError('Font asset budget exceeded')
        with opener.open(Request(url,headers={'User-Agent':UA}),timeout=25) as r:
            data=r.read(2_000_001);mime=r.headers.get_content_type()
        if len(data)>2_000_000 or not data:raise ValueError('Invalid font asset size')
        if u.hostname=='fonts.googleapis.com' and mime!='text/css':raise ValueError('Font stylesheet is not CSS')
        if u.hostname=='fonts.gstatic.com' and not (data[:4] in (b'wOFF',b'wOF2',b'OTTO',b'\x00\x01\x00\x00')):
            raise ValueError('Font asset does not have a recognised font signature')
        cache[url]=(data,mime)
        manifest.append({'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'type':mime})
        if mime=='text/css':
            todo.extend(urljoin(url,m.group(1).strip()) for m in URL_RE.finditer(data.decode('utf-8')))
    return cache

GUARDS=r'''(() => {
  window.__ipdQA = {links: [], blocked: []};
  window.open = u => {window.__ipdQA.blocked.push(String(u)); return null;};
  navigator.sendBeacon = u => {window.__ipdQA.blocked.push(String(u)); return false;};
  window.WebSocket = function(){throw new Error('QA blocks WebSockets');};
  document.addEventListener('click', e => {
    const a=e.target.closest && e.target.closest('a');
    if(a){window.__ipdQA.links.push(a.getAttribute('href')); e.preventDefault();}
  }, true); // DO NOT stop propagation: test the real link-close handlers.
  document.addEventListener('submit', e => e.preventDefault(), true);
  HTMLFormElement.prototype.submit=function(){window.__ipdQA.blocked.push('form.submit');};
})();'''

HIT=r'''el => {
 const rs=[...el.getClientRects()].filter(r=>r.width>0&&r.height>0);
 return rs.length>0 && rs.every(r=>r.left>=-0.5&&r.right<=innerWidth+0.5&&r.top>=-0.5&&r.bottom<=innerHeight+0.5&&
   [0.2,0.5,0.8].every(x=>{let n=document.elementFromPoint(r.x+r.width*x,r.y+r.height/2);return n===el||el.contains(n)}));
}'''

class Report:
    def __init__(self,out):
        self.out=out;out.mkdir(parents=True,exist_ok=True)
        self.data={'status':'RUNNING','scope':'local complete-resource copy, not production',
          'candidate_sha256':None,'source_pr_head':None,'checks':[],
          'assets':[], 'errors':[], 'blocked_requests':[], 'missing_resources':[],
          'manual_gates':['Review rendered screenshots and animations',
                          'Review accessibility findings against baseline',
                          'Revalidate main/head/reviews/required checks before merge',
                          'Verify production/deployment after a separately authorised merge'],
          'merged':False,'published':False,'native_safari_tested':False}
    def check(self,name,ok,detail=None):
        self.data['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
    def save(self):
        (self.out/'report.json').write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
    def summary(self):
        fails=[x for x in self.data['checks'] if not x['passed']]
        if self.data['errors'] or fails or self.data['missing_resources']:
            self.data['status']='FAILED_OR_BLOCKED'
        else:self.data['status']='AUTOMATED_CHECKS_PASSED_MANUAL_REVIEW_STILL_REQUIRED'
        self.save(); print(self.data['status'],len(self.data['checks']),'checks;',len(fails),'failed')
        return 1 if self.data['status']=='FAILED_OR_BLOCKED' else 0

def preflight(root,baseline,report,check_sha=True):
    data=(root/'index.html').read_bytes();p=parse(data)
    if check_sha:
        actual_sha256=hashlib.sha256(data).hexdigest()
        report.data['candidate_sha256']=actual_sha256
        report.check('Exact candidate Git blob',git_blob(data)==CANDIDATE_BLOB,git_blob(data))
        font_hrefs=[u for u in p.assets if urlsplit(u).hostname=='fonts.googleapis.com']
        report.check('Google Fonts CSS2 URL corrected',GOOD_FONT_URL in font_hrefs and BAD_FONT_URL not in font_hrefs,font_hrefs)
        nav_lists=[dict(attrs) for tag,attrs in p.shape if tag=='ul' and dict(attrs).get('id')=='navLinks']
        report.check('Scrollable mobile nav excluded from sequential tab order',len(nav_lists)==1 and nav_lists[0].get('tabindex')=='-1',nav_lists)
        old=baseline.read_bytes() if baseline else subprocess.check_output(['git','show',MAIN+':index.html'],cwd=root)
        report.check('Baseline matches verified main blob',git_blob(old)==MAIN_BLOB)
        report.check('SEO, contacts, markup, copy and non-menu scripts unchanged',frozen_signature(p)==frozen_signature(parse(old)))
        # CSS is excluded from frozen_signature by design; explicitly report it.
        old_markup=parse(old)
        css_before='\n'.join(old_markup.styles).encode('utf-8')
        css_after='\n'.join(p.styles).encode('utf-8')
        css_modified=css_before!=css_after
        report.data['inline_css_comparison']={
            'changed':css_modified,
            'main_sha256':hashlib.sha256(css_before).hexdigest(),
            'candidate_sha256':hashlib.sha256(css_after).hexdigest(),
            'main_blocks':len(old_markup.styles),
            'candidate_blocks':len(p.styles),
        }
        if css_modified:
            report.data['manual_gates'].append('Review changed inline CSS vs main at mobile, desktop and native 200% zoom')
        if baseline is None:
            def git(*a):return subprocess.check_output(['git',*a],cwd=root,text=True).strip()
            report.data['tested_commit']=git('rev-parse','HEAD')
            report.data['source_pr_head']=report.data['tested_commit']
            report.check('Live main has not invalidated the baseline',git('rev-parse','origin/main')==MAIN)
            remote=git('config','--get','remote.origin.url').rstrip('/')
            report.check('Exact intended repository checkout',remote in ('https://github.com/'+REPO,'https://github.com/'+REPO+'.git'))
            paths=git('diff','--name-only',MAIN,'HEAD').splitlines()
            unexpected=[x for x in paths if x!='index.html' and x!='.github/workflows/ipd-home-cross-browser.yml' and not x.startswith('qa/pr10/')]
            report.check('No unrelated files or site configuration changed',not unexpected,unexpected)
    mandatory={'/assets/photo-proof.css','/assets/ivm-typography.css','/analytics.js'}
    todo=list(p.assets)+list(mandatory);done=set();font_urls=[]
    while todo:
        url=urljoin(ORIGIN+'/',todo.pop())
        if url in done:continue
        done.add(url);u=urlsplit(url)
        if u.scheme=='data':continue
        if u.hostname in TRACKING_HOSTS:
            report.data['blocked_requests'].append({'url':url,'reason':'External tracking is intentionally never loaded'})
            continue
        if u.hostname in FONT_HOSTS:font_urls.append(url);continue
        path=safe_local(root,url)
        if path is None:
            report.data['errors'].append('Unreviewed external page asset: '+url);continue
        if not path.is_file():report.data['missing_resources'].append(str(path.relative_to(root)));continue
        b=path.read_bytes()
        report.data['assets'].append({'path':str(path.relative_to(root)),'bytes':len(b),'git_blob':git_blob(b),'sha256':hashlib.sha256(b).hexdigest()})
        if path.suffix=='.css':
            css=b.decode('utf-8')
            todo.extend(urljoin(url,m.group(1).strip()) for m in URL_RE.finditer(css) if not m.group(1).startswith(('data:','#')))
            todo.extend(urljoin(url,x) for x in re.findall(r'''@import\s+['"]([^'"]+)['"]''',css))
    for href in sorted(set(p.links)):
        u=urlsplit(urljoin(ORIGIN+'/',href))
        if u.hostname in SITE_HOSTS:
            f=safe_local(root,href)
            report.check('Internal target exists: '+u.path,bool(f and f.is_file()))
    report.check('Complete local resources (no subset CSS or placeholders)',not report.data['missing_resources'],report.data['missing_resources'])
    return p,list(set(font_urls))

def run_one(pw,engine,root,fonts,report,width,height,axe_path,native=False):
    exe=None
    if engine=='chromium':
        import os
        exe=os.environ.get('IPD_QA_CHROMIUM_EXECUTABLE')
    browser=getattr(pw,engine).launch(headless=not native,executable_path=exe)
    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,service_workers='block',accept_downloads=False)
    context.add_init_script(GUARDS)
    errors=[];missing=[];loaded=set();blocked=[]
    def route_handler(route):
        request=route.request;url=request.url
        if request.method!='GET':blocked.append({'url':url,'reason':'non-GET'});route.abort();return
        if url in fonts:
            b,m=fonts[url];loaded.add(url);route.fulfill(status=200,content_type=m,body=b);return
        path=safe_local(root,url)
        if path and path.is_file():
            loaded.add(str(path.relative_to(root)))
            route.fulfill(status=200,content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',body=path.read_bytes());return
        if path:missing.append(str(path.relative_to(root)))
        blocked.append({'url':url,'reason':'not in exact local/font allowlist'});route.abort()
    context.route('**/*',route_handler)
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    prefix=f'{engine}-{width}x{height}'+('-native200' if native else '')
    def ck(name,ok,detail=None):report.check(prefix+': '+name,ok,detail)
    try:
        page.goto(ORIGIN+'/',wait_until='networkidle',timeout=30000)
        page.evaluate('document.fonts.ready')
        if native:
            page.bring_to_front()
            # In Xvfb, bringing the Playwright page to front may not give
            # Firefox's actual X11 window keyboard focus. Focus a real Firefox
            # window before native shortcut input; do not emulate zoom via CSS.
            firefox_window=None
            if engine=='firefox':
                matches=subprocess.run(
                    ['xdotool','search','--onlyvisible','--class','[Ff]irefox'],
                    capture_output=True,text=True,check=False)
                window_ids=[wid for wid in matches.stdout.splitlines() if wid.isdecimal()]
                for wid in reversed(window_ids):
                    focus=subprocess.run(['xdotool','windowfocus',wid],capture_output=True,text=True,check=False)
                    if focus.returncode==0:
                        firefox_window=wid
                        break
                report.data.setdefault('x11_native_zoom_focus',{})[prefix]={
                    'matching_window_count':len(window_ids),
                    'focused_window_found':firefox_window is not None,
                }
            def zoom_key(keys):
                if firefox_window:
                    subprocess.run(['xdotool','windowfocus',firefox_window],check=False)
                if keys=='ctrl+wheel-up':
                    # A genuine X11 Ctrl+wheel gesture asks Firefox to change
                    # its native browser page zoom, not a CSS/viewport scale.
                    # It is a distinct path when keyboard shortcuts are ignored.
                    if firefox_window:
                        subprocess.run(['xdotool','mousemove','--window',firefox_window,'120','180'],check=False)
                        subprocess.run(['xdotool','keydown','Control_L'],check=False)
                        try:
                            subprocess.run(['xdotool','click','4'],check=False)
                        finally:
                            subprocess.run(['xdotool','keyup','Control_L'],check=False)
                else:
                    subprocess.run(['xdotool','key','--clearmodifiers',keys],check=True)
            shortcuts=['ctrl+plus']
            if engine=='firefox':
                # Browser-native zoom can use keyboard or Control + wheel;
                # every attempt must be measured, never assumed to have worked.
                shortcuts=['ctrl+plus','ctrl+equal','ctrl+KP_Add','ctrl+wheel-up']
            confirmed=False;best=None
            for shortcut in shortcuts:
                zoom_key('ctrl+0')
                page.wait_for_timeout(250)
                initial=page.evaluate("() => ({dpr:devicePixelRatio,innerWidth,clientWidth:document.documentElement.clientWidth})")
                levels=[];ratio=1.0
                for _ in range(12):
                    zoom_key(shortcut)
                    page.wait_for_timeout(250)
                    current=page.evaluate("() => ({dpr:devicePixelRatio,innerWidth,clientWidth:document.documentElement.clientWidth})")
                    dpr_ratio=current['dpr']/initial['dpr'] if initial['dpr'] else 1.0
                    viewport_ratio=initial['innerWidth']/current['innerWidth'] if current['innerWidth'] else 1.0
                    ratio=max(dpr_ratio,viewport_ratio)
                    levels.append({'effective':round(ratio,3),'dpr':round(dpr_ratio,3),
                                   'viewport':round(viewport_ratio,3),'innerWidth':current['innerWidth'],
                                   'clientWidth':current['clientWidth']})
                    # Browser-native zoom levels are discrete. A native level from
                    # 198% through 210% is accepted as exercising at least the
                    # requested 200% condition; the exact measured ratio is retained.
                    if 1.98<=ratio<=2.10:
                        confirmed=True;break
                    if ratio>2.10:break
                attempt={'shortcut':shortcut,'ratio':ratio,'steps':len(levels),
                         'observed':levels,'initial':initial}
                if best is None or abs(ratio-2)<abs(best['ratio']-2):best=attempt
                if confirmed:
                    best=attempt;break
            report.data.setdefault('native_zoom_attempts',{})[prefix]=best
            if not confirmed:
                report.data['manual_gates'].append(
                    prefix+': native browser UI zoom >=200% could not be confirmed on this Linux/Xvfb runner; '
                    'no viewport/CSS emulation was substituted'
                )
                return
            ck('Native browser UI zoom reached at least 200%',True,best)
        # Exercise actual analytics.js banner locally with all remote outputs disabled.
        reject=page.locator('#ipd-consent button[data-consent="denied"]')
        ck('Actual consent banner was executed',reject.count()==1)
        if reject.count():
            ck('Essential-only control is visible and unobstructed',reject.evaluate(HIT))
            reject.click(timeout=3500)
            ck('Consent rejection closes banner',page.locator('#ipd-consent').count()==0)
        fonts_state=page.evaluate('''() => [...document.fonts].map(f=>({family:f.family,status:f.status}))''')
        for family in ['Manrope','Cormorant Garamond']:
            ck('Real font loaded: '+family,any(family in f['family'] and f['status']=='loaded' for f in fonts_state))
        for i in range(page.locator('img').count()):
            image=page.locator('img').nth(i);image.scroll_into_view_if_needed()
            loaded_ok=False
            for _ in range(30):
                loaded_ok=image.evaluate('el=>el.complete&&el.naturalWidth>0')
                if loaded_ok:break
                page.wait_for_timeout(100)
            if loaded_ok:
                try:image.evaluate('(el)=>el.decode()')
                except Exception as e:errors.append('Image decode after load: '+str(e))
            ck('Real image decoded '+str(i),loaded_ok,{'src':image.get_attribute('src'),'complete':image.evaluate('el=>el.complete'),'naturalWidth':image.evaluate('el=>el.naturalWidth')})
        # The Home CSS uses scroll-behavior:smooth. After visiting each real
        # image, a smooth scrollTo(0,0) can still be travelling from the footer
        # when Chromium captures a viewport: the screenshot then looks blank.
        # Use a synchronous scroll for evidence, without changing site CSS.
        page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
        page.wait_for_timeout(150)
        closed_scroll=page.evaluate('window.scrollY')
        ck('Closed screenshot starts at document top',abs(closed_scroll)<=1,{'scrollY':closed_scroll})
        page.screenshot(path=str(report.out/(prefix+'-closed.png')))
        mobile=page.evaluate("matchMedia('(max-width:768px)').matches")
        toggle=page.locator('#navToggle');menu=page.locator('#navLinks')
        if mobile:
            ck('Closed menu is inert',menu.evaluate('el=>el.inert'))
            ck('Toggle fits and can receive pointer input',toggle.evaluate(HIT))
            toggle.focus();page.keyboard.press('Tab')
            ck('Tab skips closed links',page.evaluate("!document.getElementById('navLinks').contains(document.activeElement)"))
            toggle.focus();page.keyboard.press('Shift+Tab')
            ck('Shift+Tab skips closed links',page.evaluate("!document.getElementById('navLinks').contains(document.activeElement)"))
            toggle.click(timeout=3500)
            page.wait_for_timeout(90)
            ck('Opening transition is configured',menu.evaluate("el=>getComputedStyle(el).transitionProperty.includes('transform') && parseFloat(getComputedStyle(el).transitionDuration)>0"))
            page.wait_for_timeout(400)
            ck('Open state and aria-expanded',toggle.get_attribute('aria-expanded')=='true' and not menu.evaluate('el=>el.inert'))
            toggle.focus();page.keyboard.press('Tab');page.wait_for_timeout(80)
            first_focus=page.evaluate("""() => ({ok:document.activeElement===document.querySelector('#navLinks a'),tag:document.activeElement&&document.activeElement.tagName,id:document.activeElement&&document.activeElement.id,href:document.activeElement&&document.activeElement.getAttribute&&document.activeElement.getAttribute('href'),text:document.activeElement&&document.activeElement.textContent&&document.activeElement.textContent.trim().slice(0,80)})""")
            ck('Tab reaches first open link',first_focus['ok'],first_focus)
            page.keyboard.press('Shift+Tab')
            ck('Shift+Tab returns to toggle',page.evaluate("document.activeElement.id==='navToggle'"))
            for _ in range(menu.locator('a').count()):page.keyboard.press('Tab')
            page.wait_for_timeout(80)
            book_focus=page.evaluate("""() => ({ok:document.activeElement===document.querySelector('#navLinks .nav-cta'),tag:document.activeElement&&document.activeElement.tagName,id:document.activeElement&&document.activeElement.id,href:document.activeElement&&document.activeElement.getAttribute&&document.activeElement.getAttribute('href'),text:document.activeElement&&document.activeElement.textContent&&document.activeElement.textContent.trim().slice(0,80)})""")
            ck('Book Now reached by keyboard',book_focus['ok'],book_focus)
            ck('Book Now visible after keyboard scrolling',menu.locator('.nav-cta').evaluate(HIT),menu.locator('.nav-cta').evaluate('el=>({scrollTop:el.closest("#navLinks").scrollTop,rect:{left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom},vw:innerWidth,vh:innerHeight})'))
            page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
            open_scroll=page.evaluate('window.scrollY')
            ck('Open screenshot starts at document top',abs(open_scroll)<=1,{'scrollY':open_scroll})
            page.screenshot(path=str(report.out/(prefix+'-open.png')))
            # Axe must inspect the OPEN menu, not just its closed end state.
            if axe_path:
                page.add_script_tag(path=str(axe_path))
                open_result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
                (report.out/(prefix+'-axe-open.json')).write_text(json.dumps(open_result,ensure_ascii=False,indent=2),encoding='utf-8')
                open_serious=[{'id':v['id'],'impact':v.get('impact'),'nodes':[n['target'] for n in v['nodes']]}
                              for v in open_result['violations'] if v.get('impact') in ('serious','critical')]
                ck('No serious/critical OPEN-menu axe findings',not open_serious,open_serious)
                if open_result.get('incomplete'):report.data['manual_gates'].append(prefix+': Review OPEN-menu axe incomplete results')
            else:
                ck('Open-menu axe-core available',False,'axe-core unavailable')
            page.keyboard.press('Escape');page.wait_for_timeout(400)
            ck('Escape closes and returns focus',menu.evaluate('el=>el.inert') and page.evaluate("document.activeElement.id==='navToggle'"))
            toggle.click();page.wait_for_timeout(400)
            ck('Reopening resets scroll',menu.evaluate('el=>el.scrollTop')<1)
            menu.locator('a').first.click();page.wait_for_timeout(400)
            ck('Real link handler closes menu without following link',toggle.get_attribute('aria-expanded')=='false')
            toggle.click();page.wait_for_timeout(400);toggle.click();page.wait_for_timeout(400)
            ck('Toggle closes menu',menu.evaluate('el=>el.inert'))
        else:ck('Desktop menu is not inert',not menu.evaluate('el=>el.inert'))
        if not native:
            page.set_viewport_size({'width':1024,'height':900})
            desktop_ready=True
            try:page.wait_for_function("() => !document.getElementById('navLinks').inert",timeout=2500)
            except Exception:desktop_ready=False
            desktop_state=page.evaluate("""() => ({inert:document.getElementById('navLinks').inert,expanded:document.getElementById('navToggle').getAttribute('aria-expanded'),matches:matchMedia('(max-width:768px)').matches})""")
            ck('Resize to desktop removes inert',desktop_ready and not desktop_state['inert'],desktop_state)
            page.set_viewport_size({'width':390,'height':844})
            mobile_ready=True
            try:page.wait_for_function("() => document.getElementById('navLinks').inert && document.getElementById('navToggle').getAttribute('aria-expanded')==='false'",timeout=2500)
            except Exception:mobile_ready=False
            mobile_state=page.evaluate("""() => ({inert:document.getElementById('navLinks').inert,expanded:document.getElementById('navToggle').getAttribute('aria-expanded'),matches:matchMedia('(max-width:768px)').matches})""")
            ck('Resize to mobile closes and reinstates inert',mobile_ready and mobile_state['inert'] and mobile_state['expanded']=='false',mobile_state)
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(400)
        for i in range(page.locator('.faq-q').count()):
            q=page.locator('.faq-q').nth(i);q.click();
            ck('FAQ opens '+str(i),q.get_attribute('aria-expanded')=='true')
            q.click();ck('FAQ closes '+str(i),q.get_attribute('aria-expanded')=='false')
        for selector in ['.hero-actions .btn-primary','.hero-actions .btn-ghost','.cta-strip .btn-dark']:
            el=page.locator(selector);el.scroll_into_view_if_needed();page.wait_for_timeout(200)
            ck('Booking control visible '+selector,el.evaluate(HIT))
            href=el.get_attribute('href');ck('Approved WhatsApp destination '+selector,bool(href and urlsplit(href).hostname=='wa.me' and urlsplit(href).path=='/34613756211'))
            el.click(timeout=3500)
        page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(450)
        for i in range(page.locator('.ipd-lang-link').count()):
            el=page.locator('.ipd-lang-link').nth(i)
            el.scroll_into_view_if_needed();page.wait_for_timeout(80)
            ck('Language control visible '+str(i),el.evaluate(HIT),el.evaluate('el=>({position:getComputedStyle(el.parentElement).position,rect:{left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom},vw:innerWidth,vh:innerHeight})'))
        overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
        ck('No horizontal document overflow',overflow<=0,overflow)
        if axe_path:
            if page.evaluate('typeof window.axe === "undefined"'): page.add_script_tag(path=str(axe_path))
            result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
            (report.out/(prefix+'-axe.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            serious=[{'id':v['id'],'impact':v.get('impact'),'nodes':[n['target'] for n in v['nodes']]} for v in result['violations'] if v.get('impact') in ('serious','critical')]
            ck('No serious/critical automated accessibility findings',not serious,serious)
            if result.get('incomplete'):report.data['manual_gates'].append(prefix+': Review axe incomplete results')
        else:ck('Accessibility engine available',False,'axe-core path missing; contrast must not be marked passed')
        ck('Actual full CSS and analytics script loaded',all(x in loaded for x in ['assets/photo-proof.css','assets/ivm-typography.css','analytics.js']))
        ck('No JavaScript execution errors',not errors,errors)
        ck('No missing runtime assets',not missing,missing)
        page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
        final_scroll=page.evaluate('window.scrollY')
        ck('Final screenshot starts at document top',abs(final_scroll)<=1,{'scrollY':final_scroll})
        page.screenshot(path=str(report.out/(prefix+'-final.png')))
    except Exception as e:
        ck('Scenario completed',False,str(e));errors.append(traceback.format_exc())
        try:page.screenshot(path=str(report.out/(prefix+'-failure.png')))
        except Exception:pass
    finally:
        report.data.setdefault('browser_versions',{})[engine]=browser.version
        report.data['blocked_requests'].extend(blocked)
        report.data['missing_resources'].extend(missing)
        report.data['errors'].extend(errors)
        context.close();browser.close();report.save()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--baseline',type=Path)
    ap.add_argument('--browser',action='append',choices=['chromium','firefox','webkit'])
    ap.add_argument('--axe',type=Path);ap.add_argument('--preflight-only',action='store_true');ap.add_argument('--native-zoom',action='store_true')
    args=ap.parse_args();root=args.root.resolve();report=Report(args.output.resolve())
    try:
        _,font_urls=preflight(root,args.baseline,report)
        if args.preflight_only or any(not c['passed'] for c in report.data['checks']) or report.data['errors']:
            report.data['status']='PREFLIGHT_ONLY_NOT_BROWSER_VALIDATED' if not report.data['missing_resources'] else 'BLOCKED_INCOMPLETE_RESOURCES'
            report.save();print(report.data['status']);return 2
        if not font_urls:raise RuntimeError('Real external font stylesheet was not found')
        fonts=fetch_fonts(font_urls,report.data['assets'])
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            # Try the real browser-UI zoom gesture in every requested engine. Detection
            # uses both device-pixel ratio and the CSS viewport width because engines
            # expose native zoom differently. If the runner cannot prove 200%, the
            # scenario remains an explicit manual gate; it is never replaced by CSS or
            # viewport emulation.
            engines=args.browser or ['chromium','firefox','webkit']
            for engine in engines:
                for width,height in ([(390,844),(640,844)] if args.native_zoom else SIZES):
                    try:run_one(pw,engine,root,fonts,report,width,height,args.axe,args.native_zoom)
                    except Exception as e:
                        report.data['errors'].append(engine+' launch/setup failure: '+str(e));report.save();break
        return report.summary()
    except Exception as e:
        report.data['errors'].append(str(e));report.data['status']='SETUP_BLOCKED';report.save()
        print('SETUP_BLOCKED:',str(e));return 2
if __name__=='__main__':sys.exit(main())
