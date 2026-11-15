// Package api provides the read-only REST API for querying usage state.
package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

// UsageResponse is the shape of GET /api/usage.
type UsageResponse struct {
	Models   map[string]time.Time `json:"models"`
	LastSeen time.Time            `json:"last_seen"` // most recent across all models
	Total    int                  `json:"total"`
}

// UsageHandler serves GET /api/usage.
type UsageHandler struct {
	Store *state.Store
	Now   func() time.Time
}

// NewUsageHandler returns a handler with the given store.
func NewUsageHandler(s *state.Store) *UsageHandler {
	return &UsageHandler{Store: s, Now: time.Now}
}

// ServeHTTP handles GET /api/usage.
func (h *UsageHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	snap := h.Store.Snapshot()

	var lastSeen time.Time
	for _, ts := range snap {
		if ts.After(lastSeen) {
			lastSeen = ts
		}
	}

	resp := UsageResponse{
		Models:   snap,
		LastSeen: lastSeen,
		Total:    len(snap),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(resp)
}
