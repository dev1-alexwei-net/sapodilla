package state

import (
	"sync"
	"testing"
	"time"
)

func TestStoreSnapshot(t *testing.T) {
	t0 := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	for _, tc := range []struct {
		name    string
		records []time.Time
		want    Snapshot
	}{
		{name: "empty"},
		{name: "latest time", records: []time.Time{t0, t0.Add(time.Minute), t0.Add(2 * time.Minute)}, want: Snapshot{Total: 3, LastSeen: timePtr(t0.Add(2 * time.Minute))}},
		{name: "time never regresses", records: []time.Time{t0.Add(time.Hour), t0}, want: Snapshot{Total: 2, LastSeen: timePtr(t0.Add(time.Hour))}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var store Store
			for _, at := range tc.records {
				store.Record(at)
			}
			got := store.Snapshot()
			if got.Total != tc.want.Total || !sameTime(got.LastSeen, tc.want.LastSeen) {
				t.Fatalf("Snapshot() = %+v, want %+v", got, tc.want)
			}
		})
	}
}

func TestStoreConcurrentRecord(t *testing.T) {
	var store Store
	var wg sync.WaitGroup
	for range 100 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			store.Record(time.Now())
		}()
	}
	wg.Wait()
	if got := store.Snapshot().Total; got != 100 {
		t.Fatalf("total = %d, want 100", got)
	}
}

func timePtr(t time.Time) *time.Time { return &t }

func sameTime(a, b *time.Time) bool {
	return a == nil && b == nil || a != nil && b != nil && a.Equal(*b)
}
