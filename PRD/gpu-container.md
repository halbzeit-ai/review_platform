# GPU Container Architecture PRD

## Overview
This document outlines the migration from the current dedicated GPU server architecture to an on-demand, container-based GPU processing system using Datacrunch.io container orchestration with Ollama models.

## Current State vs Future State

### Current Architecture (Dedicated GPU Server)
```
┌─────────────────┐    ┌─────────────────┐
│ Backend CPU     │    │ Dedicated GPU   │
│ (prod_cpu)      │────│ Server          │
│ Queue Manager   │    │ - Always ON     │
│                 │    │ - Single Point  │
└─────────────────┘    │ - Mixed Models  │
                       └─────────────────┘
```

**Issues:**
- Always-on GPU costs (even when idle)
- Single point of failure
- Resource waste during low usage
- Mixed visual/text processing on same instance

### Future Architecture (Container-Based)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Backend CPU     │    │ Visual Container│    │ Text Container  │
│ (Queue Manager) │────│ (On-Demand)    │    │ (On-Demand)     │
│                 │    │ - Ollama Visual │    │ - Ollama Text   │
│                 │    │ - Scale 0-3     │    │ - Scale 0-5     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       ▲
         │              ┌────────┼───────────────────────┼────────┐
         └──────────────│        PostgreSQL Queue                │
                        │   ┌─────────────────────────────────┐   │
                        │   │ • Persistent task storage       │   │
                        │   │ • Container lifecycle mgmt      │   │
                        │   │ • Auto-scaling triggers         │   │
                        │   │ • Task dependencies             │   │
                        │   │ • Progress tracking             │   │
                        │   └─────────────────────────────────┘   │
                        └─────────────────────────────────────────┘
```

## Container Architecture Design

### Container 1: Visual Processing Container
**Purpose:** Handle all visual analysis tasks
**Base Image:** `ollama/ollama:latest` with vision model
**Model:** `llava:13b` or similar vision-language model
**Scaling:** 0-3 replicas based on visual task queue depth

**Responsibilities:**
- PDF to image conversion
- Slide visual analysis
- Slide feedback generation
- Visual content extraction

**Endpoints:**
- `POST /api/visual-analysis` - Analyze PDF slides
- `POST /api/slide-feedback` - Generate slide feedback
- `GET /api/health` - Container health check

**Resource Requirements:**
- GPU: 1x H100 or A100
- Memory: 32GB+
- Storage: 50GB for model weights

### Container 2: Text Processing Container
**Purpose:** Handle all text-based AI processing
**Base Image:** `ollama/ollama:latest` with text model
**Model:** `gemma3:27b` or similar large language model
**Scaling:** 0-5 replicas based on text task queue depth

**Responsibilities:**
- Company offering extraction
- Startup name extraction
- Healthcare classification
- Funding amount extraction
- Deck date extraction
- Template-based analysis
- Specialized analysis (clinical, regulatory, science)

**Endpoints:**
- `POST /api/extraction/{type}` - Various extraction tasks
- `POST /api/template-analysis` - Template processing
- `POST /api/specialized-analysis` - Specialized analysis
- `GET /api/health` - Container health check

**Resource Requirements:**
- GPU: 1x H100 or A100
- Memory: 48GB+
- Storage: 100GB for model weights

## Processing Queue Integration

### Queue-Driven Task Flow
1. **Task Creation:** Backend creates tasks in `processing_queue` table
2. **Container Trigger:** Queue depth triggers container startup via Datacrunch API
3. **Task Polling:** Container polls for available tasks matching its capabilities
4. **Task Processing:** Container processes task, updates progress in real-time
5. **Result Storage:** Completed results stored in appropriate tables
6. **Container Scaling:** Auto-scale down when queue is empty

### Task Types and Routing
```sql
-- Task types mapped to containers
visual_tasks = [
    'visual_analysis',
    'slide_feedback'
]

text_tasks = [
    'company_offering_extraction',
    'startup_name_extraction', 
    'healthcare_classification',
    'funding_amount_extraction',
    'deck_date_extraction',
    'template_analysis',
    'specialized_clinical',
    'specialized_regulatory',
    'specialized_science'
]
```

### Container Registration System
```sql
-- Enhanced processing_servers table
CREATE TABLE processing_servers (
    id VARCHAR(255) PRIMARY KEY,
    server_type VARCHAR(50) NOT NULL, -- 'visual_container', 'text_container'
    container_id VARCHAR(255), -- Datacrunch container ID
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    capabilities JSONB DEFAULT '{}',
    current_load INTEGER DEFAULT 0,
    max_concurrent_tasks INTEGER DEFAULT 5,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Auto-Scaling Strategy

### Scaling Triggers
- **Scale Up:** Queue depth > threshold for 2+ minutes
- **Scale Down:** No tasks in queue for 10+ minutes
- **Emergency Scale:** Critical priority tasks (immediate startup)

### Scaling Configuration
```yaml
visual_container_scaling:
  min_replicas: 0
  max_replicas: 3
  scale_up_threshold: 2 # tasks waiting
  scale_up_delay: 120s # wait before scaling
  scale_down_delay: 600s # wait before scaling down
  startup_timeout: 300s # max container startup time

text_container_scaling:
  min_replicas: 0
  max_replicas: 5
  scale_up_threshold: 3 # tasks waiting
  scale_up_delay: 120s
  scale_down_delay: 600s
  startup_timeout: 300s
```

## Cost Optimization

### Current Costs (Dedicated GPU)
- Always-on GPU server: ~$800/month
- Utilization: ~20-30% average
- Waste: ~$560/month on idle time

### Projected Costs (Container-Based)
- Visual container: ~$0.50/hour (only when processing)
- Text container: ~$0.80/hour (only when processing)
- Estimated usage: 50 hours/month total
- Monthly cost: ~$65/month
- **Savings: ~$735/month (92% reduction)**

## Implementation Phases

### Phase 1: Current System Stabilization (Week 1)
- Fix GPU server registration in processing queue
- Implement proper queue polling mechanism
- Ensure specialized analysis tasks are created
- Test complete processing pipeline

### Phase 2: Container Development (Weeks 2-3)
- Build Ollama-based Docker images
- Implement container-based queue polling
- Create Datacrunch deployment configurations
- Develop container orchestration logic

### Phase 3: Parallel Testing (Week 4)
- Deploy containers alongside current system
- A/B test processing tasks
- Validate performance and reliability
- Tune auto-scaling parameters

### Phase 4: Migration (Week 5)
- Route all new tasks to container system
- Monitor performance and costs
- Retire dedicated GPU server
- Full production deployment

### Phase 5: Optimization (Week 6+)
- Fine-tune auto-scaling algorithms
- Optimize container startup times
- Implement advanced load balancing
- Monitor cost savings

## Technical Requirements

### Backend Changes
- Container lifecycle management API
- Enhanced queue polling endpoints
- Auto-scaling decision engine
- Container health monitoring
- Task routing based on container capabilities

### Container Infrastructure
- Ollama model preloading optimizations
- Fast container startup (< 2 minutes)
- Persistent model caching
- Health check endpoints
- Graceful shutdown handling

### Monitoring & Observability
- Container performance metrics
- Queue depth monitoring
- Cost tracking per task type
- Processing time analytics
- Error rate monitoring

## Success Metrics

### Performance
- Container startup time: < 2 minutes
- Task processing time: Same as current system
- Queue wait time: < 5 minutes average
- System availability: 99.5%+

### Cost
- Monthly GPU costs: < $100/month
- Cost per processed document: < $0.10
- Cost savings vs current: > 90%

### Reliability
- Task success rate: > 99%
- Container failure rate: < 1%
- Queue processing SLA: 95% within 10 minutes

## Risk Mitigation

### Technical Risks
- **Container startup latency:** Pre-warm containers, optimize images
- **Model loading time:** Persistent model caching, shared storage
- **Queue system complexity:** Thorough testing, fallback mechanisms

### Operational Risks
- **Datacrunch dependency:** Multi-cloud strategy consideration
- **Cost overruns:** Strict auto-scaling limits, cost monitoring
- **Processing delays:** Queue prioritization, emergency scaling

### Business Risks
- **Migration complexity:** Phased rollout, parallel testing
- **Service disruption:** Blue-green deployment strategy
- **Performance regression:** Comprehensive benchmarking

## Future Enhancements

### Advanced Features
- Multi-region container deployment
- GPU type optimization (H100 vs A100 vs RTX)
- Batch processing for efficiency
- Advanced model caching strategies

### AI/ML Improvements
- Model quantization for faster loading
- Specialized model fine-tuning
- Multi-modal processing optimization
- Real-time inference optimizations

### Operational Excellence
- Advanced monitoring dashboards
- Predictive auto-scaling
- Cost optimization algorithms
- Automated performance tuning

---

**Document Version:** 1.0  
**Last Updated:** August 15, 2025  
**Owner:** AI Processing Team  
**Stakeholders:** Backend Team, Infrastructure Team, Finance Team