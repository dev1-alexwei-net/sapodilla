// Package track handles metadata-only request notifications from the proxy.
package track

import (
	"encoding/json"
	"net/http"
	"time"
)

// Recorder is the storage behavior required by Handler.
type Recorder interface {
	Record(time.Time)
}

// Handler records the arrival time of a mirrored request.
type Handler struct {
	store Recorder
	now   func() time.Time
}

// NewHandler constructs a Handler using the given recorder.
func NewHandler(store Recorder) *Handler {
	return &Handler{store: store, now: time.Now}
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	h.store.Record(h.now())
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]bool{"ok": true})
}
