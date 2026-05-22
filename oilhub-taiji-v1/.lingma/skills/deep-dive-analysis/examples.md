# Deep Dive Analysis - Examples

## Example 1: Null Pointer Exception in Authentication Service

### Problem Statement

User reports: "Login fails with NullPointerException for some users"

Error log:
```
java.lang.NullPointerException at AuthService.java:42
```

### Step 1: Locate the Error

Read `AuthService.java` around line 42:

```java
// AuthService.java:38-45
public UserProfile getUserProfile(String userId) {
    User user = userRepository.findById(userId);
    Profile profile = profileRepository.findByUserId(userId);  // Line 40
    return new UserProfile(user.getName(), profile.getAvatar()); // Line 42 - NPE here
}
```

**Initial observation**: `profile.getAvatar()` on line 42 throws NPE, meaning `profile` is null.

### Step 2: Trace Call Chain

Use `search_symbol` to find who calls `getUserProfile`:

```
UserController.login()
  → AuthService.authenticate()
    → AuthService.getUserProfile()  ← NPE occurs here
```

### Step 3: Form Hypotheses

**Hypothesis 1**: `profileRepository.findByUserId()` returns null for some users.

**Prediction**: Users without a profile record in the database will trigger this bug.

**Test**: Check if all users have associated profiles:
```sql
SELECT u.id FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE p.id IS NULL;
```

**Result**: PASS - Found 15 users without profiles.

### Step 4: Root Cause Analysis

| Claim | Source | Line(s) |
|-------|--------|---------|
| `profile` can be null | `AuthService.java` | 40 |
| No null check before use | `AuthService.java` | 42 |
| Some users lack profiles | Database query above | - |

**Root Cause**: The code assumes every user has a profile, but the database schema allows users without profiles (nullable foreign key).

**Category**: Logic Error + Data Error

### Step 5: Fix Recommendation

```java
// Option 1: Handle missing profile gracefully
public UserProfile getUserProfile(String userId) {
    User user = userRepository.findById(userId);
    Profile profile = profileRepository.findByUserId(userId);
    String avatar = profile != null ? profile.getAvatar() : "/default-avatar.png";
    return new UserProfile(user.getName(), avatar);
}

// Option 2: Enforce invariant at database level
// Add NOT NULL constraint to profiles.user_id and ensure all users have profiles
```

---

## Example 2: API Response Timeout

### Problem Statement

User reports: "The /api/reports endpoint sometimes takes 30+ seconds to respond"

### Step 1: Reproduce and Measure

Run the endpoint with profiling:
```bash
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8080/api/reports?year=2024"
```

Result: `time_total: 32.451s`

### Step 2: Trace the Code Path

```
ReportController.getReports()
  → ReportService.generateReport()
    → ReportRepository.findAllByYear()
      → EntityManager.createQuery().getResultList()  ← Takes 30s
```

### Step 3: Analyze the Query

Read `ReportRepository.java`:

```java
// ReportRepository.java:25-30
@Query("SELECT r FROM Report r WHERE r.year = :year")
public List<Report> findAllByYear(@Param("year") int year) {
    return entityManager.createQuery(query, Report.class)
        .setParameter("year", year)
        .getResultList();  // Loads ALL reports into memory
}
```

**Observation**: This loads entire report entities into memory. Each report includes large text content.

### Step 4: Check Data Volume

```sql
SELECT COUNT(*), AVG(LENGTH(content)) FROM reports WHERE year = 2024;
-- Result: 50,000 rows, avg content size 10KB = ~500MB total
```

### Step 5: Form Hypotheses

**Hypothesis 1**: Loading 500MB of data into memory causes GC pressure and slow response.

**Test**: Monitor JVM heap during request:
```bash
jstat -gc <pid> 1000
```

**Result**: PASS - Heap usage spikes from 200MB to 800MB during request, triggering multiple GC cycles.

### Step 6: Root Cause Analysis

**Root Cause**: The endpoint returns full report entities including large text content, but the frontend only needs metadata (title, date, summary).

**Category**: Performance Error (N+1 style problem, over-fetching)

### Step 7: Fix Recommendation

```java
// Create a DTO with only needed fields
public class ReportSummary {
    private Long id;
    private String title;
    private LocalDate date;
    private String summary;  // First 200 chars, not full content
}

// Use projection query
@Query("SELECT new com.example.ReportSummary(r.id, r.title, r.date, SUBSTRING(r.content, 1, 200)) FROM Report r WHERE r.year = :year")
public List<ReportSummary> findSummariesByYear(@Param("year") int year);
```

Expected improvement: 500MB → 5MB data transfer, response time 30s → <1s.

---

## Example 3: Intermittent Test Failure

### Problem Statement

User reports: "The test `test_user_creation` fails about 10% of the time with 'duplicate key error'"

### Step 1: Read the Failing Test

```python
# tests/test_users.py:45-52
def test_user_creation():
    user = create_user(email="test@example.com")
    assert user.email == "test@example.com"
    cleanup()  # Deletes the user
```

### Step 2: Identify Race Condition Pattern

The test uses a hardcoded email. If two test instances run concurrently (or a previous run didn't clean up), they collide.

### Step 3: Check Test Isolation

Read the `cleanup()` function:

```python
# tests/conftest.py:20-25
def cleanup():
    db.session.delete(User.query.filter_by(email="test@example.com").first())
    db.session.commit()
```

**Observation**: Cleanup happens AFTER the test, not before. If a previous run crashed before cleanup, the user still exists.

### Step 4: Form Hypotheses

**Hypothesis 1**: Previous test run left stale data, causing duplicate key on re-run.

**Test**: Check if user exists before test starts:
```python
def test_user_creation():
    # Debug: check preconditions
    existing = User.query.filter_by(email="test@example.com").first()
    print(f"Pre-existing user: {existing}")  # Sometimes prints a user!
    user = create_user(email="test@example.com")
```

**Result**: PASS - Occasionally finds a pre-existing user from a crashed previous run.

### Step 5: Root Cause Analysis

**Root Cause**: Test uses non-unique fixture data and cleanup is not guaranteed (no try-finally or fixture teardown).

**Category**: Test Isolation Error

### Step 6: Fix Recommendation

```python
# Use unique data per test run
import uuid

def test_user_creation():
    unique_email = f"test-{uuid.uuid4()}@example.com"
    user = create_user(email=unique_email)
    assert user.email == unique_email
    # Cleanup via pytest fixture teardown, not manual call
```

Or better, use pytest fixtures with proper teardown:

```python
@pytest.fixture
def test_user():
    user = create_user(email=f"test-{uuid.uuid4()}@example.com")
    yield user
    db.session.delete(user)
    db.session.commit()

def test_user_creation(test_user):
    assert test_user.email.startswith("test-")
```

---

## Example 4: Configuration-Dependent Bug

### Problem Statement

User reports: "Application works locally but fails in production with 'Connection refused'"

### Step 1: Compare Configurations

Local `.env`:
```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=myapp
```

Production config (from deployment manifest):
```
DATABASE_HOST=db.internal.company.com
DATABASE_PORT=5432
DATABASE_NAME=myapp_prod
```

### Step 2: Check Connection Code

```python
# db/connection.py:10-15
def get_connection():
    host = os.getenv("DATABASE_HOST", "localhost")
    port = int(os.getenv("DATABASE_PORT", "5432"))
    name = os.getenv("DATABASE_NAME", "myapp")
    return psycopg2.connect(host=host, port=port, dbname=name)
```

**Observation**: Code reads env vars correctly. No obvious bug.

### Step 3: Check Network Connectivity

From production server:
```bash
$ telnet db.internal.company.com 5432
Trying 10.0.1.50...
telnet: Unable to connect to remote host: Connection refused
```

### Step 4: Form Hypotheses

**Hypothesis 1**: Database server is not running or not accepting connections.

**Test**: Check database server status:
```bash
$ ssh db.internal.company.com "systemctl status postgresql"
● postgresql.service - PostgreSQL database server
   Active: active (running) since Mon 2024-01-15
```

Database is running. Check if it's listening:
```bash
$ netstat -tlnp | grep 5432
tcp   0   0 127.0.0.1:5432   0.0.0.0:*   LISTEN   1234/postgres
```

**Result**: Database is only listening on `127.0.0.1` (localhost), not on the external interface.

### Step 5: Root Cause Analysis

**Root Cause**: PostgreSQL is configured to only accept local connections (`listen_addresses = 'localhost'` in `postgresql.conf`). Production app server cannot reach it.

**Category**: Configuration Error

### Step 6: Fix Recommendation

On the database server, update `/etc/postgresql/14/main/postgresql.conf`:
```
listen_addresses = 'localhost,10.0.1.50'  # Add the server's external IP
```

And update `/etc/postgresql/14/main/pg_hba.conf`:
```
host    myapp_prod    app_user    10.0.1.0/24    md5
```

Then restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## Key Takeaways from Examples

1. **Always read the actual code** at the reported location before forming theories
2. **Verify hypotheses with evidence** - don't stop at "probably"
3. **Trace the full call chain** - the symptom location is rarely the root cause
4. **Check assumptions about data** - null values, empty collections, missing records
5. **Consider environment differences** - config, network, permissions, data volume
6. **Document your iteration** - show how you ruled out wrong hypotheses
