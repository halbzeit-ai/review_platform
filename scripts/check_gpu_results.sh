#!/bin/bash
# Check GPU processing results on shared filesystem

echo "🔍 Checking GPU Processing Results"
echo "=" * 50

# Check if shared filesystem is mounted
if [ ! -d "/mnt/shared" ]; then
    echo "❌ Shared filesystem not mounted at /mnt/shared"
    exit 1
fi

echo "📁 Shared filesystem structure:"
ls -la /mnt/shared/

echo ""
echo "📄 Recent uploads:"
if [ -d "/mnt/shared/uploads" ]; then
    find /mnt/shared/uploads -name "*.pdf" -type f -exec ls -la {} \; | head -5
else
    echo "No uploads directory found"
fi

echo ""
echo "📊 Recent results:"
if [ -d "/mnt/shared/results" ]; then
    find /mnt/shared/results -name "*_results.json" -type f -exec ls -la {} \; | head -5
else
    echo "No results directory found"
fi

echo ""
echo "🔬 Latest result file content:"
if [ -d "/mnt/shared/results" ]; then
    latest_result=$(find /mnt/shared/results -name "*_results.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$latest_result" ]; then
        echo "File: $latest_result"
        echo "Size: $(stat -c%s "$latest_result") bytes"
        echo "Content:"
        echo "--- START ---"
        cat "$latest_result"
        echo ""
        echo "--- END ---"
        
        echo ""
        echo "🧪 JSON validation:"
        if python3 -m json.tool "$latest_result" > /dev/null 2>&1; then
            echo "✅ Valid JSON"
        else
            echo "❌ Invalid JSON - this is the problem!"
            echo "JSON validation error:"
            python3 -m json.tool "$latest_result"
        fi
    else
        echo "No result files found"
    fi
else
    echo "No results directory found"
fi

echo ""
echo "⏰ Temporary processing markers:"
if [ -d "/mnt/shared/temp" ]; then
    ls -la /mnt/shared/temp/processing_complete_* 2>/dev/null || echo "No completion markers found"
else
    echo "No temp directory found"
fi