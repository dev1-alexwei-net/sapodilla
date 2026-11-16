package state

import (
	"sync"
	"testing"
	"time"
)

func TestRecordIncrementsTotalAndLastSeen(t *testing.T) {
	s := New()
	now := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)

	s.Record(now)

	if got := s.Total(); got != 1 {
		t.Fatalf("total = %d, want 1", got)
	}
	if !s.LastSeen().Equal(now) {
		t.Fatalf("lastSeen = %v, want %v", s.LastSeen(), now)
	}
}

func TestRecordMultiple(t *testing.T) {
	s := New()
	t0 := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)

	s.Record(t0)
	s.Record(t0.Add(time.Minute))
	s.Record(t0.Add(2 * time.Minute))

	if got := s.Total(); got != 3 {
		t.Fatalf("total = %d, want 3", got)
	}
	want := t0.Add(2 * time.Minute)
	if !s.LastSeen().Equal(want) {
		t.Fatalf("lastSeen = %v, want %v", s.LastSeen(), want)
	}
}

func TestRecordEarlierTimeDoesNotRegressLastSeen(t *testing.T) {
	s := New()
	late := time.Date(2026, 11, 15, 13, 0, 0, 0, time.UTC)
	early := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)

	s.Record(late)
	s.Record(early)

	if !s.LastSeen().Equal(late) {
		t.Fatalf("lastSeen = %v, want %v (should not regress)", s.LastSeen(), late)
	}
	if got := s.Total(); got != 2 {
		t.Fatalf("total = %d, want 2", got)
	}
}

func TestEmptyStore(t *testing.T) {
	s := New()
	if got := s.Total(); got != 0 {
		t.Fatalf("total = %d, want 0", got)
	}
	if !s.LastSeen().IsZero() {
		t.Fatalf("lastSeen = %v, want zero time", s.LastSeen())
	}
}

func TestConcurrentRecord(t *testing.T) {
	s := New()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			s.Record(time.Now())
		}()
	}
	wg.Wait()

	if got := s.Total(); got != 100 {
		t.Fatalf("total = %d, want 100", got)
	}
	if s.LastSeen().IsZero() {
		t.Fatal("lastSeen should not be zero after records")
	}
}
