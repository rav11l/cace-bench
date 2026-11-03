import concurrent.futures, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, time
SOURCE = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'results'
MODEL = 'gpt-6.1-sol via Codex CLI isolated sessions (unpinned, low effort)'
CLI = shutil.which('codex')

def worker(family):
    sys.path.insert(0, str(SOURCE))
    import proposer_llm as P
    directory = OUT / family
    directory.mkdir(parents=True, exist_ok=True)
    isolated = ROOT / ('isolated-' + family)
    isolated.mkdir(exist_ok=True)
    def call(user):
        key = hashlib.sha256(json.dumps([P.MODEL, P.SYSTEM, user]).encode()).hexdigest()
        P.Stats.calls += 1
        hit = P.CACHE.get(key)
        if hit is not None:
            P.Stats.cache_hits += 1
            return hit
        prompt = ('Respond to this benchmark task without using any tools, files, web, or other context. '
                  'Return only the requested JSON.\n\n' + P.SYSTEM + '\n\n' + user)
        started = time.time()
        command = [CLI, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                   '--sandbox', 'read-only', '-C', str(isolated), '-m', 'gpt-6.1-sol',
                   '-c', 'model_reasoning_effort="low"', '--json', '-']
        proc = subprocess.run(command, input=prompt, text=True, encoding='utf-8',
                              errors='replace', capture_output=True, timeout=180)
        events = []
        for line in proc.stdout.splitlines():
            try: events.append(json.loads(line))
            except json.JSONDecodeError: pass
        items = [e.get('item', {}) for e in events if e.get('type') == 'item.completed']
        prohibited = [e for e in items if e.get('type') not in ('agent_message', 'reasoning')]
        messages = [e['text'] for e in items if e.get('type') == 'agent_message']
        if proc.returncode or prohibited or not messages or not any(e.get('type') == 'turn.completed' for e in events):
            (directory / 'failure.json').write_text(json.dumps({'key':key,'returncode':proc.returncode,'events':events,'stderr':proc.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
            raise RuntimeError('Model call failed or used tools; see failure.json')
        response = messages[-1]
        # Preserve verbatim responses; the existing benchmark parser alone validates candidates.
        record = {'key':key,'system':P.SYSTEM,'prompt':user,'response':response,
                  'duration_seconds':time.time()-started,'completed_at':datetime.datetime.now(datetime.UTC).isoformat(),
                  'usage':[e.get('usage') for e in events if e.get('type')=='turn.completed']}
        with (directory / 'requests.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
        P.CACHE.put(key, hashlib.sha256(user.encode()).hexdigest(), response)
        print(f'{family}: model request saved, total calls {P.Stats.calls}, cache hits {P.Stats.cache_hits}',flush=True)
        return response
    P._call = call
    sys.argv = ['proposer_llm.py','--seeds','5','--families',family,'--severities','mid','--model',MODEL,'--out',str(directory)]
    P.main()
    return family

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    metadata = {'model':MODEL,'temperature':None,'reasoning_effort':'low','seeds':5,'families':['thr','scope','struct'],'severity':'mid','world':'synthetic','started_at':datetime.datetime.now(datetime.UTC).isoformat(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),'source_hashes':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ['proposer_llm.py','evolve.py']},'protocol_notes':['Codex agent system instructions also apply; not raw API equivalence.','One new ephemeral session per cache miss; tool-use responses are rejected.','Model snapshot and temperature cannot be pinned through this CLI.','No reference answers or source repository supplied to model.']}
    (ROOT/'manifest.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
            for fam in pool.map(worker,['thr','scope','struct']): print('COMPLETED '+fam,flush=True)
        combined=OUT/'combined'; combined.mkdir(exist_ok=True)
        with (combined/'llm_cache.jsonl').open('w',encoding='utf-8') as target:
            for fam in ['thr','scope','struct']:
                target.write((OUT/fam/'llm_cache.jsonl').read_text(encoding='utf-8'))
        cmd=[sys.executable,str(SOURCE/'proposer_llm.py'),'--seeds','5','--severities','mid','--model',MODEL,'--out',str(combined)]
        subprocess.run(cmd,cwd=SOURCE,check=True)
        subprocess.run([sys.executable,str(SOURCE/'tools/llm_tables.py'),str(combined),str(SOURCE/'results/shift'),'--severities','mid'],cwd=SOURCE,check=True)
        metadata['status']='completed'
    except Exception as e:
        metadata['status']='failed';metadata['error']=str(e)
        raise
    finally:
        metadata['updated_at']=datetime.datetime.now(datetime.UTC).isoformat()
        (ROOT/'manifest.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
