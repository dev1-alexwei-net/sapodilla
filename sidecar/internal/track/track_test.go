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

func TestTrackIncrementsTotal(t *testing.T) {
	s := state.New()
	h := NewHandler(s)
	fixed := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	h.Now = func() time.Time { return fixed }

	req := httptest.NewRequest("POST", "/track", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := s.Total(); got != 1 {
		t.Fatalf("total = %d, want 1", got)
	}
	if !s.LastSeen().Equal(fixed) {
		t.Fatalf("lastSeen = %v, want %v", s.LastSeen(), fixed)
	}
}

func TestTrackIgnoresBody(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	// Body with arbitrary JSON — sidecar must not care.
	req := httptest.NewRequest("POST", "/track",
		strings.NewReader(`{"model":"llama3.1:8b","prompt":"hi"}`))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := s.Total(); got != 1 {
		t.Fatalf("total = %d, want 1", got)
	}
}

func TestTrackArbitraryMethodAndPath(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	// Any method, any path — all should be recorded.
	for _, method := range []string{"GET", "POST", "PUT", "DELETE", "PATCH"} {
		req := httptest.NewRequest(method, "/whatever/path?x=1", nil)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)

		if rec.Code != http.StatusOK {
			t.Fatalf("%s: status = %d, want 200", method, rec.Code)
		}
	}
	if got := s.Total(); got != 5 {
		t.Fatalf("total = %d, want 5", got)
	}
}

func TestTrackMalformedBodyStill200(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("POST", "/track",
		strings.NewReader("not json at all"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 even for malformed body", rec.Code)
	}
	if got := s.Total(); got != 1 {
		t.Fatalf("total = %d, want 1", got)
	}
}

func TestTrackResponseBodyIsJSON(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("POST", "/track", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	var resp map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("response is not valid JSON: %v", err)
	}
	if resp["ok"] != true {
		t.Fatalf("expected ok=true, got %v", resp)
	}
}
