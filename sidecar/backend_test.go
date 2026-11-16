package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

func TestSessionSnapshot(t *testing.T) {
	at := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	s := &session{}
	if got := s.snapshot(); got.Total != 0 || got.LastSeen != nil {
		t.Fatalf("empty snapshot = %+v", got)
	}
	s.record(at)
	s.record(at.Add(time.Minute))
	s.record(at)
	if got := s.snapshot(); got.Total != 3 || got.LastSeen == nil || !got.LastSeen.Equal(at.Add(time.Minute)) {
		t.Fatalf("snapshot = %+v", got)
	}
}

func TestSessionConcurrentRecord(t *testing.T) {
	s := &session{}
	var wg sync.WaitGroup
	for range 100 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.record(time.Now())
		}()
	}
	wg.Wait()
	if got := s.snapshot().Total; got != 100 {
		t.Fatalf("total = %d, want 100", got)
	}
}

func TestUsage(t *testing.T) {
	w := httptest.NewRecorder()
	(&session{}).usage(w, httptest.NewRequest(http.MethodGet, "/api/usage", nil))
	var got snapshot
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil || w.Code != http.StatusOK || got.Total != 0 {
		t.Fatalf("usage = %d %+v, err %v", w.Code, got, err)
	}
}

func TestUsageRejectsOtherMethods(t *testing.T) {
	w := httptest.NewRecorder()
	(&session{}).usage(w, httptest.NewRequest(http.MethodPost, "/api/usage", nil))
	if w.Code != http.StatusMethodNotAllowed || w.Header().Get("Allow") != http.MethodGet {
		t.Fatalf("usage = %d Allow %q", w.Code, w.Header().Get("Allow"))
	}
}

func TestTrackRecordsAndAcknowledges(t *testing.T) {
	s := &session{}
	w := httptest.NewRecorder()
	s.track(w, httptest.NewRequest(http.MethodPut, "/track", nil))
	var got map[string]bool
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil || w.Code != http.StatusOK || !got["ok"] || s.snapshot().Total != 1 {
		t.Fatalf("track = %d %+v, err %v", w.Code, got, err)
	}
}
