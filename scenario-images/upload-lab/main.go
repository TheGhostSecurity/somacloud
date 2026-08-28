package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

var users = map[string]string{"user": "user123", "admin": "admin123"}
var sessions = map[string]string{}

func token() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func login(w http.ResponseWriter, r *http.Request) {
	if r.Method == "POST" {
		r.ParseForm()
		u := r.FormValue("username")
		p := r.FormValue("password")
		if users[u] == p {
			t := token()
			sessions[t] = u
			http.SetCookie(w, &http.Cookie{Name: "sid", Value: t, Path: "/"})
			http.Redirect(w, r, "/", 302)
			return
		}
	}
	fmt.Fprint(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Upload Lab</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:32px;width:380px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}.sub{color:#5c5c5c;margin:0 0 20px;font-size:0.9rem}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:12px;box-sizing:border-box}
button{width:100%;background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600}
.hint{margin-top:12px;font-size:0.8rem;color:#5c5c5c}
</style></head><body>
<div class="card"><h1>Upload Lab</h1><p class="sub">Globex Profile Manager - login</p>
<form method="POST"><input type="text" name="username" placeholder="Username"><input type="password" name="password" placeholder="Password"><button type="submit">Login</button></form>
<p class="hint">Use: user / user123</p></div></body></html>`)
}

func index(w http.ResponseWriter, r *http.Request) {
	c, err := r.Cookie("sid")
	if err != nil || sessions[c.Value] == "" {
		http.Redirect(w, r, "/login", 302)
		return
	}
	uname := sessions[c.Value]

	msg := ""
	if r.Method == "POST" {
		r.ParseMultipartForm(2 << 20)
		f, h, err := r.FormFile("avatar")
		if err == nil {
			defer f.Close()
			name := filepath.Base(h.Filename)
			dst, err := os.Create("/srv/uploads/" + name)
			if err == nil {
				_, err = io.Copy(dst, f)
				dst.Close()
				if err == nil {
					msg = "File uploaded: " + name
				}
			}
		}
	}

	list := ""
	entries, _ := os.ReadDir("/srv/uploads")
	for _, e := range entries {
		list += `<a href="/uploads/` + e.Name() + `">` + e.Name() + `</a> `
	}

	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Profile Manager</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}h2{font-size:1rem;margin:0 0 12px}
.success{color:#107c41}.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;text-decoration:none;display:inline-block;margin-right:8px}
</style></head><body>
<div class="card"><h1>Profile Manager</h1><p>Logged in as: <strong>%s</strong></p></div>
<div class="card"><h2>Upload Avatar</h2>
<p class="success">%s</p>
<form method="POST" enctype="multipart/form-data"><input type="file" name="avatar" accept="image/*"><button type="submit">Upload</button></form>
<p class="hint">No extension filtering. Upload a script and execute it with <b>/run?file=name</b> to read /flag.txt.</p>
</div>
<div class="card"><h2>Uploaded Files</h2>%s</div>
<div class="card"><a href="/login">Logout</a></div>
</body></html>`, template.HTMLEscapeString(uname), template.HTMLEscapeString(msg), list)
}

func serveUploads(w http.ResponseWriter, r *http.Request) {
	name := filepath.Base(r.URL.Path)
	data, err := os.ReadFile("/srv/uploads/" + name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Write(data)
}

func runScript(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("file")
	if name == "" {
		http.Error(w, "missing file", 400)
		return
	}
	path := "/srv/uploads/" + filepath.Base(name)
	cmd := exec.Command("sh", path)
	out, err := cmd.CombinedOutput()
	fmt.Fprintf(w, "<pre>%s%s</pre>", template.HTMLEscapeString(string(out)), template.HTMLEscapeString(errText(err)))
}

func errText(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}

func main() {
	os.MkdirAll("/srv/uploads", 0777)
	http.HandleFunc("/", index)
	http.HandleFunc("/login", login)
	http.HandleFunc("/uploads/", serveUploads)
	http.HandleFunc("/run", runScript)
	http.ListenAndServe(":80", nil)
}