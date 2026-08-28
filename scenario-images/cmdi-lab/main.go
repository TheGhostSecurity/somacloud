package main

import (
	"fmt"
	"html/template"
	"net/http"
	"os/exec"
)

func index(w http.ResponseWriter, r *http.Request) {
	target := ""
	output := ""
	if r.Method == "POST" {
		r.ParseForm()
		target = r.FormValue("target")
		cmd := exec.Command("sh", "-c", "ping -c 2 "+target)
		out, err := cmd.CombinedOutput()
		if err != nil {
			output = string(out) + "\n" + err.Error()
		} else {
			output = string(out)
		}
	}
	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CMDi Lab</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}h2{font-size:1rem;margin:0 0 12px}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px;box-sizing:border-box}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:12px;white-space:pre-wrap;word-break:break-all}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
</style></head><body>
<div class="card"><h1>Network Ping Tool</h1><p class="hint">Globex ops utility - enter an IP address to ping.</p>
<form method="POST"><input type="text" name="target" placeholder="e.g. 127.0.0.1" value="%s"><button type="submit">Ping</button></form>
<p class="hint">Try: <b>127.0.0.1; cat /flag.txt</b></p>
</div>
<div class="card"><h2>Output</h2><pre>%s</pre></div>
</body></html>`, template.HTMLEscapeString(target), template.HTMLEscapeString(output))
}

func main() {
	http.HandleFunc("/", index)
	http.ListenAndServe(":80", nil)
}