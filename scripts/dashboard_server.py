#!/usr/bin/env python3
"""ARION MISSION CONTROL v4"""
import http.server, json, os, re, subprocess, threading, time, queue
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs
import socketserver

PORT = int(os.environ.get("DASHBOARD_PORT", 9090))
HOME = Path.home()
ARION = HOME/"biblioteca-universal-arion"
TASKS = HOME/".openclaw"/"workspace"/"tasks"
OBRES = ARION/"obres"
LOGS = {"openclaw":HOME/"openclaw.log","worker":HOME/"claude-worker.log","claude_result":Path("/tmp/claude-code-result.txt"),"claude_status":Path("/tmp/claude-code-status.txt"),"claude_live":Path("/tmp/claude-live.txt")}

class S:
    @staticmethod
    def worker():
        try:
            pf=Path("/tmp/worker.pid"); lf=TASKS/"worker.lock"
            wp=pf.read_text().strip() if pf.exists() else None
            wr=False
            if wp:
                try: wr=subprocess.run(["ps","-p",wp,"-o","comm="],capture_output=True,text=True,timeout=3).returncode==0
                except: pass
            if not wr:
                try:
                    r=subprocess.run(["pgrep","-f","claude-worker"],capture_output=True,text=True,timeout=3)
                    wr=r.returncode==0
                    if wr and r.stdout.strip(): wp=r.stdout.strip().split('\n')[0]
                except: pass
            ca=False
            try: ca=bool(subprocess.run(["bash","-c","ps aux|grep '[c]laude.*-p'|head -1"],capture_output=True,text=True,timeout=3).stdout.strip())
            except: pass
            ct=None
            if lf.exists():
                try:
                    c=lf.read_text().strip()
                    try: d=json.loads(c); ct=d.get("task",d.get("instruction","..."))[:100]
                    except: ct=c[:100]
                except: ct="..."
            return {"running":wr,"pid":wp,"claude_active":ca,"current_task":ct}
        except Exception as e: return {"running":False,"error":str(e)}

    @staticmethod
    def tasks():
        t={"pending":[],"running":[],"done":[],"failed":[]}
        try:
            if not TASKS.exists(): return {"pending":[],"running":[],"done":[],"failed":[],"counts":{"pending":0,"running":0,"done":0,"failed":0}}
            # Check subdirectory structure first (pending/, running/, done/, failed/)
            has_subdirs=any((TASKS/d).is_dir() for d in ["pending","running","done","failed"])
            if has_subdirs:
                for status in ["pending","running","done","failed"]:
                    d=TASKS/status
                    if not d.is_dir(): continue
                    for f in sorted(d.glob("*.json")):
                        try: data=json.loads(f.read_text())
                        except: data={}
                        t[status].append({"name":f.stem,"type":data.get("type","?"),"instruction":data.get("instruction","")[:150]})
            else:
                # Fallback: flat files with prefixes
                for f in sorted(TASKS.glob("*.json")):
                    n=f.stem
                    if n=="worker": continue
                    try: data=json.loads(f.read_text())
                    except: data={}
                    i={"name":n,"type":data.get("type","?"),"instruction":data.get("instruction","")[:150]}
                    if n.startswith("done_"): t["done"].append(i)
                    elif n.startswith("failed_"): t["failed"].append(i)
                    elif n.startswith("running_"): t["running"].append(i)
                    else: t["pending"].append(i)
        except: pass
        return {"pending":t["pending"][-30:],"running":t["running"],"done":t["done"][-15:],"failed":t["failed"][-10:],"counts":{k:len(v) for k,v in t.items()}}

    @staticmethod
    def obres():
        o=[]
        try:
            if not OBRES.exists(): return o
            for cat in sorted(OBRES.iterdir()):
                if not cat.is_dir(): continue
                for aut in sorted(cat.iterdir()):
                    if not aut.is_dir(): continue
                    for ob in sorted(aut.iterdir()):
                        if not ob.is_dir(): continue
                        m={}; mf=ob/"metadata.yml"
                        if mf.exists():
                            try:
                                for l in mf.read_text().split('\n'):
                                    if ':' in l: k,v=l.split(':',1); m[k.strip()]=v.strip().strip('"\'')
                            except: pass
                        st="empty"
                        if (ob/".validated").exists(): st="validated"
                        elif (ob/".fixing").exists(): st="fixing"
                        elif (ob/".needs_fix").exists(): st="needs_fix"
                        elif (ob/"traduccio.md").exists(): st="translated"
                        elif (ob/"original.md").exists(): st="has_original"
                        sc=None
                        for sf in [ob/".validated",ob/".needs_fix"]:
                            if sf.exists():
                                try:
                                    x=re.search(r'[\d.]+',sf.read_text().strip())
                                    if x: sc=float(x.group())
                                except: pass
                        o.append({"categoria":cat.name,"autor":aut.name,"obra":m.get("titol",ob.name),"llengua":m.get("llengua_original","?"),"status":st,"score":sc})
        except: pass
        return o

    @staticmethod
    def daily():
        try:
            today=datetime.now().strftime('%Y-%m-%d')
            yest=(datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')
            wl=LOGS["worker"]; td=tf=trl=yd=0
            if wl.exists():
                try:
                    r=subprocess.run(["grep",today,str(wl)],capture_output=True,text=True,timeout=5)
                    if r.returncode==0:
                        for l in r.stdout.split('\n'):
                            lo=l.lower()
                            if 'completada' in lo or '✅' in lo: td+=1
                            if 'failed' in lo or '❌' in lo: tf+=1
                            if 'rate limit' in lo or 'rate_limit' in lo: trl+=1
                except: pass
                try:
                    r=subprocess.run(["bash","-c",f"grep -c '{yest}.*COMPLETADA\\|{yest}.*✅' {wl}"],capture_output=True,text=True,timeout=3)
                    if r.returncode==0: yd=int(r.stdout.strip())
                except: pass
            wu="—"
            try:
                pf=Path("/tmp/worker.pid")
                if pf.exists():
                    r=subprocess.run(["ps","-p",pf.read_text().strip(),"-o","etime="],capture_output=True,text=True,timeout=3)
                    if r.returncode==0: wu=r.stdout.strip()
            except: pass
            return {"today_done":td,"today_failed":tf,"today_rate_limits":trl,"yesterday_done":yd,"worker_uptime":wu}
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def claude_session():
        try:
            wl=LOGS["worker"]; is_rl=False; ri="Activa"
            if wl.exists():
                try:
                    r=subprocess.run(["tail","-50",str(wl)],capture_output=True,text=True,timeout=3)
                    for line in reversed(r.stdout.strip().split('\n')):
                        lo=line.lower()
                        if 'rate limit' in lo or 'usage limit' in lo or 'pausa' in lo:
                            is_rl=True
                            pm=re.search(r'pausa\s+(\d+)\s*min',lo)
                            ri=f"Pausa {pm.group(1)} min" if pm else "En pausa"
                            break
                        elif 'completada' in lo or '✅' in lo: break
                except: pass
            return {"is_rate_limited":is_rl,"reset_info":ri}
        except Exception as e: return {"error":str(e),"is_rate_limited":False}

    @staticmethod
    def venice_diem():
        """Crèdits Venice / DIEM via API."""
        try:
            # Llegir VENICE_API_KEY de .env o entorn
            api_key=os.environ.get("VENICE_API_KEY","")
            if not api_key:
                env_file=ARION/".env"
                if env_file.exists():
                    for line in env_file.read_text().split('\n'):
                        if line.startswith("VENICE_API_KEY="):
                            api_key=line.split('=',1)[1].strip().strip('"').strip("'")
            if not api_key:
                env_file=HOME/".env"
                if env_file.exists():
                    for line in env_file.read_text().split('\n'):
                        if line.startswith("VENICE_API_KEY="):
                            api_key=line.split('=',1)[1].strip().strip('"').strip("'")
            if not api_key:
                return {"available":False,"raw":"VENICE_API_KEY no trobada"}
            r=subprocess.run(["curl","-s","-H",f"Authorization: Bearer {api_key}","https://api.venice.ai/api/v1/billing/balance"],capture_output=True,text=True,timeout=15)
            out=r.stdout.strip()
            if not out:
                return {"available":False,"raw":"API no respon"}
            try:
                data=json.loads(out)
                if "error" in data:
                    return {"available":False,"raw":str(data["error"])[:200]}
                return {"available":True,"data":data,"raw":out[:500]}
            except json.JSONDecodeError:
                return {"available":False,"raw":out[:200]}
        except Exception as e:
            return {"available":False,"raw":str(e)}

    @staticmethod
    def openclaw():
        try:
            r=subprocess.run(["pgrep","-f","openclaw"],capture_output=True,text=True,timeout=3)
            run=r.returncode==0; last=""
            if LOGS["openclaw"].exists():
                try: last=subprocess.run(["tail","-1",str(LOGS["openclaw"])],capture_output=True,text=True,timeout=3).stdout.strip()[:120]
                except: pass
            return {"running":run,"last_activity":last}
        except Exception as e: return {"running":False,"error":str(e)}

    @staticmethod
    def git():
        try:
            r=subprocess.run(["git","log","--oneline","-8"],capture_output=True,text=True,timeout=5,cwd=str(ARION))
            c=r.stdout.strip().split('\n') if r.returncode==0 else []
            r2=subprocess.run(["git","status","--short"],capture_output=True,text=True,timeout=5,cwd=str(ARION))
            ch=len([l for l in r2.stdout.strip().split('\n') if l.strip()]) if r2.stdout.strip() else 0
            return {"recent_commits":c[:8],"uncommitted_changes":ch}
        except Exception as e: return {"error":str(e),"recent_commits":[],"uncommitted_changes":0}

    @staticmethod
    def system():
        try:
            with open('/proc/uptime') as f: us=float(f.readline().split()[0])
            r=subprocess.run(["free","-m"],capture_output=True,text=True,timeout=3)
            mp=r.stdout.strip().split('\n')[1].split(); mt,mu=int(mp[1]),int(mp[2])
            r=subprocess.run(["df","-h",str(HOME)],capture_output=True,text=True,timeout=3)
            dp=r.stdout.strip().split('\n')[1].split()
            return {"uptime":f"{int(us//3600)}h {int((us%3600)//60)}m","memory":f"{mu}/{mt}MB","mem_pct":round(mu/mt*100,1),"disk":f"{dp[2]}/{dp[1]}","disk_pct":dp[4]}
        except Exception as e: return {"error":str(e)}

class LS:
    def __init__(self):
        self.subs=[]; self._pos={}; self._on=False
    def start(self):
        if self._on: return
        self._on=True; threading.Thread(target=self._w,daemon=True).start()
    def stop(self): self._on=False
    def sub(self):
        q=queue.Queue(maxsize=300); self.subs.append(q); return q
    def unsub(self,q):
        if q in self.subs: self.subs.remove(q)
    def _bc(self,t,d):
        dead=[]
        for q in self.subs:
            try: q.put_nowait({"type":t,"data":d,"ts":datetime.now().isoformat()})
            except queue.Full: dead.append(q)
        for x in dead: self.subs.remove(x)
    def _w(self):
        while self._on:
            for n,p in LOGS.items():
                try:
                    if not p.exists(): continue
                    sz=p.stat().st_size; lp=self._pos.get(n,max(0,sz-4096))
                    if sz>lp:
                        with open(p,'r',errors='replace') as f:
                            f.seek(lp); nc=f.read(8192); self._pos[n]=f.tell()
                        if nc.strip():
                            for l in nc.strip().split('\n')[-30:]:
                                if l.strip(): self._bc("log",{"source":n,"line":l.strip()[:500]})
                    elif sz<lp: self._pos[n]=0
                except: pass
            time.sleep(1)

ls=LS()

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        p=self.path.split('?')[0]
        if p=='/': self._html()
        elif p=='/api/state': self._st()
        elif p=='/api/stream': self._sse()
        elif p=='/api/logs': self._lg()
        else: self.send_error(404)
    def do_POST(self):
        p=self.path.split('?')[0]
        if p=='/api/execute': self._ex()
        elif p=='/api/task': self._tk()
        else: self.send_error(404)
    def _st(self):
        self._j({"ts":datetime.now().isoformat(),"worker":S.worker(),"tasks":S.tasks(),"obres":S.obres(),"daily":S.daily(),"claude_session":S.claude_session(),"venice":S.venice_diem(),"openclaw":S.openclaw(),"git":S.git(),"system":S.system()})
    def _sse(self):
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream')
        self.send_header('Cache-Control','no-cache')
        self.send_header('Connection','keep-alive')
        self.end_headers()
        q=ls.sub()
        try:
            while True:
                try:
                    ev=q.get(timeout=15)
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode()); self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(f"data: {json.dumps({'type':'heartbeat'})}\n\n".encode()); self.wfile.flush()
        except(BrokenPipeError,ConnectionResetError,OSError): pass
        finally: ls.unsub(q)
    def _lg(self):
        pa=parse_qs(self.path.split('?')[1] if '?' in self.path else '')
        src=pa.get('source',['worker'])[0]; n=int(pa.get('n',['50'])[0])
        lp=LOGS.get(src); lines=[]
        if lp and lp.exists():
            try: lines=subprocess.run(["tail",f"-{n}",str(lp)],capture_output=True,text=True,timeout=5).stdout.strip().split('\n')
            except: pass
        self._j({"source":src,"lines":lines})
    def _ex(self):
        try:
            b=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            c=b.get('command','').strip()
            ok=any(c.startswith(p) for p in ['tail','head','cat','ls','grep','wc','find','ps aux','df','free','uptime','git log','git status','git diff','bash ~/biblioteca-universal-arion/scripts/','kill ','pkill -f claude-worker','pkill -f dashboard','source ~/.nvm/nvm.sh','bankr'])
            if not ok: return self._j({"error":"Comanda no permesa"},403)
            r=subprocess.run(["bash","-c",c],capture_output=True,text=True,timeout=30,cwd=str(ARION))
            self._j({"stdout":r.stdout[-4000:],"stderr":r.stderr[-2000:],"code":r.returncode})
        except Exception as e: self._j({"error":str(e)},500)
    def _tk(self):
        try:
            b=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            inst=b.get('instruction','')
            if not inst: return self._j({"error":"No instruction"},400)
            TASKS.mkdir(parents=True,exist_ok=True)
            ts=datetime.now().strftime("%Y%m%d_%H%M%S")
            (TASKS/f"dashboard_{b.get('type','custom')}_{ts}.json").write_text(json.dumps({"type":b.get('type','custom'),"instruction":inst,"created":datetime.now().isoformat(),"source":"dashboard"},indent=2))
            self._j({"ok":True})
        except Exception as e: self._j({"error":str(e)},500)
    def _j(self,d,c=200):
        try:
            p=json.dumps(d,ensure_ascii=False).encode()
            self.send_response(c); self.send_header('Content-Type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(p)
        except(BrokenPipeError,ConnectionResetError,OSError): pass
    def _html(self):
        try:
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(HTML.encode())
        except(BrokenPipeError,ConnectionResetError,OSError): pass

HTML=r"""<!DOCTYPE html>
<html lang="ca"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Arion Mission Control</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
:root{--v:#0a0b0f;--p:#111318;--c:#181b22;--e:#1f232c;--h:#252a35;--b:#2a2f3a;--ba:#3d4455;--g:#c9a227;--gb:#e8c84a;--gd:#8a7018;--em:#34d399;--ed:#065f46;--r:#f87171;--rd:#7f1d1d;--am:#fbbf24;--ad:#78350f;--bl:#60a5fa;--bd:#1e3a5f;--pu:#a78bfa;--cy:#22d3ee;--t1:#e8eaf0;--t2:#8b92a5;--t3:#555c6e}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Outfit',sans-serif;background:var(--v);color:var(--t1);height:100vh;overflow:hidden}
.hdr{background:var(--p);border-bottom:1px solid var(--b);padding:.5rem 1.25rem;display:flex;justify-content:space-between;align-items:center;height:48px;flex-shrink:0}
.hdr-l{display:flex;align-items:center;gap:1rem}.logo{font-size:1.2rem;font-weight:800;background:linear-gradient(135deg,var(--gb),var(--g));-webkit-background-clip:text;-webkit-text-fill-color:transparent}.logo-s{font-size:.6rem;color:var(--t3);letter-spacing:2px;text-transform:uppercase}
.hdr-r{display:flex;align-items:center;gap:1.25rem}.hs{display:flex;align-items:center;gap:.35rem;font-size:.75rem;color:var(--t2);font-family:'JetBrains Mono',monospace}
.dot{width:7px;height:7px;border-radius:50%;background:var(--em);animation:pu 2s ease-in-out infinite}.dot.off{background:var(--r);animation:none}.dot.wa{background:var(--am);animation:pu 1s infinite}
@keyframes pu{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(52,211,153,.4)}50%{opacity:.6;box-shadow:0 0 0 5px rgba(52,211,153,0)}}
.rl{background:linear-gradient(90deg,var(--rd),var(--ad));padding:.25rem 1rem;text-align:center;font-size:.72rem;font-weight:600;color:var(--am);display:none;flex-shrink:0}.rl.on{display:block;animation:bk 2s infinite}@keyframes bk{0%,100%{opacity:1}50%{opacity:.5}}
.main{display:flex;height:calc(100vh - 48px);overflow:hidden}
.cl{flex:1;display:flex;flex-direction:column;border-right:1px solid var(--b);min-width:0}
.cr{width:380px;overflow-y:auto;flex-shrink:0;background:var(--v)}.cr::-webkit-scrollbar{width:4px}.cr::-webkit-scrollbar-thumb{background:var(--ba);border-radius:2px}
.pnl{padding:.8rem 1rem;border-bottom:1px solid var(--b)}.pt{font-size:.65rem;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;color:var(--t3);margin-bottom:.6rem;display:flex;justify-content:space-between;align-items:center}
.bd{font-size:.6rem;padding:.12rem .45rem;border-radius:8px;font-weight:500}.bo{background:var(--ed);color:var(--em)}.bw{background:var(--ad);color:var(--am)}.be{background:var(--rd);color:var(--r)}.bi{background:var(--bd);color:var(--bl)}
.gr{display:flex;align-items:center;gap:1rem;margin-bottom:.5rem}.ring{position:relative;width:72px;height:72px;flex-shrink:0}.ring svg{transform:rotate(-90deg);width:72px;height:72px}.ring .bg{fill:none;stroke:var(--b);stroke-width:5}.ring .fg{fill:none;stroke:var(--g);stroke-width:5;stroke-linecap:round;transition:stroke-dashoffset .8s ease}.ring .ctr{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}
.gpct{font-size:1.1rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--gb)}.glbl{font-size:.45rem;color:var(--t3);text-transform:uppercase;letter-spacing:1px}.gi{flex:1}.gi .big{font-size:.85rem;font-weight:600;margin-bottom:.15rem}.gi .sm{font-size:.68rem;color:var(--t3);line-height:1.4}
.sg{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem}.sb{text-align:center;padding:.35rem .25rem;background:var(--c);border-radius:5px}.sv{font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace}.sl{font-size:.55rem;color:var(--t3);text-transform:uppercase;letter-spacing:.5px}
.lst{display:flex;flex-direction:column;gap:1px}
.or{display:flex;align-items:center;gap:.4rem;padding:.3rem .4rem;border-radius:3px;font-size:.72rem}.or:hover{background:var(--h)}.od{width:7px;height:7px;border-radius:50%;flex-shrink:0}.od.validated{background:var(--em)}.od.translated{background:var(--bl)}.od.needs_fix{background:var(--am)}.od.fixing{background:var(--am);animation:pu 1s infinite}.od.has_original{background:var(--t3)}.od.empty{background:var(--b)}
.on2{flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.oa{color:var(--t3);font-size:.62rem;flex-shrink:0}.os{font-family:'JetBrains Mono',monospace;font-size:.68rem;font-weight:600;flex-shrink:0}.os.hi{color:var(--em)}.os.mid{color:var(--am)}.os.lo{color:var(--r)}
.tr2{padding:.3rem .4rem;border-radius:3px;font-size:.7rem;border-left:3px solid transparent;display:flex;align-items:center;gap:.4rem}.tr2:hover{background:var(--h)}.tr2.pending{border-left-color:var(--t3)}.tr2.running{border-left-color:var(--bl);background:rgba(30,58,95,.3)}.tr2.done{border-left-color:var(--em);opacity:.5}.tr2.failed{border-left-color:var(--r);opacity:.6}
.tt{font-family:'JetBrains Mono',monospace;font-size:.55rem;padding:.08rem .25rem;border-radius:3px;background:var(--e);color:var(--t2);flex-shrink:0}.td2{flex:1;color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gtr{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:var(--t2);padding:.15rem 0;display:flex;gap:.4rem}.gtr .gh{color:var(--gd);flex-shrink:0}.gtr .gm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sr{display:flex;justify-content:space-between;font-size:.7rem;padding:.15rem 0}.sr .k{color:var(--t3)}.sr .vl{font-family:'JetBrains Mono',monospace;color:var(--t2)}
.tm{flex:1;display:flex;flex-direction:column;min-height:0}.tabs{display:flex;border-bottom:1px solid var(--b);background:var(--c);flex-shrink:0}
.tab{padding:.35rem .75rem;font-size:.68rem;font-weight:500;color:var(--t3);cursor:pointer;border-bottom:2px solid transparent;font-family:'JetBrains Mono',monospace;transition:all .15s}.tab:hover{color:var(--t2);background:var(--h)}.tab.on{color:var(--g);border-bottom-color:var(--g);background:var(--e)}
.tb{flex:1;overflow-y:auto;padding:.4rem;font-family:'JetBrains Mono',monospace;font-size:.7rem;line-height:1.5;min-height:0;background:var(--v)}.tb::-webkit-scrollbar{width:4px}.tb::-webkit-scrollbar-thumb{background:var(--ba);border-radius:2px}
.ll{padding:1px 4px;border-radius:2px;white-space:pre-wrap;word-break:break-all}.ll:hover{background:var(--h)}.ll .s{color:var(--t3);margin-right:.4rem;font-size:.6rem}.ll.src-openclaw .s{color:var(--pu)}.ll.src-worker .s{color:var(--bl)}.ll.src-claude_result .s{color:var(--g)}.ll.src-claude_live .s{color:var(--cy);font-weight:600}.ll.src-cmd .s{color:var(--cy)}
.ll .t{color:var(--t3);font-size:.6rem;margin-right:.35rem}.ll .c{color:#4ade80}.ll .c.err{color:var(--r)}.ll .c.warn{color:var(--am)}.ll .c.ok{color:var(--em)}.ll .c.think{color:var(--cy);font-style:italic}
.ti{display:flex;align-items:center;padding:.35rem .5rem;border-top:1px solid var(--b);background:var(--c);flex-shrink:0}.ti .pr{color:var(--g);font-family:'JetBrains Mono',monospace;font-size:.72rem;margin-right:.35rem}
.ti input{flex:1;background:transparent;border:none;color:var(--t1);font-family:'JetBrains Mono',monospace;font-size:.72rem;outline:none}
@media(max-width:900px){.cr{width:320px}}@media(max-width:700px){.main{flex-direction:column}.cr{width:100%;height:50vh}}
</style></head><body>
<div class="rl" id="rl">⚠ RATE LIMIT — Claude en pausa</div>
<header class="hdr"><div class="hdr-l"><div><div class="logo">ARION</div><div class="logo-s">Mission Control</div></div></div>
<div class="hdr-r"><div class="hs"><div class="dot" id="wd"></div><span id="wl">Worker</span></div><div class="hs"><div class="dot" id="ocd"></div><span>OpenClaw</span></div><div class="hs" style="color:var(--t3)" id="ck"></div></div></header>
<div class="main"><div class="cl"><div class="tm">
<div class="tabs"><div class="tab on" data-s="all" onclick="stab(this)">Tot</div><div class="tab" data-s="openclaw" onclick="stab(this)">OpenClaw</div><div class="tab" data-s="worker" onclick="stab(this)">Worker</div><div class="tab" data-s="claude_result" onclick="stab(this)">Claude Output</div><div class="tab" data-s="claude_live" onclick="stab(this)">Claude Live</div></div>
<div class="tb" id="tb"></div>
<div class="ti"><span class="pr">arion $</span><input id="cmd" placeholder="tail, grep, git log, ps aux..." onkeydown="if(event.key==='Enter')rc()"/></div>
</div></div>
<div class="cr">
<div class="pnl"><div class="pt">Sessió Claude <span class="bd" id="cb">—</span></div>
<div class="gr"><div class="ring"><svg viewBox="0 0 72 72"><circle class="bg" cx="36" cy="36" r="30"/><circle class="fg" id="crg" cx="36" cy="36" r="30" stroke-dasharray="188.5" stroke-dashoffset="188.5"/></svg><div class="ctr"><div class="gpct" id="cpct">—</div><div class="glbl" id="cgl">usat</div></div></div>
<div class="gi"><div class="big" id="crst">Carregant...</div><div class="sm" id="cdtl">Claude Max · Opus 4.6</div></div></div></div>
<div class="pnl"><div class="pt">Consum Diari <span class="bd bi">avui</span></div>
<div class="sg"><div class="sb"><div class="sv" style="color:var(--em)" id="dd">0</div><div class="sl">Fetes</div></div><div class="sb"><div class="sv" style="color:var(--r)" id="df">0</div><div class="sl">Fallides</div></div><div class="sb"><div class="sv" style="color:var(--am)" id="dr">0</div><div class="sl">Rate Limits</div></div></div>
<div style="margin-top:.4rem;font-size:.65rem;color:var(--t3);text-align:center" id="dc">—</div></div>
<div class="pnl"><div class="pt">Venice / DIEM <span class="bd" id="vb">—</span></div><div id="venice-info" style="font-family:'JetBrains Mono',monospace;font-size:.7rem;color:var(--t2);white-space:pre-wrap;max-height:80px;overflow-y:auto;background:var(--c);padding:.4rem;border-radius:4px">Carregant...</div></div>
<div class="pnl"><div class="pt">Worker <span class="bd" id="wb2">—</span></div><div style="display:flex;gap:.4rem;flex-wrap:wrap"><button onclick="workerCmd('restart')" style="padding:.3rem .6rem;background:var(--bd);color:var(--bl);border:none;border-radius:4px;font-size:.65rem;cursor:pointer;font-family:'JetBrains Mono',monospace">⟳ Restart</button><button onclick="workerCmd('stop')" style="padding:.3rem .6rem;background:var(--rd);color:var(--r);border:none;border-radius:4px;font-size:.65rem;cursor:pointer;font-family:'JetBrains Mono',monospace">⏹ Stop</button><button onclick="workerCmd('status')" style="padding:.3rem .6rem;background:var(--e);color:var(--t2);border:none;border-radius:4px;font-size:.65rem;cursor:pointer;font-family:'JetBrains Mono',monospace">📊 Estat</button></div><div id="worker-info" style="margin-top:.4rem;font-family:'JetBrains Mono',monospace;font-size:.65rem;color:var(--t3)"></div></div>
<div class="pnl"><div class="pt">Obres <span class="bd bi" id="oc">0</span></div><div class="lst" id="ol" style="max-height:240px;overflow-y:auto"></div></div>
<div class="pnl"><div class="pt">Tasques <span class="bd bi" id="tc">0</span></div><div class="lst" id="tl" style="max-height:200px;overflow-y:auto"></div></div>
<div class="pnl"><div class="pt">Git <span class="bd" id="gb2">—</span></div><div class="lst" id="gl"></div></div>
<div class="pnl"><div class="pt">Sistema</div><div id="si"></div></div>
</div></div>
<script>
let fi='all',L=[],as2=!0;const MX=600;
setInterval(()=>{document.getElementById('ck').textContent=new Date().toLocaleTimeString('ca-ES')},1000);
function csse(){const e=new EventSource('/api/stream');e.onmessage=v=>{const d=JSON.parse(v.data);if(d.type==='log')al(d.data.source,d.data.line,d.ts)};e.onerror=()=>{e.close();setTimeout(csse,3000)}}
function al(s,t,ts){const l={s,t,ts};L.push(l);if(L.length>MX)L.shift();if(fi==='all'||fi===s)rl2(l)}
function rl2(l){const e=document.getElementById('tb'),d=document.createElement('div');d.className='ll src-'+l.s;let cl='';const lo=l.t.toLowerCase();if(lo.includes('error')||lo.includes('❌')||lo.includes('failed'))cl='err';else if(lo.includes('warning')||lo.includes('⚠')||lo.includes('rate limit'))cl='warn';else if(lo.includes('✅')||lo.includes('completada')||lo.includes('validated'))cl='ok';else if(lo.includes('thinking')||lo.includes('analitz')||lo.includes('traduint')||lo.includes('processing'))cl='think';const tm=l.ts?new Date(l.ts).toLocaleTimeString('ca-ES',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';const sn={openclaw:'OCLAW',worker:'WORKR',claude_result:'CLAUD',claude_status:'CSTAT',claude_live:'LIVE✦',cmd:'CMD'}[l.s]||l.s.slice(0,5).toUpperCase();d.innerHTML=`<span class="t">${tm}</span><span class="s">[${sn}]</span><span class="c ${cl}">${esc(l.t)}</span>`;e.appendChild(d);if(as2)e.scrollTop=e.scrollHeight;while(e.children.length>MX)e.removeChild(e.firstChild)}
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
function stab(el){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');fi=el.dataset.s;const b=document.getElementById('tb');b.innerHTML='';(fi==='all'?L:L.filter(l=>l.s===fi)).slice(-300).forEach(rl2)}
function rc(){const i=document.getElementById('cmd'),c=i.value.trim();if(!c)return;i.value='';al('cmd','$ '+c,new Date().toISOString());fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:c})}).then(r=>r.json()).then(d=>{if(d.error)al('cmd','ERROR: '+d.error,new Date().toISOString());else{if(d.stdout)d.stdout.split('\n').forEach(l=>{if(l.trim())al('cmd',l,new Date().toISOString())});if(d.stderr)d.stderr.split('\n').forEach(l=>{if(l.trim())al('cmd','⚠ '+l,new Date().toISOString())})}}).catch(e=>al('cmd','ERR: '+e.message,new Date().toISOString()))}
document.getElementById('tb').addEventListener('scroll',function(){as2=(this.scrollHeight-this.scrollTop-this.clientHeight)<50});
function rf(){fetch('/api/state').then(r=>r.json()).then(ui).catch(e=>console.error(e))}
function ui(d){
document.getElementById('wd').className=d.worker.claude_active?'dot':d.worker.running?'dot':'dot off';
document.getElementById('wl').textContent=d.worker.claude_active?'Worker ⚡':d.worker.running?'Worker':'Worker OFF';
document.getElementById('ocd').className=d.openclaw.running?'dot':'dot off';
document.getElementById('rl').className=d.claude_session&&d.claude_session.is_rate_limited?'rl on':'rl';
uc(d.claude_session,d.daily);ud(d.daily);uv(d.venice);uo(d.obres);ut(d.tasks);ug(d.git);us(d.system);uw(d.worker)}
function uc(s,dy){const b=document.getElementById('cb'),r=document.getElementById('crg'),p=document.getElementById('cpct'),rs=document.getElementById('crst'),dt=document.getElementById('cdtl'),gl=document.getElementById('cgl');if(!s)return;if(s.is_rate_limited){b.textContent='Rate Limited';b.className='bd bw';p.textContent='⏸';p.style.color='var(--r)';rs.textContent=s.reset_info||'En pausa';r.style.stroke='var(--r)';r.style.strokeDashoffset=0;gl.textContent='pausat'}else{b.textContent='Activa';b.className='bd bo';p.style.color='var(--gb)';const td=dy?dy.today_done||0:0;p.textContent=td;gl.textContent='avui';rs.textContent='Sessió activa';dt.textContent='Claude Max · Opus 4.6'+(dy&&dy.worker_uptime&&dy.worker_uptime!=='—'?' · Worker '+dy.worker_uptime:'');const pv=Math.min(100,(td/50)*100),ci=188.5;r.style.strokeDashoffset=ci-(ci*pv/100);r.style.stroke=pv>80?'var(--am)':'var(--g)'}}
function ud(dy){if(!dy)return;document.getElementById('dd').textContent=dy.today_done||0;document.getElementById('df').textContent=dy.today_failed||0;document.getElementById('dr').textContent=dy.today_rate_limits||0;const y=dy.yesterday_done||0,t=dy.today_done||0;document.getElementById('dc').textContent=y>0?(t>=y?'+':'')+(t-y)+' vs ahir ('+y+')':'—'}
function uo(o){if(!o)return;const el=document.getElementById('ol'),c=document.getElementById('oc'),ct={};o.forEach(x=>ct[x.status]=(ct[x.status]||0)+1);c.textContent=o.length+' · ✅'+(ct.validated||0)+' · 🔧'+((ct.needs_fix||0)+(ct.fixing||0));o.sort((a,b)=>{const od={validated:0,fixing:1,needs_fix:2,translated:3,has_original:4,empty:5};return(od[a.status]||5)-(od[b.status]||5)});el.innerHTML=o.map(x=>{let s='',sc='';if(x.score!=null){s=x.score.toFixed(1);sc=x.score>=7.5?'hi':x.score>=5?'mid':'lo'}return`<div class="or"><div class="od ${x.status}"></div><span class="on2">${esc(x.obra)}</span><span class="oa">${esc(x.autor)}</span>${s?`<span class="os ${sc}">${s}</span>`:''}</div>`}).join('')}
function ut(t){if(!t)return;const el=document.getElementById('tl'),c=document.getElementById('tc');c.textContent=t.counts.pending+' pend · '+t.counts.running+' act · '+t.counts.done+' ok';const a=[...t.running.map(x=>({...x,st:'running'})),...t.pending.map(x=>({...x,st:'pending'})),...t.failed.map(x=>({...x,st:'failed'})),...t.done.slice(-5).map(x=>({...x,st:'done'}))];el.innerHTML=a.map(x=>`<div class="tr2 ${x.st}"><span class="tt">${esc(x.type||'?')}</span><span class="td2">${esc(x.instruction||x.name)}</span></div>`).join('')}
function ug(g){if(!g)return;const b=document.getElementById('gb2');b.textContent=(g.uncommitted_changes||0)+' canvis';b.className=g.uncommitted_changes>0?'bd bw':'bd bo';document.getElementById('gl').innerHTML=(g.recent_commits||[]).map(c=>{const p=c.split(' ');return`<div class="gtr"><span class="gh">${p[0]}</span><span class="gm">${esc(p.slice(1).join(' '))}</span></div>`}).join('')}
function us(s){if(!s)return;document.getElementById('si').innerHTML=[['Uptime',s.uptime||'—'],['Memòria',(s.memory||'—')+' ('+(s.mem_pct||0)+'%)'],['Disc',(s.disk||'—')+' ('+(s.disk_pct||'?')+')']].map(([k,v])=>`<div class="sr"><span class="k">${k}</span><span class="vl">${v}</span></div>`).join('')}
function uv(v){if(!v)return;const b=document.getElementById('vb'),el=document.getElementById('venice-info');if(!v.available){b.textContent='Offline';b.className='bd bw';el.textContent=v.raw||'No disponible';return}b.textContent='Actiu';b.className='bd bo';if(v.data){const d=v.data;let txt='';if(d.diem_balance!=null)txt+='DIEM Balance: '+d.diem_balance+'\n';if(d.diem_daily_allowance!=null)txt+='DIEM Diari: '+d.diem_daily_allowance+'\n';if(d.diem_used_today!=null)txt+='DIEM Usat Avui: '+d.diem_used_today+'\n';if(d.usd_balance!=null)txt+='USD: $'+d.usd_balance+'\n';if(d.credits!=null)txt+='Crèdits: '+d.credits+'\n';if(d.credit_balance!=null)txt+='Crèdits: '+d.credit_balance+'\n';if(d.daily_usage!=null)txt+='Ús diari: '+JSON.stringify(d.daily_usage)+'\n';if(d.epoch_reset_time)txt+='Reset: '+new Date(d.epoch_reset_time*1000).toLocaleTimeString('ca-ES')+'\n';if(d.balance!=null&&typeof d.balance==='object'){for(const[k,val] of Object.entries(d.balance)){txt+=k+': '+val+'\n'}}else if(d.balance!=null){txt+='Balance: '+d.balance+'\n'}if(!txt)txt=JSON.stringify(d,null,1);el.textContent=txt.trim()}else{el.textContent=v.raw||'Sense dades'}}
function uw(w){if(!w)return;const b=document.getElementById('wb2'),el=document.getElementById('worker-info');if(w.running){b.textContent=w.claude_active?'Processant':'Actiu';b.className=w.claude_active?'bd bw':'bd bo'}else{b.textContent='Aturat';b.className='bd be'}el.textContent=w.current_task?'Tasca: '+w.current_task:''}
function workerCmd(action){const el=document.getElementById('worker-info');el.textContent='Executant...';let cmd='';if(action==='restart'){cmd='kill $(cat /tmp/worker.pid) 2>/dev/null; sleep 2; bash ~/biblioteca-universal-arion/scripts/start-worker.sh'}else if(action==='stop'){cmd='kill $(cat /tmp/worker.pid) 2>/dev/null; rm -f ~/.openclaw/workspace/tasks/worker.lock'}else if(action==='status'){cmd='ps aux | grep claude-worker | grep -v grep; echo "---"; cat /tmp/worker.pid 2>/dev/null; echo "---"; ls ~/.openclaw/workspace/tasks/*.json 2>/dev/null | wc -l'}fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd})}).then(r=>r.json()).then(d=>{if(d.error)el.textContent='Error: '+d.error;else el.textContent=(d.stdout||'').slice(-200);setTimeout(rf,2000)}).catch(e=>el.textContent='Error: '+e.message)}
function li(){['worker','openclaw','claude_result','claude_live'].forEach(s=>{fetch('/api/logs?source='+s+'&n=40').then(r=>r.json()).then(d=>{if(d.lines)d.lines.forEach(l=>{if(l.trim())al(s,l,new Date().toISOString())})}).catch(()=>{})})}
csse();li();rf();setInterval(rf,10000);
</script></body></html>"""

class TS(socketserver.ThreadingMixIn,http.server.HTTPServer):
    allow_reuse_address=True; daemon_threads=True

def main():
    print(f"\n╔══════════════════════════════════════════════════╗\n║       ARION MISSION CONTROL — v4                 ║\n║       http://localhost:{PORT}                       ║\n╚══════════════════════════════════════════════════╝\n")
    ls.start(); srv=TS(("0.0.0.0",PORT),H)
    print(f"  Port {PORT} | {len(LOGS)} log fonts | Ctrl+C per aturar\n")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Bye"); ls.stop(); srv.shutdown()

if __name__=="__main__":
    import sys
    if "--port" in sys.argv:
        i=sys.argv.index("--port")
        if i+1<len(sys.argv): PORT=int(sys.argv[i+1])
    main()
