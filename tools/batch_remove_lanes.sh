#!/bin/bash
# Batch Lane System Removal Script
# Removes common lane system patterns from Python and shell scripts

echo "=== Batch Lane System Removal ==="
echo ""

# Define files to process (excluding archived versions and backups)
FILES=$(find {{CATALYST_ROOT}}/tools -name "*.py" -o -name "*.sh" | grep -v "versions/" | grep -v ".backup")

TOTAL=0
UPDATED=0

for file in $FILES; do
    ((TOTAL++))

    # Skip if file doesn't contain lane references
        continue
    fi

    echo "Processing: $file"

    # Create backup
    cp "$file" "$file.lane_backup"

    # Common patterns to remove/replace
    sed -i '' 's/standard/standard/g' "$file"
    sed -i '' 's/standard/standard/g' "$file"
    sed -i '' 's/STANDARD/STANDARD/g' "$file"
    sed -i '' 's/STANDARD/STANDARD/g' "$file"

    ((UPDATED++))
done

echo ""
echo "=== Summary ==="
echo "Total files scanned: $TOTAL"
echo "Files updated: $UPDATED"
echo ""
echo "Backups created with .lane_backup extension"
