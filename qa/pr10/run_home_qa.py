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
CANDIDATE_BLOB = '8b1f9ef75eb397aa78fea29de7fb9ddc2d462e40'
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
    page.goto(ORIGIN+'/',wait_until='networkidle',timeout=30000)
    page.evaluate('document.fonts.ready')
    report.data.setdefault('browser_versions',{})[engine]=browser.version
    if native:
        page.bring_to_front(); page.keyboard.press('Control+0')
        before=page.evaluate('devicePixelRatio')
        observed=[];ratio=1
        for _ in range(12):
            page.keyboard.press('Control++');page.wait_for_timeout(200)
            ratio=page.evaluate('devicePixelRatio')/before;observed.append(round(ratio,3))
            if abs(ratio-2)<.02 or ratio>2.02:break
        report.check(f'{engine} native browser zoom reached 200 percent',abs(ratio-2)<.02,observed)
    page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(150)
    toggle=page.locator('#navToggle');menu=page.locator('#navLinks')
    mobile=width<=768
    report.check(f'{engine}-{width}x{height}: menu initial inert',page.evaluate("document.querySelector('#navLinks').inert") is mobile)
    if mobile:
        toggle.click();page.wait_for_timeout(420)
        report.check(f'{engine}-{width}x{height}: menu opens',menu.evaluate("e=>e.classList.contains('open')"))
        report.check(f'{engine}-{width}x{height}: opened menu not inert',not page.evaluate("document.querySelector('#navLinks').inert"))
        report.check(f'{engine}-{width}x{height}: toggle expanded',toggle.get_attribute('aria-expanded')=='true')
        report.check(f'{engine}-{width}x{height}: menu within viewport',menu.evaluate(HIT))
        page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
        report.check(f'{engine}-{width}x{height}: tab reaches first menu link',page.evaluate("document.activeElement===document.querySelector('#navLinks a')"))
        page.keyboard.press('Escape');page.wait_for_timeout(420)
        report.check(f'{engine}-{width}x{height}: Escape closes',not menu.evaluate("e=>e.classList.contains('open')"))
        report.check(f'{engine}-{width}x{height}: focus returned to toggle',page.evaluate("document.activeElement===document.querySelector('#navToggle')"))
        report.check(f'{engine}-{width}x{height}: closed menu inert',page.evaluate("document.querySelector('#navLinks').inert"))
        toggle.click();page.wait_for_timeout(420);menu.locator('a').first.click();page.wait_for_timeout(420)
        report.check(f'{engine}-{width}x{height}: link closes menu',not menu.evaluate("e=>e.classList.contains('open')"))
    else:
        report.check(f'{engine}-{width}x{height}: desktop menu not inert',not page.evaluate("document.querySelector('#navLinks').inert"))
    faq=page.locator('.faq-q').first;faq.click()
    report.check(f'{engine}-{width}x{height}: FAQ opens',faq.get_attribute('aria-expanded')=='true')
    report.check(f'{engine}-{width}x{height}: no horizontal document overflow',page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"),page.evaluate("({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})"))
    report.check(f'{engine}-{width}x{height}: body text remains readable',page.evaluate("getComputedStyle(document.body).fontSize")!='0px')
    report.check(f'{engine}-{width}x{height}: all CTA links exist',page.locator('a[href]').count()>0)
    report.check(f'{engine}-{width}x{height}: external contact requests intercepted',not any(x for x in blocked if any(h in x['url'] for h in ['wa.me','tel:','mailto:'])))
    if axe_path:
        page.add_script_tag(path=str(axe_path))
        axe=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa']}})")
        serious=[v for v in axe['violations'] if v.get('impact') in ('serious','critical')]
        report.check(f'{engine}-{width}x{height}: No serious/critical automated accessibility findings',not serious,[{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in serious])
        (report.out/f'{engine}-{width}x{height}-axe.json').write_text(json.dumps(axe,ensure_ascii=False,indent=2),encoding='utf-8')
    report.data['blocked_requests'].extend(blocked);report.data['missing_resources'].extend(missing);report.data['errors'].extend(errors)
    page.screenshot(path=str(report.out/f'{engine}-{width}x{height}-final.png'),full_page=True)
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
            report.data['status']='PREFLIGHT_ONLY_NOT_BROWSER_VALIDATED' if not report.data['missing_resources'] else 'SETUP_BLOCKED'
            report.save();print(report.data['status']);return 2
        fonts=fetch_fonts(font_urls,report.data['assets'])
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            for engine in args.browser or ['chromium','firefox','webkit']:
                for width,height in ((390,844),(320,568)) if args.native_zoom else SIZES:
                    try:run_one(pw,engine,root,fonts,report,width,height,args.axe,args.native_zoom)
                    except Exception as e:
                        report.data['errors'].append(engine+' launch/setup failure: '+str(e));report.save();break
        return report.summary()
    except Exception as e:
        report.data['errors'].append(str(e));report.data['status']='SETUP_BLOCKED';report.save()
        traceback.print_exc();print('SETUP_BLOCKED');return 2
if __name__=='__main__':sys.exit(main())
