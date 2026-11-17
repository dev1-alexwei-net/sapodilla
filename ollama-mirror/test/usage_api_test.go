package usageapitest

import (
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

var usageAPIBinary string

func TestMain(m *testing.M) {
	tempDir, err := os.MkdirTemp("", "usage-api-test-")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	usageAPIBinary = filepath.Join(tempDir, "usage-api")

	build := exec.Command("go", "build", "-race", "-o", usageAPIBinary, "../src")
	if output, err := build.CombinedOutput(); err != nil {
		fmt.Fprintf(os.Stderr, "build usage API: %v\n%s", err, output)
		_ = os.RemoveAll(tempDir)
		os.Exit(1)
	}

	code := m.Run()
	_ = os.RemoveAll(tempDir)
	os.Exit(code)
}

type usageSnapshot struct {
	Total    int64 `json:"total"`
	LastSeen *int64 `json:"last_seen"`
}

func startUsageAPI(t *testing.T) (*http.Client, string) {
	t.Helper()

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := listener.Addr().String()
	if err := listener.Close(); err != nil {
		t.Fatal(err)
	}

	cmd := exec.Command(usageAPIBinary)
	cmd.Env = append(os.Environ(), "ADDR="+addr)
	cmd.Stdout = io.Discard
	cmd.Stderr = io.Discard
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_ = cmd.Process.Signal(os.Interrupt)
		done := make(chan struct{})
		go func() {
			_ = cmd.Wait()
			close(done)
		}()
		select {
		case <-done:
		case <-time.After(2 * time.Second):
			_ = cmd.Process.Kill()
			<-done
		}
	})

	client := &http.Client{Timeout: time.Second}
	baseURL := "http://" + addr
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		response, err := client.Get(baseURL + "/api/healthz")
		if err == nil {
			_ = response.Body.Close()
			if response.StatusCode == http.StatusOK {
				return client, baseURL
			}
		}
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatalf("usage API at %s did not become healthy", baseURL)
	return nil, ""
}

func readUsage(t *testing.T, client *http.Client, baseURL string) usageSnapshot {
	t.Helper()
	response, err := client.Get(baseURL + "/api/usage")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		t.Fatalf("GET /api/usage status = %d, want %d", response.StatusCode, http.StatusOK)
	}
	var usage usageSnapshot
	if err := json.NewDecoder(response.Body).Decode(&usage); err != nil {
		t.Fatal(err)
	}
	return usage
}

func TestUsageAPITracksRequests(t *testing.T) {
	client, baseURL := startUsageAPI(t)
	if got := readUsage(t, client, baseURL); got.Total != 0 || got.LastSeen != nil {
		t.Fatalf("initial usage = %+v, want zero total and null last_seen", got)
	}

	response, err := client.Post(baseURL+"/track", "application/json", nil)
	if err != nil {
		t.Fatal(err)
	}
	_ = response.Body.Close()
	if response.StatusCode != http.StatusOK {
		t.Fatalf("POST /track status = %d, want %d", response.StatusCode, http.StatusOK)
	}

	if got := readUsage(t, client, baseURL); got.Total != 1 || got.LastSeen == nil {
		t.Fatalf("usage after track = %+v, want total 1 and non-null last_seen", got)
	} else {
		now := time.Now().UnixMilli()
		if *got.LastSeen < now-5000 || *got.LastSeen > now+5000 {
			t.Fatalf("last_seen = %d, want milliseconds near %d", *got.LastSeen, now)
		}
	}
}

func TestUsageAPIRejectsOtherMethods(t *testing.T) {
	client, baseURL := startUsageAPI(t)
	request, err := http.NewRequest(http.MethodPost, baseURL+"/api/usage", nil)
	if err != nil {
		t.Fatal(err)
	}
	response, err := client.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusMethodNotAllowed || response.Header.Get("Allow") != http.MethodGet {
		t.Fatalf("POST /api/usage = %d, Allow %q; want 405 and GET", response.StatusCode, response.Header.Get("Allow"))
	}
}

func TestUsageAPIConcurrentTracking(t *testing.T) {
	client, baseURL := startUsageAPI(t)
	const count = 100
	var wg sync.WaitGroup
	errs := make(chan error, count)
	for range count {
		wg.Add(1)
		go func() {
			defer wg.Done()
			response, err := client.Post(baseURL+"/track", "application/json", nil)
			if err != nil {
				errs <- err
				return
			}
			_ = response.Body.Close()
			if response.StatusCode != http.StatusOK {
				errs <- fmt.Errorf("POST /track status = %d", response.StatusCode)
			}
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Error(err)
	}
	if got := readUsage(t, client, baseURL); got.Total != count || got.LastSeen == nil {
		t.Fatalf("usage after concurrent tracking = %+v, want total %d", got, count)
	}
}
