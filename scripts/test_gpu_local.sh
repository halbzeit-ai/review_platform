# Test GPU processing script locally

echo "Testing GPU Processing Script Locally"
echo "====================================="

# Check if we have the GPU processing code
if [ ! -f "/mnt/shared/gpu_processing/main.py" ]; then
    echo "ERROR: GPU processing code not found in shared filesystem"
    echo "Run: ./scripts/sync_gpu_code.sh"
    exit 1
fi

# Find a test PDF file
test_pdf=$(find /mnt/shared/uploads -name "*.pdf" -type f | head -1)
if [ -z "$test_pdf" ]; then
    echo "ERROR: No PDF files found for testing"
    exit 1
fi

echo "Test PDF: $test_pdf"
echo "File size: $(stat -c%s "$test_pdf") bytes"

# Extract relative path for processing
relative_path=${test_pdf#/mnt/shared/}
echo "Relative path: $relative_path"

# Test the GPU processing script
echo ""
echo "Testing GPU processing script execution..."

cd /opt/review-platform/backend
source ../venv/bin/activate

# Set environment variable for shared filesystem
export SHARED_FILESYSTEM_MOUNT_PATH="/mnt/shared"

# Try to run the GPU processing locally
echo "Running: python3 /mnt/shared/gpu_processing/main.py $relative_path"
python3 /mnt/shared/gpu_processing/main.py "$relative_path"

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "SUCCESS: GPU processing script completed"
else
    echo "ERROR: GPU processing script failed with exit code $exit_code"
fi

# Check if results were generated
results_file="/mnt/shared/results/${relative_path//\//_}"
results_file="${results_file%.pdf}_results.json"

echo ""
echo "Checking results..."
echo "Expected results file: $results_file"

if [ -f "$results_file" ]; then
    echo "SUCCESS: Results file exists"
    echo "File size: $(stat -c%s "$results_file") bytes"
    echo "Content preview:"
    head -10 "$results_file"
    
    echo ""
    echo "JSON validation:"
    if python3 -m json.tool "$results_file" > /dev/null 2>&1; then
        echo "SUCCESS: Valid JSON"
    else
        echo "ERROR: Invalid JSON"
        python3 -m json.tool "$results_file"
    fi
else
    echo "ERROR: Results file not created"
fi

# Check completion marker
marker_file="/mnt/shared/temp/processing_complete_${relative_path//\//_}"
if [ -f "$marker_file" ]; then
    echo "SUCCESS: Completion marker created"
else
    echo "ERROR: Completion marker not created"
fi
