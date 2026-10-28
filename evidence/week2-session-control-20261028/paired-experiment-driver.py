import sys,time,subprocess,json,platform,ssl,uuid
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
from importlib.metadata import version
sys.path.insert(0,str(Path('scripts').resolve()))
from local_tls_server import generate_self_signed_cert
import benchmark_tls as b
root=Path('.tmp/local-week2-paired-20261028-unique');root.mkdir(parents=True,exist_ok=False)
output=Path('results/week2/local-openssl41-paired-20261028');output.mkdir(parents=True,exist_ok=False)
cert,key=generate_self_signed_cert(root/'cert');exe=r'C:\Program Files\OpenSSL-Win64\bin\openssl.exe'
server=subprocess.Popen([exe,'s_server','-accept','127.0.0.1:19534','-cert',str(cert),'-key',str(key),'-tls1_3','-groups','X25519:X25519MLKEM768','-www'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
client_version=subprocess.run([exe,'version'],capture_output=True,text=True,check=True).stdout.strip()
common={'server_version':client_version,'server_configuration':'OpenSSL s_server -tls1_3 -groups X25519:X25519MLKEM768 -www; no client authentication or authorization','client_version':client_version,'network_path':'IPv4 loopback 127.0.0.1:19534','server_name':'localhost','trust':'ephemeral self-signed localhost certificate explicitly supplied to client','ordering':'hybrid, classical, classical, hybrid; two blocks of 50 attempts per mode','sample_count_rationale':'100 per mode rather than 1000: each process takes about 1 second; 1000 per mode would take over 35 minutes; p95/p99 are exploratory only','measurement_scope':'perf_counter_ns around verify_tls_group: process startup, TCP, TLS, certificate verification, output capture, shutdown and parsing; not isolated handshake latency','environment':platform.platform(),'python':sys.version,'python_ssl':ssl.OPENSSL_VERSION,'cryptography':version('cryptography'),'started_utc':datetime.now(timezone.utc).isoformat()}
(output/'experiment.json').write_text(json.dumps(common,indent=2),encoding='utf-8')
blocks={'classical':[],'hybrid':[]}; records={'classical':[],'hybrid':[]}
try:
 time.sleep(.7)
 if server.poll() is not None:raise RuntimeError('OpenSSL server failed to start')
 for idx,mode in enumerate(['hybrid','classical','classical','hybrid'],1):
  print(f'[{idx}/4] {mode}: 5 warm-ups, 50 attempts',flush=True)
  samples,meta=b.run_tls_benchmark(mode=mode,host='127.0.0.1',port=19534,server_name='localhost',ca_file=str(cert),warmup=5,iterations=50,timeout=5,openssl_path=exe,run_id=f'paired-{mode}-block-{idx}')
  meta['experiment_provenance']=common
  b.write_results(samples,meta,output/f'block-{idx}-{mode}')
  blocks[mode].append(samples);records[mode].append(meta)
  print(f'[{idx}/4] preserved {len(samples)} attempts',flush=True)
 for mode in ('classical','hybrid'):
  samples=[]
  for block in blocks[mode]:
   for sample in block:samples.append(replace(sample,attempt=len(samples)+1))
  successes=[s.latency_ms for s in samples if s.success]
  meta={'run_id':f'paired-{mode}-combined','mode':mode,'host':'127.0.0.1','port':19534,'expected_group':b.EXPECTED_GROUPS[mode],'warmup_connections':10,'measured_connections':len(samples),'successful_count':len(successes),'failed_count':len(samples)-len(successes),'success_rate':len(successes)/len(samples),'statistics':b.compute_statistics(successes),'preflight_verification':{'block_preflights':[m['preflight_verification'] for m in records[mode]]},'warmup_attempts':[s for m in records[mode] for s in m['warmup_attempts']],'experiment_provenance':common,'session_evidence':'OpenSSL normal output New/Reused TLSv1.3 per sample; unambiguous status only'}
  b.write_results(samples,meta,output/mode)
 print('Paired raw outputs saved. Session statuses:', {m:{str(s.session_reused) for block in blocks[m] for s in block} for m in blocks},flush=True)
finally:
 server.terminate();server.wait(timeout=5)
