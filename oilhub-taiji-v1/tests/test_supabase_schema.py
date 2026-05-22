"""
Supabase Schema Verification Tests for Dog Adoption Center Management System
Tests table creation, constraints, and CRUD operations.
"""
import os
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

# Supabase connection parameters from environment
SUPABASE_DB_URL = os.environ.get("SUPABASE_DATABASE_URL", "")


@pytest.fixture(scope="module")
def db_connection():
    """Create a database connection for the test module."""
    if not SUPABASE_DB_URL:
        pytest.skip("SUPABASE_DATABASE_URL not set")

    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def cursor(db_connection):
    """Create a cursor for individual tests."""
    cur = db_connection.cursor(cursor_factory=RealDictCursor)
    yield cur
    cur.close()


class TestSchemaVerification:
    """Test suite for verifying the dog adoption center schema."""

    def test_tables_exist(self, cursor):
        """Verify all required tables exist."""
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('dogs', 'owners', 'adoption_records')
            ORDER BY table_name;
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]
        assert 'dogs' in tables, "dogs table missing"
        assert 'owners' in tables, "owners table missing"
        assert 'adoption_records' in tables, "adoption_records table missing"

    def test_dogs_columns(self, cursor):
        """Verify dogs table has all required columns."""
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'dogs'
            ORDER BY ordinal_position;
        """)
        columns = {row['column_name']: row for row in cursor.fetchall()}

        assert 'id' in columns
        assert columns['id']['data_type'] == 'uuid'
        assert 'name' in columns
        assert columns['name']['is_nullable'] == 'NO'
        assert 'breed' in columns
        assert 'age' in columns
        assert 'gender' in columns
        assert 'health_status' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns
        assert 'deleted_at' in columns

    def test_owners_columns(self, cursor):
        """Verify owners table has all required columns."""
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'owners'
            ORDER BY ordinal_position;
        """)
        columns = {row['column_name']: row for row in cursor.fetchall()}

        assert 'id' in columns
        assert columns['id']['data_type'] == 'uuid'
        assert 'name' in columns
        assert columns['name']['is_nullable'] == 'NO'
        assert 'contact' in columns
        assert columns['contact']['is_nullable'] == 'NO'
        assert 'address' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns
        assert 'deleted_at' in columns

    def test_adoption_records_columns(self, cursor):
        """Verify adoption_records table has all required columns."""
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'adoption_records'
            ORDER BY ordinal_position;
        """)
        columns = {row['column_name']: row for row in cursor.fetchall()}

        assert 'id' in columns
        assert columns['id']['data_type'] == 'uuid'
        assert 'dog_id' in columns
        assert 'owner_id' in columns
        assert 'adoption_date' in columns
        assert 'returned' in columns
        assert 'notes' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns
        assert 'deleted_at' in columns

    def test_foreign_keys(self, cursor):
        """Verify foreign key constraints exist."""
        cursor.execute("""
            SELECT tc.constraint_name, tc.table_name, kcu.column_name,
                   ccu.table_name AS foreign_table_name,
                   ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'adoption_records';
        """)
        fks = cursor.fetchall()
        assert len(fks) >= 2, "Expected at least 2 foreign keys on adoption_records"

        fk_targets = {(row['column_name'], row['foreign_table_name']) for row in fks}
        assert ('dog_id', 'dogs') in fk_targets
        assert ('owner_id', 'owners') in fk_targets


class TestCRUDOperations:
    """Test suite for CRUD operations on the schema."""

    def test_create_dog(self, cursor):
        """Test creating a dog record."""
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, breed, age, gender, health_status;
        """, ('Buddy', 'Golden Retriever', 3, 'male', 'Healthy'))
        result = cursor.fetchone()
        assert result is not None
        assert result['name'] == 'Buddy'
        assert result['breed'] == 'Golden Retriever'
        assert result['age'] == 3
        assert result['gender'] == 'male'

        # Cleanup
        cursor.execute("DELETE FROM dogs WHERE name = 'Buddy';")

    def test_create_owner(self, cursor):
        """Test creating an owner record."""
        cursor.execute("""
            INSERT INTO owners (name, contact, address)
            VALUES (%s, %s, %s)
            RETURNING id, name, contact, address;
        """, ('John Doe', 'john@example.com', '123 Main St'))
        result = cursor.fetchone()
        assert result is not None
        assert result['name'] == 'John Doe'
        assert result['contact'] == 'john@example.com'

        # Cleanup
        cursor.execute("DELETE FROM owners WHERE name = 'John Doe';")

    def test_create_adoption_record(self, cursor):
        """Test creating an adoption record with foreign keys."""
        # Create a dog first
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, ('Max', 'Labrador', 2, 'male', 'Healthy'))
        dog_id = cursor.fetchone()['id']

        # Create an owner
        cursor.execute("""
            INSERT INTO owners (name, contact, address)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, ('Jane Smith', 'jane@example.com', '456 Oak Ave'))
        owner_id = cursor.fetchone()['id']

        # Create adoption record
        cursor.execute("""
            INSERT INTO adoption_records (dog_id, owner_id, adoption_date, returned, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, dog_id, owner_id, adoption_date, returned, notes;
        """, (dog_id, owner_id, '2024-01-15', False, 'First time adopter'))
        result = cursor.fetchone()
        assert result is not None
        assert result['dog_id'] == dog_id
        assert result['owner_id'] == owner_id
        assert result['returned'] == False

        # Cleanup
        cursor.execute("DELETE FROM adoption_records WHERE dog_id = %s;", (dog_id,))
        cursor.execute("DELETE FROM dogs WHERE id = %s;", (dog_id,))
        cursor.execute("DELETE FROM owners WHERE id = %s;", (owner_id,))

    def test_read_dog(self, cursor):
        """Test reading a dog record."""
        # Insert test data
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, ('Charlie', 'Beagle', 5, 'female', 'Vaccinated'))
        dog_id = cursor.fetchone()['id']

        # Read back
        cursor.execute("SELECT * FROM dogs WHERE id = %s;", (dog_id,))
        result = cursor.fetchone()
        assert result is not None
        assert result['name'] == 'Charlie'
        assert result['breed'] == 'Beagle'

        # Cleanup
        cursor.execute("DELETE FROM dogs WHERE id = %s;", (dog_id,))

    def test_update_dog(self, cursor):
        """Test updating a dog record."""
        # Insert test data
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, ('Rocky', 'Poodle', 4, 'male', 'Healthy'))
        dog_id = cursor.fetchone()['id']

        # Update
        cursor.execute("""
            UPDATE dogs SET age = %s, health_status = %s
            WHERE id = %s
            RETURNING age, health_status, updated_at;
        """, (5, 'Needs checkup', dog_id))
        result = cursor.fetchone()
        assert result is not None
        assert result['age'] == 5
        assert result['health_status'] == 'Needs checkup'
        assert result['updated_at'] is not None

        # Cleanup
        cursor.execute("DELETE FROM dogs WHERE id = %s;", (dog_id,))

    def test_delete_dog(self, cursor):
        """Test soft deleting a dog record."""
        # Insert test data
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, ('Luna', 'Husky', 2, 'female', 'Healthy'))
        dog_id = cursor.fetchone()['id']

        # Soft delete
        cursor.execute("""
            UPDATE dogs SET deleted_at = NOW()
            WHERE id = %s
            RETURNING deleted_at;
        """, (dog_id,))
        result = cursor.fetchone()
        assert result is not None
        assert result['deleted_at'] is not None

        # Verify it's excluded from active records
        cursor.execute("SELECT COUNT(*) FROM dogs WHERE id = %s AND deleted_at IS NULL;", (dog_id,))
        count = cursor.fetchone()['count']
        assert count == 0

        # Hard cleanup
        cursor.execute("DELETE FROM dogs WHERE id = %s;", (dog_id,))

    def test_gender_constraint(self, cursor):
        """Test gender check constraint."""
        with pytest.raises(Exception):
            cursor.execute("""
                INSERT INTO dogs (name, gender)
                VALUES (%s, %s);
            """, ('Invalid', 'other'))

    def test_cascade_delete(self, cursor):
        """Test cascade delete on adoption records."""
        # Create a dog
        cursor.execute("""
            INSERT INTO dogs (name, breed, age, gender, health_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, ('CascadeTest', 'Mix', 1, 'male', 'Healthy'))
        dog_id = cursor.fetchone()['id']

        # Create an owner
        cursor.execute("""
            INSERT INTO owners (name, contact, address)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, ('Cascade Owner', 'cascade@test.com', '789 Test St'))
        owner_id = cursor.fetchone()['id']

        # Create adoption record
        cursor.execute("""
            INSERT INTO adoption_records (dog_id, owner_id, adoption_date)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (dog_id, owner_id, '2024-06-01'))
        adoption_id = cursor.fetchone()['id']

        # Delete the dog - should cascade to adoption_records
        cursor.execute("DELETE FROM dogs WHERE id = %s;", (dog_id,))

        # Verify adoption record is also deleted
        cursor.execute("SELECT COUNT(*) FROM adoption_records WHERE id = %s;", (adoption_id,))
        count = cursor.fetchone()['count']
        assert count == 0

        # Cleanup owner
        cursor.execute("DELETE FROM owners WHERE id = %s;", (owner_id,))
