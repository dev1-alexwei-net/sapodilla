package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

type snapshotReader struct{ snapshot state.Snapshot }

func (r snapshotReader) Snapshot() state.Snapshot { return r.snapshot }

func TestUsageHandler(t *testing.T) {
	lastSeen := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	for _, tc := range []struct {
		name string
		want state.Snapshot
	}{
		{name: "empty"},
		{name: "populated", want: state.Snapshot{Total: 3, LastSeen: &lastSeen}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			r := httptest.NewRequest(http.MethodGet, "/api/usage", nil)
			NewUsageHandler(snapshotReader{tc.want}).ServeHTTP(w, r)
			var got state.Snapshot
			if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
				t.Fatal(err)
			}
			if w.Code != http.StatusOK || w.Header().Get("Content-Type") != "application/json" || !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("response = %d %q %+v, want 200 application/json %+v", w.Code, w.Header().Get("Content-Type"), got, tc.want)
			}
		})
	}
}

func TestUsageHandlerRejectsOtherMethods(t *testing.T) {
	w := httptest.NewRecorder()
	NewUsageHandler(snapshotReader{}).ServeHTTP(w, httptest.NewRequest(http.MethodPost, "/api/usage", nil))
	if w.Code != http.StatusMethodNotAllowed || w.Header().Get("Allow") != http.MethodGet {
		t.Fatalf("response = %d Allow %q, want 405 Allow GET", w.Code, w.Header().Get("Allow"))
	}
}
