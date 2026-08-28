package main

import (
	"embed"
	"io/fs"
	"log"
	"net/http"
	"strings"
)

//go:embed static
var staticFS embed.FS

func main() {
	content, err := fs.Sub(staticFS, "static")
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()

	// Landing page (public home)
	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		servePlain(w, r, content, "index.html", "text/html")
	})

	// Public site pages (for website fingerprinting + robots.txt labs)
	mux.HandleFunc("GET /about", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "about.html", "text/html") })
	mux.HandleFunc("GET /products", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "products.html", "text/html") })
	mux.HandleFunc("GET /contact", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "contact.html", "text/html") })

	// robots.txt — exposes hidden directories (Lab: robots.txt Analysis)
	mux.HandleFunc("GET /robots.txt", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte("User-agent: *\n" +
			"Disallow: /admin/\n" +
			"Disallow: /private/\n" +
			"Disallow: /backup/\n" +
			"Disallow: /server-status\n" +
			"\n" +
			"Sitemap: http://globex.local/sitemap.xml\n"))
	})

	// Hidden directories revealed by robots.txt
	mux.HandleFunc("GET /admin/", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "admin.html", "text/html") })
	mux.HandleFunc("GET /private/", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "private.html", "text/html") })
	mux.HandleFunc("GET /backup/", func(w http.ResponseWriter, r *http.Request) { servePlain(w, r, content, "backup.html", "text/html") })

	// Simple sitemap (referenced by robots.txt)
	mux.HandleFunc("GET /sitemap.xml", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/xml")
		_, _ = w.Write([]byte("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
			"<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" +
			"  <url><loc>http://globex.local/</loc></url>\n" +
			"  <url><loc>http://globex.local/about</loc></url>\n" +
			"  <url><loc>http://globex.local/products</loc></url>\n" +
			"  <url><loc>http://globex.local/contact</loc></url>\n" +
			"</urlset>\n"))
	})

	// Health endpoint (nice for nmap/banner labs)
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte("{\"status\":\"ok\",\"version\":\"1.4.2\"}\n"))
	})

	log.Println("globex-web listening on :80")
	if err := http.ListenAndServe(":80", bannerMiddleware(mux)); err != nil {
		log.Fatal(err)
	}
}

func servePlain(w http.ResponseWriter, r *http.Request, fs fs.FS, name, contentType string) {
	data, err := fs.Open(name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer data.Close()
	buf := make([]byte, 0)
	file, _ := fs.Open(name)
	defer file.Close()
	info, _ := file.Stat()
	buf = make([]byte, info.Size())
	_, _ = file.Read(buf)
	w.Header().Set("Content-Type", contentType+"; charset=utf-8")
	_, _ = w.Write(buf)
}

// bannerMiddleware sets fingerprintable headers for the banner-grabbing and
// website-fingerprinting labs.
func bannerMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Server", "nginx/1.24.0")
		w.Header().Set("X-Powered-By", "PHP/8.2.3")
		w.Header().Set("X-Generator", "GlobexCMS 3.1")
		next.ServeHTTP(w, r)
	})
}

var _ = strings.TrimSpace