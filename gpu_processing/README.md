# GPU Processing Module

This directory contains the AI processing code that runs on GPU instances for analyzing pitch decks and generating reviews.

## Directory Structure

```
gpu_processing/
├── README.md          # This file
├── main.py           # Main processing script run on GPU instances
├── requirements.txt  # Python dependencies for GPU instances
├── models/           # AI model files and configurations
├── scripts/          # Utility scripts for GPU processing
├── config/           # Configuration files for AI processing
└── utils/            # Shared utilities for AI processing
```

## Overview

The GPU processing module is designed to:
1. **Analyze PDF pitch decks** using AI models
2. **Generate comprehensive reviews** based on content analysis
3. **Provide scoring and recommendations** for startups
4. **Handle batch processing** for multiple documents

## Processing Workflow

1. **File Detection**: Monitor shared filesystem for new PDF uploads
2. **PDF Analysis**: Extract text, images, and structure from pitch decks
3. **AI Processing**: Run AI models to analyze content and generate insights
4. **Review Generation**: Create structured reviews with scores and recommendations
5. **Result Storage**: Save results to shared filesystem for backend retrieval

## Current Implementation Status

### ✅ Infrastructure Ready
- GPU instance orchestration (via `backend/app/services/gpu_processing.py`)
- Shared filesystem integration
- Processing status tracking
- Error handling and monitoring

### ⏳ AI Processing Implementation
Currently contains placeholder logic that needs real AI implementation:
- PDF content extraction and analysis
- AI model loading and inference
- Review generation algorithms
- Scoring and recommendation systems

## Dependencies

The GPU instances are provisioned with:
- **PyTorch** with CUDA support
- **Transformers** library for NLP models
- **PyPDF2** for PDF processing
- **OpenCV** for image processing
- **Custom AI models** (to be implemented)

## Configuration

GPU processing can be configured via:
- Environment variables for API keys and endpoints
- Configuration files for model parameters
- Shared filesystem paths for input/output

## Usage

The processing is triggered automatically when:
1. New PDF files are uploaded to the platform
2. Backend triggers GPU instance creation
3. GPU instance runs the processing script
4. Results are stored and instance is cleaned up

## Development

To develop AI processing logic:
1. Implement real AI models in `models/` directory
2. Update `main.py` with actual processing logic
3. Test with sample pitch decks
4. Deploy to GPU instances via the backend orchestration system

## Integration Points

- **Backend Integration**: Via `backend/app/services/gpu_processing.py`
- **Shared Storage**: Files exchanged through NFS shared filesystem
- **Database**: Processing status tracked in main application database
- **API**: Results consumed by frontend via backend API endpoints