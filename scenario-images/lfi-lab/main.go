package main

import (
	"fmt"
	"html/template"
	"net/http"
	"os"
	"path/filepath"
)

var pages = map[string]string{
	"info.php":    "Globex intranet info page. Nothing interesting here yet.",
	"about.php":   "About: Globex Corp adopted the new file viewer in Q3.",
	"contact.php": "Contact: shift-lead@globex.local (internal use only).",
}

func index(w http.ResponseWriter, r *http.Request) {
	file := r.URL.Query().Get("file")
	if file == "" {
		file = "info.php"
	}
	content := "Page not found: " + filepath.Base(file)
	raw := "/srv/www/" + file
	if data, err := os.ReadFile(raw); err == nil {
		content = string(data)
	} else if text, ok := pages[file]; ok {
		content = text
	}

	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>File Viewer</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}h2{font-size:1rem;margin:0 0 12px}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:12px;white-space:pre-wrap;word-break:break-all}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;margin-right:12px;text-decoration:none}
</style></head><body>
<div class="card"><h1>Globex File Viewer</h1><p>Select a page:</p>
<a href="/?file=info.php">Info</a><a href="/?file=about.php">About</a><a href="/?file=contact.php">Contact</a>
<p class="hint">Try: <b>?file=../../flag.txt</b></p>
</div>
<div class="card"><h2>File Content: %s</h2><pre>%s</pre></div>
</body></html>`, template.HTMLEscapeString(file), template.HTMLEscapeString(content))
}

func main() {
	http.HandleFunc("/", index)
	http.ListenAndServe(":80", nil)
}