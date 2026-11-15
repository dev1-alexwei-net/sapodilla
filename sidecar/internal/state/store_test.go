package state

import (
	"sync"
	"testing"
	"time"
)

func TestRecordAndLastSeen(t *testing.T) {
	s := New()
	now := time.Now()

	s.Record("llama3.1:8b", now)

	got, ok := s.LastSeen("llama3.1:8b")
	if !ok {
		t.Fatal("expected model to be present")
	}
	if !got.Equal(now) {
		t.Fatalf("got %v, want %v", got, now)
	}
}

func TestLastSeenUnknownModel(t *testing.T) {
	s := New()
	_, ok := s.LastSeen("no-such-model")
	if ok {
		t.Fatal("expected unknown model to return false")
	}
}

func TestRecordEmptyModelNoop(t *testing.T) {
	s := New()
	now := time.Now()
	s.Record("", now)

	snap := s.Snapshot()
	if len(snap) != 0 {
		t.Fatalf("expected empty snapshot, got %v", snap)
	}
}

func TestRecordOverwritesEarlier(t *testing.T) {
	s := New()
	t1 := time.Now().Add(-1 * time.Hour)
	t2 := time.Now()

	s.Record("m", t1)
	s.Record("m", t2)

	got, _ := s.LastSeen("m")
	if !got.Equal(t2) {
		t.Fatalf("expected latest timestamp, got %v, want %v", got, t2)
	}
}

func TestSnapshotIsIsolatedCopy(t *testing.T) {
	s := New()
	s.Record("a", time.Now())

	snap1 := s.Snapshot()
	s.Record("b", time.Now())
	snap2 := s.Snapshot()

	if _, ok := snap1["b"]; ok {
		t.Fatal("snapshot1 should not contain b (taken before b was recorded)")
	}
	if _, ok := snap2["a"]; !ok {
		t.Fatal("snapshot2 should contain a")
	}
}

func TestConcurrentRecord(t *testing.T) {
	s := New()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			s.Record("shared", time.Now())
		}(i)
	}
	wg.Wait()

	if _, ok := s.LastSeen("shared"); !ok {
		t.Fatal("expected shared model to be present after concurrent records")
	}
}
