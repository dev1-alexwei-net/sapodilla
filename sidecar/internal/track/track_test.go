package track

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

func TestHandlerRecordsAndAcknowledges(t *testing.T) {
	now := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	var store state.Store
	h := &Handler{store: &store, now: func() time.Time { return now }}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, httptest.NewRequest(http.MethodPost, "/track", strings.NewReader("ignored")))

	if w.Code != http.StatusOK || w.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("response = %d %q, want 200 application/json", w.Code, w.Header().Get("Content-Type"))
	}
	var response struct {
		OK bool `json:"ok"`
	}
	if err := json.NewDecoder(w.Body).Decode(&response); err != nil || !response.OK {
		t.Fatalf("response body = %q, err = %v, want {\"ok\":true}", w.Body, err)
	}
	if got := store.Snapshot(); got.Total != 1 || got.LastSeen == nil || !got.LastSeen.Equal(now) {
		t.Fatalf("Snapshot() = %+v, want one record at %v", got, now)
	}
}

func TestHandlerAcceptsAnyMethodAndBody(t *testing.T) {
	for _, tc := range []struct{ method, body string }{
		{http.MethodGet, ""},
		{http.MethodPut, "not json"},
		{http.MethodDelete, `{"arbitrary":true}`},
	} {
		t.Run(tc.method, func(t *testing.T) {
			var store state.Store
			w := httptest.NewRecorder()
			NewHandler(&store).ServeHTTP(w, httptest.NewRequest(tc.method, "/any/path", strings.NewReader(tc.body)))
			if got := store.Snapshot().Total; w.Code != http.StatusOK || got != 1 {
				t.Fatalf("response = %d, total = %d; want 200 and one record", w.Code, got)
			}
		})
	}
}
