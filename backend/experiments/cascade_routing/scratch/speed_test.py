import http.client, json, time
for npred in [16, 128]:
    c = http.client.HTTPConnection("localhost", 11434, timeout=300)
    body = json.dumps({"model": "qwen2.5:latest", "prompt": "Ek cube ka surface area batao side 5 cm hai.",
                       "stream": False, "options": {"num_predict": npred}})
    t0 = time.time()
    c.request("POST", "/api/generate", body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    d = json.loads(r.read().decode())
    dt = time.time() - t0
    print(f"num_predict={npred} took {dt:.1f}s eval={d.get('eval_count')} eval_rate={d.get('eval_duration',0)/1e9:.1f}s prompt_eval={d.get('prompt_eval_duration',0)/1e9:.1f}s")
    c.close()
