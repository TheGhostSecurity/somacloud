package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net/http"
	"strings"
)

const flag = "FLAG{xss_is_not_a_dinosaur}"

type feedback struct {
	User, Msg string
}

var users = map[string]string{"admin": "admin123", "guest": "guest123"}
var sessions = map[string]string{}
var board []feedback

func token() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func index(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>XSS Lab</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:32px;width:380px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}.sub{color:#5c5c5c;margin:0 0 20px;font-size:0.9rem}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:12px;box-sizing:border-box}
button{width:100%;background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600}
.hint{margin-top:12px;font-size:0.8rem;color:#5c5c5c}
</style></head><body>
<div class="card"><h1>XSS Lab</h1><p class="sub">Globex Feedback Board - login</p>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="Username">
<input type="password" name="password" placeholder="Password">
<button type="submit">Login</button></form>
<p class="hint">Use: admin / admin123 or guest / guest123</p>
</div></body></html>`)
}

func doLogin(w http.ResponseWriter, r *http.Request) {
	r.ParseForm()
	u := r.FormValue("username")
	p := r.FormValue("password")
	if users[u] != p {
		http.Redirect(w, r, "/?err=1", 302)
		return
	}
	t := token()
	sessions[t] = u
	http.SetCookie(w, &http.Cookie{Name: "sid", Value: t, Path: "/"})
	http.Redirect(w, r, "/dashboard", 302)
}

func dashboard(w http.ResponseWriter, r *http.Request) {
	c, err := r.Cookie("sid")
	if err != nil || sessions[c.Value] == "" {
		http.Redirect(w, r, "/", 302)
		return
	}
	uname := sessions[c.Value]

	if r.Method == "POST" {
		r.ParseForm()
		msg := r.FormValue("message")
		if msg != "" {
			board = append([]feedback{{uname, msg}}, board...)
		}
	}

	list := ""
	for _, f := range board {
		list += `<div class="comment"><strong>` + f.User + `:</strong> ` + f.Msg + `</div>`
	}

	proved := false
	for _, f := range board {
		low := strings.ToLower(f.Msg)
		if strings.Contains(low, "<script") || strings.Contains(low, "onerror") {
			proved = true
		}
	}
	flagCard := ""
	if proved {
		flagCard = `<div class="card"><h2>Flag</h2><p class="flag">` + flag + `</p></div>
<p class="hint">Stored XSS confirmed: an unescaped payload now lives in the board and executes for every viewer.</p>`
	}

	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Feedback Board</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}h2{font-size:1rem;margin:0 0 12px}
textarea{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px;min-height:80px;box-sizing:border-box;font-family:monospace}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600}
.comment{border-bottom:1px solid #eee;padding:10px 0;font-size:0.9rem}.comment strong{color:#0067c0}
.flag{font-family:monospace;font-size:1.1rem;color:#107c41;background:#ecfdf3;padding:12px;border-radius:8px;text-align:center;border:1px solid #86efac}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
</style></head><body>
<div class="card"><h1>Feedback Board</h1><p>Logged in as: <strong>%s</strong></p></div>
<div class="card"><h2>Post Feedback</h2>
<form method="POST"><textarea name="message" placeholder="Write your feedback..."></textarea><button type="submit">Submit</button></form>
<p class="hint">Try: <b>&lt;script&gt;alert('XSS')&lt;/script&gt;</b> or <b>&lt;img src=x onerror=alert(1)&gt;</b></p>
</div>
<div class="card"><h2>Recent Feedback</h2>%s</div>
%s
<div class="card"><a href="/">Logout</a></div>
</body></html>`, uname, list, flagCard)
}

func main() {
	http.HandleFunc("/", index)
	http.HandleFunc("/login", doLogin)
	http.HandleFunc("/dashboard", dashboard)
	http.ListenAndServe(":80", nil)
}