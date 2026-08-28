package main

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"fmt"
	"html/template"
	"net/http"

	_ "modernc.org/sqlite"
)

const flag = "FLAG{sqli_exploited_mastery}"

var db *sql.DB
var sessions = map[string]int{}

func handleError(w http.ResponseWriter, err error) {
	if err != nil {
		http.Error(w, err.Error(), 500)
	}
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite", "file:globex?mode=memory&cache=shared")
	handleError(nil, err)
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)`)
	handleError(nil, err)
	_, err = db.Exec(`INSERT OR IGNORE INTO users VALUES (1,'admin','admin_secret','admin')`)
	handleError(nil, err)
	_, err = db.Exec(`INSERT OR IGNORE INTO users VALUES (2,'alice','alice_pass','user')`)
	handleError(nil, err)
	_, err = db.Exec(`INSERT OR IGNORE INTO users VALUES (3,'bob','bob_pass','user')`)
	handleError(nil, err)
}

func newToken() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	page := `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SQLi Lab</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:32px;width:380px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}
.sub{color:#5c5c5c;margin:0 0 20px;font-size:0.9rem}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:12px;box-sizing:border-box}
button{width:100%;background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600}
.hint{margin-top:12px;font-size:0.8rem;color:#5c5c5c}
</style></head><body>
<div class="card"><h1>SQLi Lab</h1><p class="sub">Globex HR portal - login</p>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="Username">
<input type="password" name="password" placeholder="Password">
<button type="submit">Login</button></form>
<p class="hint">Hint: try <b>' OR 1=1 --</b></p>
</div></body></html>`
	fmt.Fprint(w, page)
}

func doLogin(w http.ResponseWriter, r *http.Request) {
	r.ParseForm()
	user := r.FormValue("username")
	pass := r.FormValue("password")
	q := "SELECT id, username, role FROM users WHERE username='" + user + "' AND password='" + pass + "'"
	var id int
	var uname, role string
	err := db.QueryRow(q).Scan(&id, &uname, &role)
	if err != nil {
		http.Redirect(w, r, "/?err=1", 302)
		return
	}
	tok := newToken()
	sessions[tok] = id
	http.SetCookie(w, &http.Cookie{Name: "sid", Value: tok, Path: "/"})
	http.Redirect(w, r, "/dashboard", 302)
}

func dashboard(w http.ResponseWriter, r *http.Request) {
	c, err := r.Cookie("sid")
	if err != nil {
		http.Redirect(w, r, "/", 302)
		return
	}
	id, ok := sessions[c.Value]
	if !ok {
		http.Redirect(w, r, "/", 302)
		return
	}
	var uname, role string
	db.QueryRow("SELECT username, role FROM users WHERE id=?", id).Scan(&uname, &role)

	rows := [][3]string{}
	q := r.URL.Query().Get("q")
	if q != "" {
		sql := "SELECT id, username, password FROM users WHERE username LIKE '%" + q + "%' OR role LIKE '%" + q + "%'"
		res, err := db.Query(sql)
		if err == nil {
			defer res.Close()
			for res.Next() {
				var a, b, cc string
				if res.Scan(&a, &b, &cc) == nil {
					rows = append(rows, [3]string{a, b, cc})
				}
			}
		}
	}

	searchHTML := ""
	for _, row := range rows {
		searchHTML += "<tr><td>" + template.HTMLEscapeString(row[0]) + "</td><td>" + template.HTMLEscapeString(row[1]) + "</td><td>" + template.HTMLEscapeString(row[2]) + "</td></tr>"
	}
	flagCard := ""
	if role == "admin" {
		flagCard = `<div class="card"><h2>Flag</h2><p class="flag">` + flag + `</p></div>`
	}

	fmt.Fprintf(w, `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Dashboard</title>
<style>
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f;padding:40px 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin:0 auto 16px;max-width:640px}
h1{font-size:1.5rem;color:#0067c0;margin:0 0 4px}h2{font-size:1rem;margin:0 0 12px}
input{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px;box-sizing:border-box}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:12px}
th,td{border:1px solid #e0e0e0;padding:8px 12px;text-align:left}
.flag{font-family:monospace;font-size:1.1rem;color:#107c41;background:#ecfdf3;padding:12px;border-radius:8px;text-align:center;border:1px solid #86efac}
.hint{font-size:0.8rem;color:#5c5c5c;margin-top:8px}
</style></head><body>
<div class="card"><h1>Welcome, %s</h1><p>Role: %s</p></div>
<div class="card"><h2>Search Users</h2>
<form method="GET"><input type="text" name="q" placeholder="Search by username or role..." value=""><button type="submit">Search</button></form>
<table><tr><th>ID</th><th>Username</th><th>Role</th></tr>%s</table>
<p class="hint">Try UNION: <b>' UNION SELECT id,username,password FROM users --</b></p>
</div>
%s
<div class="card"><a href="/">Logout</a></div>
</body></html>`, template.HTMLEscapeString(uname), template.HTMLEscapeString(role), searchHTML, flagCard)
}

func main() {
	initDB()
	http.HandleFunc("/", loginHandler)
	http.HandleFunc("/login", doLogin)
	http.HandleFunc("/dashboard", dashboard)
	http.ListenAndServe(":80", nil)
}