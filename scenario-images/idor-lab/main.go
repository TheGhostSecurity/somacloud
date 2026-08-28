package main

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"html/template"
	"net/http"
	"strconv"
)

type profile struct {
	ID, Username, FullName, Email, Notes string
}

var users = []profile{
	{ID: "1", Username: "admin", FullName: "Admin User", Email: "admin@bank.local", Notes: "FLAG{idor_exploited_like_a_pro}"},
	{ID: "2", Username: "alice", FullName: "Alice Johnson", Email: "alice@bank.local", Notes: "Personal note: change passwords regularly"},
	{ID: "3", Username: "bob", FullName: "Bob Smith", Email: "bob@bank.local", Notes: "Buy flowers for the anniversary"},
	{ID: "4", Username: "carol", FullName: "Carol White", Email: "carol@bank.local", Notes: "Team offsite planned for Q4"},
}

var creds = map[string]string{"alice": "alice_pass", "bob": "bob_pass", "carol": "carol_pass"}
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
		if creds[u] == p {
			var id string
			for _, pr := range users {
				if pr.Username == u {
					id = pr.ID
				}
			}
			t := token()
			sessions[t] = id
			http.SetCookie(w, &http.Cookie{Name: "sid", Value: t, Path: "/"})
			http.Redirect(w, r, "/", 302)
			return
		}
	}
	fmt.Fprint(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>IDOR Lab</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:32px;width:380px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}.sub{color:#5c5c5c;margin:0 0 20px;font-size:0.9rem}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:12px;box-sizing:border-box}
button{width:100%;background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600}
.hint{margin-top:12px;font-size:0.8rem;color:#5c5c5c}
</style></head><body>
<div class="card"><h1>IDOR Lab</h1><p class="sub">GlobexBank User Profile Portal - login</p>
<form method="POST"><input type="text" name="username" placeholder="Username"><input type="password" name="password" placeholder="Password"><button type="submit">Login</button></form>
<p class="hint">Use: alice / alice_pass or bob / bob_pass</p></div></body></html>`)
}

func dashboard(w http.ResponseWriter, r *http.Request) {
	c, err := r.Cookie("sid")
	if err != nil {
		http.Redirect(w, r, "/login", 302)
		return
	}
	uid := sessions[c.Value]
	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Dashboard</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0}.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
a{color:#0067c0;text-decoration:none}
</style></head><body>
<div class="card"><h1>Welcome</h1><p>Your user ID: <strong>%s</strong></p><a href="/profile?id=%s">View My Profile</a></div>
<div class="card"><h1>IDOR Challenge</h1><p>The flag is stored in admin's profile notes (user ID 1).</p><p class="hint">Try: <b>/profile?id=1</b></p></div>
<div class="card"><a href="/login">Logout</a></div></body></html>`, uid, uid)
}

func profileView(w http.ResponseWriter, r *http.Request) {
	reqID := r.URL.Query().Get("id")
	if reqID == "" {
		c, err := r.Cookie("sid")
		if err != nil {
			http.Redirect(w, r, "/login", 302)
			return
		}
		reqID = sessions[c.Value]
	}
	var pr *profile
	if _, err := strconv.Atoi(reqID); err == nil {
		for i := range users {
			if users[i].ID == reqID {
				pr = &users[i]
			}
		}
	}
	if pr == nil {
		fmt.Fprint(w, `<html><body><h1>Profile</h1><p>User not found.</p></body></html>`)
		return
	}
	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>User Profile</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0}.label{font-weight:600;font-size:0.85rem;color:#5c5c5c}
pre{background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;font-size:0.85rem}
a{color:#0067c0}
</style></head><body>
<div class="card"><h1>Profile: %s</h1>
<div class="label">ID</div><p>%s</p>
<div class="label">Username</div><p>%s</p>
<div class="label">Full Name</div><p>%s</p>
<div class="label">Email</div><p>%s</p>
<div class="label">Notes</div><pre>%s</pre>
</div>
<div class="card"><a href="/">Back to Dashboard</a></div></body></html>`,
		template.HTMLEscapeString(pr.Username), pr.ID, template.HTMLEscapeString(pr.Username),
		template.HTMLEscapeString(pr.FullName), template.HTMLEscapeString(pr.Email), template.HTMLEscapeString(pr.Notes))
}

func main() {
	http.HandleFunc("/", dashboard)
	http.HandleFunc("/login", login)
	http.HandleFunc("/profile", profileView)
	http.ListenAndServe(":80", nil)
}