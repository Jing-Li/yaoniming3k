# Code Craftsmanship Iron Rules

Concrete patterns and decision trees for devtdd Hard Constraint #11. These rules apply during EVERY GREEN and REFACTOR cycle.

---

## 9.1 Constant Extraction Decision Tree

For every literal in production code, ask:

```
Is this literal a domain concept?
├─ YES → ALWAYS name it as const (even if used once)
│   Examples: "online", "offline", "reply", "broadcast"
│   → const PayloadOnline = "online"
│
├─ NO — Is it used ≥2 times?
│   ├─ YES → ALWAYS extract to const
│   │   Examples: "ayuan.*", 0755, 30*time.Second
│   │   → const SubjectAll = "ayuan.*"
│   │   → const DefaultDirPerm = 0755
│   │
│   └─ NO — Would a reader ask "why this value?"
│       ├─ YES → Name it
│       │   Examples: "127.0.0.1:9876" (default MQ addr)
│       │   → const DefaultMQAddr = "127.0.0.1:9876"
│       │
│       └─ NO → OK as inline literal
│           Examples: 0 (zero index), "" (empty string), nil
```

## 9.2 Constant Naming Convention (Go)

```go
// Group by semantic category, not by location
domain/
  const (
      // Lifecycle payloads
      PayloadOnline          = "online"
      PayloadOffline         = "offline"
      PayloadRetireAnnounced = "retire.announced"
      PayloadManifestChanged = "manifest.changed"

      // Subject patterns
      SubjectAll    = "ayuan.*"
      SubjectPrefix = "ayuan."

      // Timing
      MeditationCheckInterval = 30 * time.Second
  )

infra/localfs/
  const (
      DefaultDirPerm  os.FileMode = 0755
      DefaultFilePerm os.FileMode = 0644
  )

config/
  const (
      DefaultMQAddr   = "127.0.0.1:9876"
      DefaultLogLevel = "info"
      EnvAYuanID      = "AYUAN_ID"
      EnvBaseDir      = "AYUAN_BASE_DIR"
  )
```

## 9.3 DRY Extraction Decision Tree

```
Do 2+ code blocks share identical structure (differing only in parameters)?
├─ YES, same function → Extract inner loop into private helper
│   Example: 4x broadcast Intent construction in ABody
│   → func (b *ABody) broadcast(payload string) error { ... }
│
├─ YES, different functions in same package → Extract package-level helper
│   Example: 8x os.IsNotExist → ErrNotFound pattern in localfs
│   → func notExistToNotFound(err error) error { ... }
│
├─ YES, across packages → Extract to shared internal package
│   Example: home directory lookup in both domain and config
│   → Keep in config only, domain should not need filesystem paths
│
└─ NO → Check Rule of Three (3 similar → extract on 3rd occurrence)
```

## 9.4 Common Extraction Patterns (Go)

### Pattern: Broadcast Helper

```go
// BEFORE: 4 nearly-identical blocks
func (b *ABody) goOnline() error {
    return b.sensorium.Publisher.Publish(Intent{
        ID: generateID(), TraceID: generateTraceID(),
        From: b.ID, Type: IntentBroadcast, Payload: []byte("online"),
    })
}

// AFTER: One helper, 4 call sites
func (b *ABody) broadcast(payload string) error {
    return b.sensorium.Publisher.Publish(Intent{
        ID: generateID(), TraceID: generateTraceID(),
        From: b.ID, Type: IntentBroadcast, Payload: []byte(payload),
    })
}

func (b *ABody) goOnline() error  { return b.broadcast(PayloadOnline) }
func (b *ABody) goOffline() error { return b.broadcast(PayloadOffline) }
```

### Pattern: Error Translation Helper

```go
// BEFORE: 6x the same pattern in localfs adapters
if os.IsNotExist(err) {
    return AManifest{}, domain.ErrNotFound
}

// AFTER: One helper per return shape
func wrapNotFound(err error, zero interface{}) (interface{}, error) {
    if os.IsNotExist(err) { return zero, domain.ErrNotFound }
    return zero, err
}
// Or simpler: type-specific helpers
func loadOrNotFound[T any](load func() (T, error)) (T, error) {
    v, err := load()
    if os.IsNotExist(err) { return v, domain.ErrNotFound }
    return v, err
}
```

### Pattern: Workspace Directory Constants

```go
// BEFORE: Directory list duplicated in engine.go and engine_test.go
dirs := []string{
    filepath.Join(workspaceDir, "inbox"),
    filepath.Join(workspaceDir, "outbox"),
    // ... 6 more
}

// AFTER: Single source of truth
var workspaceSubdirs = []string{
    "inbox", "outbox", ".claude", ".claude/rules",
    "private", "private/aos", "shared",
}

func workspaceDirs(base string) []string {
    dirs := make([]string, len(workspaceSubdirs))
    for i, sub := range workspaceSubdirs {
        dirs[i] = filepath.Join(base, sub)
    }
    return dirs
}
```

## 9.5 Dead Code Detection Checklist

After every GREEN cycle, scan for:

| Signal | Detection | Action |
|--------|-----------|--------|
| Unused struct field | Field declared but never read in any method | Delete field + constructor param |
| Unused function/method | `grep -c "funcName" module/` returns only the declaration | Delete function |
| Unused import | `go vet` or IDE warning | Remove import |
| Unreachable branch | Code after unconditional `return` | Delete unreachable block |
| Commented-out code | `//` lines that look like code | Delete — git history preserves it |
| Redundant helper | Helper exists in two packages doing the same thing | Keep in the more appropriate package, delete the other |

## 9.6 Standard Library Preference Matrix

Before writing a utility function, check this matrix:

| Need | Standard Library | Custom Alternative (FORBIDDEN) |
|------|-----------------|-------------------------------|
| String contains | `strings.Contains(s, sub)` | Hand-written `containsStr()` |
| String join/split | `strings.Join()` / `strings.Split()` | Manual loop + concat |
| Path manipulation | `filepath.Join()`, `filepath.Base()` | Manual string concatenation |
| Time comparison | `time.Since()`, `time.Before()` | Manual `time.Now().Sub()` |
| Error wrapping | `fmt.Errorf("...%w...", err)` | Manual error string construction |
| Slice operations | `slices.Contains()`, `slices.Index()` (Go 1.21+) | Manual loop search |
| Maps operations | `maps.Keys()`, `maps.Values()` (Go 1.21+) | Manual loop collection |

## 9.7 Test Code Craftsmanship

Test code follows the SAME craftsmanship rules as production code:

```go
// BAD: Magic strings in test assertions
if string(intent.Payload) != "online" { ... }
if intent.Type != "broadcast" { ... }

// GOOD: Use the same constants as production
if string(intent.Payload) != domain.PayloadOnline { ... }
if intent.Type != domain.IntentBroadcast { ... }
```

```go
// BAD: Duplicated test setup
func TestFoo(t *testing.T) {
    ms := &fakeManifestLoaderSaver{manifests: make(map[string]domain.AManifest)}
    aosStore := &fakeAOSLoaderSaverChecker{files: make(map[string][]domain.AOSFile)}
    // ... 10 more lines of setup
}

// GOOD: Use the existing test factory
func TestFoo(t *testing.T) {
    ta := newTestABody("echo", true)
    // customize as needed: ta.manifest.manifests["echo"] = ...
}
```

```go
// BAD: Duplicated manifest creation across tests
ta.manifest.manifests["echo"] = domain.AManifest{ID: "echo", Name: "Echo Agent", Raw: map[string]interface{}{"id": "echo"}}

// GOOD: Test helper with descriptive name
func withManifest(ta *testABody, id, name string) {
    ta.manifest.manifests[id] = domain.AManifest{
        ID: id, Name: name, Raw: map[string]interface{}{"id": id},
    }
}
```
