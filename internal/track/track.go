// Package track handles the sidecar's /track endpoint.
package track

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

// Handler serves POST /track and GET /api/healthz (health is separate).
type Handler struct {
	Store *state.Store
	Now   func() time.Time // injectable for tests
}

// NewHandler returns a track Handler with the given store.
func NewHandler(s *state.Store) *Handler {
	return &Handler{Store: s, Now: time.Now}
}

// ServeHTTP handles the /track request.
//
// The request body is the raw Ollama request JSON (e.g.
// {"model":"llama3.1:8b","prompt":"..."}) or may be empty for GETs.
//
// The sidecar always responds 200 with the body it received unchanged
// (so NGINX mirror doesn't care about our response), and records the
// model in the store.
//
// For our use case we only need to extract the "model" field.
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	now := h.Now()
	model := extractModel(r)
	h.Store.Record(model, now)

	// Always 200, minimal body.
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]any{
		"model": model,
		"ok":    true,
	})
}

// extractModel pulls the "model" field from the request.
// It checks the JSON body first, then the "model" query param
// (some proxy configurations may pass it that way).
func extractModel(r *http.Request) string {
	if m := r.URL.Query().Get("model"); m != "" {
		return m
	}
	// Try to read the body (it may already be consumed by NGINX mirror;
	// in our design NGINX forwards the original body to the sidecar).
	var payload struct {
		Model string `json:"model"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err == nil {
		return payload.Model
	}
	return ""
}

// LogMiddleware logs every request at debug level.
func LogMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("track: %s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
