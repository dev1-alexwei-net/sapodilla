// Command ollama-mirror sidecar is a lightweight usage-tracking sidecar
// for an Ollama proxy. It receives metadata-only requests from NGINX
// (via the mirror directive) and records per-model last-seen timestamps
// in memory. It exposes a minimal REST API for querying usage state.
//
// Design constraints:
//   - stdlib only (no third-party dependencies)
//   - single binary, no persistence
//   - concurrency-safe
package main

import (
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
	"github.com/dev1-alexwei-net/ollama-mirror/internal/track"
)

func main() {
	addr := flag.String("addr", envOr("ADDR", ":9090"), "listen address for the sidecar API")
	flag.Parse()

	st := state.New()

	mux := http.NewServeMux()

	// Health
	mux.HandleFunc("/api/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"status": "ok",
			"time":   time.Now().UTC().Format(time.RFC3339),
		})
	})

	// Track: called by NGINX mirror for every proxied Ollama request
	trackHandler := track.NewHandler(st)
	mux.Handle("/track", track.LogMiddleware(trackHandler))

	// Log every request
	server := &http.Server{
		Addr:              *addr,
		Handler:           logging(mux),
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigCh
		log.Printf("received signal %v, shutting down", sig)
		if err := server.Close(); err != nil {
			log.Printf("server close: %v", err)
		}
		os.Exit(0)
	}()

	log.Printf("ollama-mirror sidecar listening on %s", *addr)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server: %v", err)
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
