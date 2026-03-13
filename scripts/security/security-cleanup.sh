#!/bin/bash
# Security Cleanup Script (Bash version)
# This script removes previously tracked sensitive files from Git while keeping them locally

echo "🔒 Security Cleanup Script"
echo "This script will remove sensitive documentation from Git tracking"
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "❌ Error: Not a git repository"
    exit 1
fi

# Files to remove from Git tracking (but keep locally)
FILES=(
    "SETUP_COMPLETE.md"
    "FIXES_APPLIED.md"
)

echo "📋 Files to remove from Git tracking:"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done
echo ""

# Ask for confirmation
read -p "Do you want to continue? (yes/no): " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "❌ Aborted"
    exit 0
fi

echo ""
echo "🔧 Removing files from Git tracking..."

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  Processing: $file"
        if git rm --cached "$file" 2>/dev/null; then
            echo "    ✅ Removed from Git tracking (file kept locally)"
        else
            echo "    ⚠️  File may not be tracked or already removed"
        fi
    fi
done

echo ""
echo "📝 Git status:"
git status --short

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📌 Next steps:"
echo "  1. Review the changes: git status"
echo "  2. Commit the changes: git add . && git commit -m 'Security: Remove exposed secrets and enhance security'"
echo "  3. Push to remote: git push origin main"
echo ""
echo "⚠️  Important: Make sure you have created a .env file with your new API key!"
