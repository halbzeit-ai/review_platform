-- Create funding stage templates and default stages
-- This provides a flexible system for managing funding process stages

-- Step 1: Create stage templates table for reusable stage definitions
CREATE TABLE IF NOT EXISTS stage_templates (
    id SERIAL PRIMARY KEY,
    stage_name VARCHAR(255) NOT NULL,
    stage_code VARCHAR(100) NOT NULL UNIQUE, -- For programmatic reference
    description TEXT,
    stage_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    estimated_duration_days INTEGER, -- Estimated time to complete
    stage_metadata JSONB DEFAULT '{}', -- Additional configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Insert the default funding stages
INSERT INTO stage_templates (stage_name, stage_code, description, stage_order, is_required, estimated_duration_days, stage_metadata) VALUES
('Deck Submission & Feedback', 'deck_submission', 'Initial pitch deck upload and GP review with feedback', 1, TRUE, 7, '{"allows_documents": true, "document_types": ["pitch_deck"], "feedback_required": true}'),
('Video Upload', 'video_upload', 'Upload pitch video and product demonstration video', 2, TRUE, 3, '{"allows_documents": true, "document_types": ["video"], "required_videos": ["pitch", "product_demo"]}'),
('GP In-Person Interview', 'gp_interview', 'Face-to-face or video interview with General Partners', 3, TRUE, 5, '{"requires_scheduling": true, "interview_types": ["video_call", "in_person"]}'),
('Founder Verification (KYC)', 'kyc_verification', 'Know Your Customer verification and founder background checks', 4, TRUE, 7, '{"requires_documents": true, "document_types": ["identity", "background_check"], "compliance_required": true}'),
('Due Diligence', 'due_diligence', 'Comprehensive analysis of business, financials, market, and legal aspects', 5, TRUE, 21, '{"allows_documents": true, "document_types": ["financial_report", "legal_docs", "market_analysis"], "dd_categories": ["financial", "legal", "technical", "market"]}'),
('Term Sheet Negotiation / LOI', 'term_sheet', 'Negotiate terms and sign Letter of Intent', 6, TRUE, 14, '{"allows_documents": true, "document_types": ["term_sheet", "loi"], "negotiation_rounds": true}'),
('Publishing', 'publishing', 'Publish investment opportunity to investor network', 7, TRUE, 2, '{"visibility": "investors", "marketing_materials": true}'),
('Call for Commits / Investor Interaction', 'investor_commits', 'Collect investor commitments and manage investor communications', 8, TRUE, 30, '{"investor_management": true, "commitment_tracking": true}'),
('Commit Complete', 'commit_complete', 'All required commitments secured and verified', 9, TRUE, 7, '{"commitment_verification": true, "funding_target_check": true}'),
('Signing - Vehicle', 'signing_vehicle', 'Legal documentation signing for investment vehicle', 10, TRUE, 5, '{"legal_docs": true, "document_types": ["vehicle_agreement"], "signing_required": true}'),
('Signing - Startup', 'signing_startup', 'Legal documentation signing by startup founders', 11, TRUE, 5, '{"legal_docs": true, "document_types": ["startup_agreement"], "founder_signatures": true}'),
('Funding Collection at Vehicle', 'funding_collection', 'Collect committed funds into investment vehicle', 12, TRUE, 10, '{"payment_processing": true, "fund_verification": true}'),
('Funding Transfer to Startup', 'funding_transfer', 'Transfer funds from vehicle to startup account', 13, TRUE, 3, '{"transfer_verification": true, "compliance_checks": true}'),
('Round Closed', 'round_closed', 'Investment round successfully completed', 14, TRUE, 1, '{"completion_verification": true, "final_reporting": true}');

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_stage_templates_order ON stage_templates(stage_order);
CREATE INDEX IF NOT EXISTS idx_stage_templates_code ON stage_templates(stage_code);
CREATE INDEX IF NOT EXISTS idx_stage_templates_active ON stage_templates(is_active);

-- Step 4: Update project_stages table to reference stage templates
ALTER TABLE project_stages ADD COLUMN IF NOT EXISTS stage_template_id INTEGER REFERENCES stage_templates(id);
ALTER TABLE project_stages ADD COLUMN IF NOT EXISTS stage_code VARCHAR(100);

-- Step 5: Create function to initialize project stages from templates
CREATE OR REPLACE FUNCTION initialize_project_stages(project_id_param INTEGER)
RETURNS INTEGER AS $$
DECLARE
    stage_count INTEGER := 0;
    template_record RECORD;
BEGIN
    -- Insert stages from active templates
    FOR template_record IN 
        SELECT id, stage_name, stage_code, stage_order, estimated_duration_days, stage_metadata
        FROM stage_templates 
        WHERE is_active = TRUE 
        ORDER BY stage_order
    LOOP
        INSERT INTO project_stages (
            project_id, 
            stage_template_id,
            stage_name, 
            stage_code,
            stage_order, 
            status, 
            stage_metadata,
            created_at
        ) VALUES (
            project_id_param,
            template_record.id,
            template_record.stage_name,
            template_record.stage_code,
            template_record.stage_order,
            CASE WHEN template_record.stage_order = 1 THEN 'active' ELSE 'pending' END,
            template_record.stage_metadata,
            CURRENT_TIMESTAMP
        );
        
        stage_count := stage_count + 1;
    END LOOP;
    
    RETURN stage_count;
END;
$$ LANGUAGE plpgsql;

-- Step 6: Create trigger to auto-initialize stages for new projects
CREATE OR REPLACE FUNCTION auto_initialize_project_stages()
RETURNS TRIGGER AS $$
BEGIN
    -- Only initialize stages for new projects that don't have test data
    IF NEW.is_test = FALSE OR NEW.is_test IS NULL THEN
        PERFORM initialize_project_stages(NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_initialize_stages
    AFTER INSERT ON projects
    FOR EACH ROW
    EXECUTE FUNCTION auto_initialize_project_stages();

-- Step 7: Initialize stages for existing production projects
DO $$
DECLARE
    project_record RECORD;
    stage_count INTEGER;
BEGIN
    FOR project_record IN 
        SELECT id FROM projects 
        WHERE (is_test = FALSE OR is_test IS NULL) 
        AND id NOT IN (SELECT DISTINCT project_id FROM project_stages WHERE project_id IS NOT NULL)
    LOOP
        SELECT initialize_project_stages(project_record.id) INTO stage_count;
        RAISE NOTICE 'Initialized % stages for project %', stage_count, project_record.id;
    END LOOP;
END $$;

-- Step 8: Create view for project progress tracking
CREATE OR REPLACE VIEW project_progress AS
SELECT 
    p.id as project_id,
    p.company_id,
    p.project_name,
    p.funding_round,
    COUNT(ps.id) as total_stages,
    COUNT(CASE WHEN ps.status = 'completed' THEN 1 END) as completed_stages,
    COUNT(CASE WHEN ps.status = 'active' THEN 1 END) as active_stages,
    COUNT(CASE WHEN ps.status = 'pending' THEN 1 END) as pending_stages,
    ROUND(
        (COUNT(CASE WHEN ps.status = 'completed' THEN 1 END)::DECIMAL / 
         NULLIF(COUNT(ps.id), 0)) * 100, 2
    ) as completion_percentage,
    (SELECT stage_name FROM project_stages WHERE project_id = p.id AND status = 'active' ORDER BY stage_order LIMIT 1) as current_stage_name,
    (SELECT stage_order FROM project_stages WHERE project_id = p.id AND status = 'active' ORDER BY stage_order LIMIT 1) as current_stage_order
FROM projects p
LEFT JOIN project_stages ps ON p.id = ps.project_id
WHERE p.is_active = TRUE
GROUP BY p.id, p.company_id, p.project_name, p.funding_round;

-- Step 9: Show summary
SELECT 
    'Stage Templates Created' as item,
    COUNT(*) as count
FROM stage_templates
WHERE is_active = TRUE

UNION ALL

SELECT 
    'Projects with Stages Initialized' as item,
    COUNT(DISTINCT project_id) as count
FROM project_stages;